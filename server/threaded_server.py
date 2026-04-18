from __future__ import annotations

import queue
import socket
import threading
import time
from dataclasses import asdict
from pathlib import Path

from config import ServerConfig
from http_utils import (
    HttpRequest,
    HttpRequestError,
    build_response,
    cors_headers,
    guess_content_type,
    json_response,
    parse_http_request,
    safe_join,
)
from runtime import CacheEntry, FileCache, MetricsStore, RateLimiter, RequestLogRecord, RequestLogger, WorkerState, utc_now_iso


WORKER_STOP = object()


class WorkerPool:
    def __init__(self, worker_count: int, task_queue: queue.Queue, handler) -> None:
        self.worker_count = max(1, int(worker_count))
        self.task_queue = task_queue
        self.handler = handler
        self._threads: list[threading.Thread] = []
        self._states: list[WorkerState] = []
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def start(self) -> None:
        if self._threads:
            return
        for index in range(self.worker_count):
            state = WorkerState(name=f"worker-{index + 1}")
            self._states.append(state)
            thread = threading.Thread(target=self._worker_loop, args=(state,), name=state.name, daemon=False)
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop_event.set()
        for _ in range(self.worker_count):
            self.task_queue.put(WORKER_STOP)
        for thread in self._threads:
            thread.join(timeout=10)

    def _worker_loop(self, state: WorkerState) -> None:
        while True:
            task = self.task_queue.get()
            if task is WORKER_STOP:
                with self._lock:
                    state.status = "terminated"
                    state.current_path = "-"
                    state.last_seen = utc_now_iso()
                self.task_queue.task_done()
                break

            conn, addr = task
            with self._lock:
                state.status = "busy"
                state.current_path = "-"
                state.last_seen = utc_now_iso()

            try:
                self.handler(conn, addr, state)
            finally:
                with self._lock:
                    state.tasks_completed += 1
                    state.status = "idle" if not self._stop_event.is_set() else "stopping"
                    state.current_path = "-"
                    state.last_seen = utc_now_iso()
                self.task_queue.task_done()

    def set_current_path(self, state: WorkerState, path: str) -> None:
        with self._lock:
            state.current_path = path
            state.last_seen = utc_now_iso()

    def set_status(self, state: WorkerState, status: str) -> None:
        with self._lock:
            state.status = status
            state.last_seen = utc_now_iso()

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            worker_states = [asdict(state) for state in self._states]
            busy = sum(1 for state in self._states if state.status == "busy")
            terminated = sum(1 for state in self._states if state.status == "terminated")
            idle = sum(1 for state in self._states if state.status == "idle")
        return {
            "worker_count": self.worker_count,
            "busy_workers": busy,
            "idle_workers": idle,
            "terminated_workers": terminated,
            "workers": worker_states,
        }


