from __future__ import annotations

import argparse
import json
import random
import socket
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


DEFAULT_PATHS = [
    "/",
    "/api/stats",
    "/api/logs?limit=10",
    "/api/threads",
    "/styles.css",
]


@dataclass(slots=True)
class RequestResult:
    path: str
    status: int
    latency_ms: float
    error: str = ""


def parse_status(response_bytes: bytes) -> int:
    try:
        header = response_bytes.split(b"\r\n", 1)[0].decode("iso-8859-1", errors="replace")
        parts = header.split()
        if len(parts) >= 2:
            return int(parts[1])
    except Exception:
        return 0
    return 0


def perform_request(host: str, port: int, path: str, timeout: float) -> RequestResult:
    start = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout) as sock:
            request = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                "User-Agent: OSLevelLoadTester/1.0\r\n"
                "Connection: close\r\n"
                "Accept: */*\r\n\r\n"
            )
            sock.sendall(request.encode("iso-8859-1"))
            response = bytearray()
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response.extend(chunk)
        elapsed_ms = (time.perf_counter() - start) * 1000
        return RequestResult(path=path, status=parse_status(bytes(response)), latency_ms=round(elapsed_ms, 2))
    except Exception as exc:  # noqa: BLE001 - benchmark harness
        elapsed_ms = (time.perf_counter() - start) * 1000
        return RequestResult(path=path, status=0, latency_ms=round(elapsed_ms, 2), error=str(exc))


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    rank = (len(ordered) - 1) * (pct / 100.0)
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = rank - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def run_load_test(
    host: str,
    port: int,
    clients: int,
    requests: int,
    paths: Iterable[str],
    timeout: float,
) -> dict[str, object]:
    path_choices = list(paths) or ["/"]
    results: list[RequestResult] = []
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=max(1, clients)) as executor:
        futures = []
        for index in range(requests):
            path = random.choice(path_choices) if len(path_choices) > 1 else path_choices[0]
            futures.append(executor.submit(perform_request, host, port, path, timeout))
        for future in as_completed(futures):
            results.append(future.result())

    duration = max(time.perf_counter() - start, 1e-6)
    latencies = [result.latency_ms for result in results if result.status > 0]
    successful = [result for result in results if 200 <= result.status < 400]
    status_counts: dict[int, int] = {}
    error_count = 0
    for result in results:
        status_counts[result.status] = status_counts.get(result.status, 0) + 1
        if result.error:
            error_count += 1

    summary = {
        "host": host,
        "port": port,
        "clients": clients,
        "requests": requests,
        "completed_requests": len(results),
        "successful_requests": len(successful),
        "network_errors": error_count,
        "success_rate_pct": round((len(successful) / requests) * 100, 2) if requests else 0.0,
        "requests_per_second": round(len(results) / duration, 2),
        "avg_latency_ms": round(statistics.mean(latencies), 2) if latencies else 0.0,
        "p95_latency_ms": round(percentile(latencies, 95), 2) if latencies else 0.0,
        "min_latency_ms": round(min(latencies), 2) if latencies else 0.0,
        "max_latency_ms": round(max(latencies), 2) if latencies else 0.0,
        "status_counts": {str(code): count for code, count in sorted(status_counts.items())},
        "results": [asdict(result) for result in results],
    }
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Threaded socket load tester")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--clients", type=int, default=20)
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--path", default=None, help="Single path to hit")
    parser.add_argument("--paths", default=None, help="Comma-separated list of paths")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.path:
        paths = [args.path]
    elif args.paths:
        paths = [item.strip() for item in args.paths.split(",") if item.strip()]
    else:
        paths = DEFAULT_PATHS

    summary = run_load_test(args.host, args.port, args.clients, args.requests, paths, args.timeout)
    if args.json:
        print(json.dumps(summary, indent=2))
        return

    print(f"Load test against http://{args.host}:{args.port}")
    print(f"Clients: {summary['clients']} | Requests: {summary['requests']}")
    print(f"Completed: {summary['completed_requests']} | Successes: {summary['successful_requests']}")
    print(f"RPS: {summary['requests_per_second']} | Avg latency: {summary['avg_latency_ms']} ms")
    print(f"P95 latency: {summary['p95_latency_ms']} ms")
    print(f"Status counts: {summary['status_counts']}")


if __name__ == "__main__":
    main()