class ThreadedHttpServer:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.metrics = MetricsStore(config.recent_log_limit)
        self.cache = FileCache(config.cache_size)
        self.logger = RequestLogger(config.log_path)
        self.rate_limiter = RateLimiter(config.rate_limit_requests, config.rate_limit_window_seconds)
        self.task_queue: queue.Queue = queue.Queue(maxsize=config.max_queue_size)
        self.worker_pool = WorkerPool(config.thread_count, self.task_queue, self._handle_connection)
        self._server_socket: socket.socket | None = None
        self._running = threading.Event()
        self._accept_thread: threading.Thread | None = None
        self._sampler_thread: threading.Thread | None = None

    def start(self) -> None:
        if self._running.is_set():
            return

        self.config.static_dir.mkdir(parents=True, exist_ok=True)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)

        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.config.host, self.config.port))
        self._server_socket.listen(self.config.backlog)
        self._server_socket.settimeout(1.0)

        self._running.set()
        self.worker_pool.start()
        self._accept_thread = threading.Thread(target=self._accept_loop, name="acceptor", daemon=False)
        self._accept_thread.start()
        self._sampler_thread = threading.Thread(target=self._sample_metrics_loop, name="metrics-sampler", daemon=False)
        self._sampler_thread.start()

    def serve_forever(self) -> None:
        self.start()
        try:
            while self._running.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt received, shutting down...")
        finally:
            self.stop()

    def stop(self) -> None:
        if not self._running.is_set():
            return

        self._running.clear()
        if self._server_socket is not None:
            try:
                self._server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

        if self._accept_thread is not None:
            self._accept_thread.join(timeout=5)
        if self._sampler_thread is not None:
            self._sampler_thread.join(timeout=5)
        self.worker_pool.stop()

    def _accept_loop(self) -> None:
        assert self._server_socket is not None
        while self._running.is_set():
            try:
                client_conn, client_addr = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            client_conn.settimeout(self.config.request_timeout_seconds)
            self.metrics.connection_opened()

            try:
                self.task_queue.put_nowait((client_conn, client_addr))
            except queue.Full:
                response = build_response(
                    503,
                    "Server queue is full. Please retry shortly.\n",
                    content_type="text/plain; charset=utf-8",
                    headers=cors_headers(),
                    server_name=self.config.server_name,
                )
                try:
                    client_conn.sendall(response)
                except OSError:
                    pass
                try:
                    client_conn.close()
                except OSError:
                    pass
                self.metrics.connection_closed()

    def _sample_metrics_loop(self) -> None:
        while self._running.is_set():
            self.metrics.sample_rps()
            time.sleep(self.config.sample_interval_seconds)

    def _handle_connection(self, conn: socket.socket, addr: tuple[str, int], worker_state: WorkerState) -> None:
        start = time.perf_counter()
        status_code = 500
        response_bytes = b""
        path_label = "-"
        cached = False
        note = ""

        try:
            raw_request = self._read_request(conn)
            if not raw_request:
                self.metrics.record_bad_request()
                response_bytes = build_response(
                    400,
                    "Bad Request\n",
                    headers=cors_headers(),
                    server_name=self.config.server_name,
                )
                status_code = 400
                path_label = "-"
            else:
                request = parse_http_request(raw_request, addr)
                path_label = request.path
                self.worker_pool.set_current_path(worker_state, request.path)

                if request.method == "OPTIONS":
                    response_bytes = build_response(
                        204,
                        b"",
                        headers=cors_headers(),
                        server_name=self.config.server_name,
                    )
                    status_code = 204
                else:
                    request_allowed = True
                    if request.path not in {"/api/benchmark", "/healthz"}:
                        allowed, retry_after = self.rate_limiter.allow(request.client_ip)
                        if not allowed:
                            self.metrics.record_rate_limited()
                            response_bytes = json_response(
                                429,
                                {
                                    "error": "Too Many Requests",
                                    "retry_after_seconds": retry_after,
                                },
                                headers={"Retry-After": str(retry_after), **cors_headers()},
                                server_name=self.config.server_name,
                            )
                            status_code = 429
                            note = "rate_limited"
                            request_allowed = False
                    if request_allowed:
                        if request.method != "GET":
                            response_bytes = json_response(
                                405,
                                {"error": "Method Not Allowed"},
                                headers={"Allow": "GET, OPTIONS", **cors_headers()},
                                server_name=self.config.server_name,
                            )
                            status_code = 405
                        else:
                            response_bytes, status_code, cached, note = self._route_request(request)

        except HttpRequestError as exc:
            self.metrics.record_bad_request()
            response_bytes = json_response(
                400,
                {"error": "Bad Request", "detail": str(exc)},
                headers=cors_headers(),
                server_name=self.config.server_name,
            )
            status_code = 400
            note = "parse_error"
        except Exception as exc:  # noqa: BLE001 - intentional server boundary
            self.metrics.record_server_error()
            response_bytes = json_response(
                500,
                {"error": "Internal Server Error", "detail": "The server failed while handling the request."},
                headers=cors_headers(),
                server_name=self.config.server_name,
            )
            status_code = 500
            note = f"exception:{type(exc).__name__}"
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            log_record = RequestLogRecord(
                timestamp=utc_now_iso(),
                ip=addr[0],
                method=getattr(request, "method", "UNKNOWN") if "request" in locals() else "UNKNOWN",
                path=path_label,
                status=status_code,
                bytes_sent=len(response_bytes),
                thread=threading.current_thread().name,
                latency_ms=latency_ms,
                cached=cached,
                note=note,
            )
            try:
                self.logger.write(log_record)
            except OSError:
                pass
            self.metrics.record_request(log_record)
            self.worker_pool.set_status(worker_state, "idle")
            try:
                conn.sendall(response_bytes)
            except OSError:
                pass
            try:
                conn.close()
            except OSError:
                pass
            self.metrics.connection_closed()

    def _read_request(self, conn: socket.socket) -> bytes:
        buffer = bytearray()
        while len(buffer) < self.config.max_request_bytes:
            try:
                chunk = conn.recv(min(4096, self.config.max_request_bytes - len(buffer)))
            except socket.timeout as exc:
                raise HttpRequestError("Request timed out") from exc
            if not chunk:
                break
            buffer.extend(chunk)
            if b"\r\n\r\n" in buffer:
                break
        return bytes(buffer)

    def _route_request(self, request: HttpRequest) -> tuple[bytes, int, bool, str]:
        if request.path == "/healthz":
            return (
                build_response(
                    200,
                    "ok\n",
                    content_type="text/plain; charset=utf-8",
                    headers=cors_headers(),
                    server_name=self.config.server_name,
                ),
                200,
                False,
                "healthz",
            )
        if request.path.startswith("/api/"):
            return self._handle_api_request(request)
        return self._serve_static(request.path)

    def _handle_api_request(self, request: HttpRequest) -> tuple[bytes, int, bool, str]:
        if request.path == "/api/benchmark":
            delay_ms = self._parse_int(request.query.get("delay_ms", ["25"])[0], default=25, minimum=0, maximum=1000)
            time.sleep(delay_ms / 1000.0)
            payload = {
                "status": "ok",
                "delay_ms": delay_ms,
                "thread": threading.current_thread().name,
                "handled_at": utc_now_iso(),
            }
            return (
                json_response(200, payload, headers=cors_headers(), server_name=self.config.server_name),
                200,
                False,
                "api_benchmark",
            )
        if request.path == "/api/stats":
            payload = self._build_stats_payload()
            return (
                json_response(200, payload, headers=cors_headers(), server_name=self.config.server_name),
                200,
                False,
                "api_stats",
            )
        if request.path == "/api/logs":
            limit = self._parse_limit(request.query.get("limit", ["50"])[0])
            payload = {
                "logs": self.metrics.recent_logs(limit),
                "limit": limit,
                "stored": len(self.metrics.recent_logs(self.config.recent_log_limit)),
            }
            return (
                json_response(200, payload, headers=cors_headers(), server_name=self.config.server_name),
                200,
                False,
                "api_logs",
            )
        if request.path == "/api/threads":
            payload = self._build_threads_payload()
            return (
                json_response(200, payload, headers=cors_headers(), server_name=self.config.server_name),
                200,
                False,
                "api_threads",
            )
        return (
            json_response(
                404,
                {"error": "API endpoint not found", "path": request.path},
                headers=cors_headers(),
                server_name=self.config.server_name,
            ),
            404,
            False,
            "api_not_found",
        )

    def _serve_static(self, request_path: str) -> tuple[bytes, int, bool, str]:
        relative_path = "index.html" if request_path == "/" else request_path.lstrip("/")
        candidate = safe_join(self.config.static_dir, relative_path)
        if candidate is None or not candidate.exists() or not candidate.is_file():
            return (
                build_response(
                    404,
                    f"File not found: {request_path}\n",
                    content_type="text/plain; charset=utf-8",
                    headers=cors_headers(),
                    server_name=self.config.server_name,
                ),
                404,
                False,
                "static_404",
            )

        try:
            mtime_ns = candidate.stat().st_mtime_ns
            cached_entry = self.cache.get(candidate, mtime_ns)
            if cached_entry is not None:
                self.metrics.record_cache_hit()
                body = cached_entry.body
                content_type = cached_entry.content_type
                cached = True
            else:
                self.metrics.record_cache_miss()
                body = candidate.read_bytes()
                content_type = guess_content_type(candidate)
                self.cache.put(
                    CacheEntry(
                        path=str(candidate),
                        body=body,
                        content_type=content_type,
                        mtime_ns=mtime_ns,
                    )
                )
                cached = False
            return (
                build_response(
                    200,
                    body,
                    content_type=content_type,
                    headers={"Cache-Control": "public, max-age=60", **cors_headers()},
                    server_name=self.config.server_name,
                ),
                200,
                cached,
                "static_file",
            )
        except OSError as exc:
            self.metrics.record_server_error()
            return (
                json_response(
                    500,
                    {"error": "Unable to read file", "detail": str(exc)},
                    headers=cors_headers(),
                    server_name=self.config.server_name,
                ),
                500,
                False,
                "file_error",
            )

    def _build_stats_payload(self) -> dict[str, object]:
        return self.metrics.snapshot(cache_stats=self.cache.snapshot(), queue_size=self.task_queue.qsize())

    def _build_threads_payload(self) -> dict[str, object]:
        payload = self.worker_pool.snapshot()
        payload["queue_size"] = self.task_queue.qsize()
        payload["pool"] = {
            "running": self._running.is_set(),
            "thread_count": self.config.thread_count,
        }
        return payload

    @staticmethod
    def _parse_limit(raw_value: str, minimum: int = 1, maximum: int = 200) -> int:
        return ThreadedHttpServer._parse_int(raw_value, default=50, minimum=minimum, maximum=maximum)

    @staticmethod
    def _parse_int(raw_value: str, *, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = default
        return max(minimum, min(maximum, value))
