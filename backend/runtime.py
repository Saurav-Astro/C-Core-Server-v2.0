from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict, defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@dataclass(slots=True)
class RequestLogRecord:
    timestamp: str
    ip: str
    method: str
    path: str
    status: int
    bytes_sent: int
    thread: str
    latency_ms: float
    cached: bool = False
    note: str = ""


@dataclass(slots=True)
class WorkerState:
    name: str
    status: str = "idle"
    current_path: str = "-"
    tasks_completed: int = 0
    last_seen: str = field(default_factory=utc_now_iso)


@dataclass(slots=True)
class CacheEntry:
    path: str
    body: bytes
    content_type: str
    mtime_ns: int
    stored_at: str = field(default_factory=utc_now_iso)


class MetricsStore:
    def __init__(self, recent_log_limit: int = 200) -> None:
        self._lock = threading.Lock()
        self.started_at = time.monotonic()
        self.active_connections = 0
        self.total_requests = 0
        self.rate_limited_requests = 0
        self.bad_requests = 0
        self.server_errors = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.bytes_sent = 0
        self.last_request_at: str | None = None
        self._request_times: deque[float] = deque()
        self._recent_logs: deque[RequestLogRecord] = deque(maxlen=recent_log_limit)
        self._rps_samples: deque[dict[str, Any]] = deque(maxlen=60)

    def connection_opened(self) -> None:
        with self._lock:
            self.active_connections += 1

    def connection_closed(self) -> None:
        with self._lock:
            self.active_connections = max(0, self.active_connections - 1)

    def record_request(self, record: RequestLogRecord) -> None:
        now = time.monotonic()
        with self._lock:
            self.total_requests += 1
            self.bytes_sent += record.bytes_sent
            self.last_request_at = record.timestamp
            self._request_times.append(now)
            self._prune_request_times(now)
            self._recent_logs.append(record)

    def record_rate_limited(self) -> None:
        with self._lock:
            self.rate_limited_requests += 1

    def record_bad_request(self) -> None:
        with self._lock:
            self.bad_requests += 1

    def record_server_error(self) -> None:
        with self._lock:
            self.server_errors += 1

    def record_cache_hit(self) -> None:
        with self._lock:
            self.cache_hits += 1

    def record_cache_miss(self) -> None:
        with self._lock:
            self.cache_misses += 1

    def current_rps(self) -> int:
        now = time.monotonic()
        with self._lock:
            return self._current_rps_locked(now)

    def sample_rps(self) -> dict[str, Any]:
        sample = {"timestamp": utc_now_iso(), "value": self.current_rps()}
        with self._lock:
            self._rps_samples.append(sample)
        return sample

    def recent_rps_samples(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._rps_samples)

    def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            records = list(self._recent_logs)[-limit:]
        return [asdict(record) for record in reversed(records)]

    def snapshot(self, *, cache_stats: dict[str, Any], queue_size: int) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            uptime = round(time.monotonic() - self.started_at, 2)
            requests = self.total_requests
            cache_hits = self.cache_hits
            cache_misses = self.cache_misses
            current_rps = self._current_rps_locked(now)
            active_connections = self.active_connections
            rate_limited_requests = self.rate_limited_requests
            bad_requests = self.bad_requests
            server_errors = self.server_errors
            bytes_sent = self.bytes_sent
            last_request_at = self.last_request_at

        cache_total = cache_hits + cache_misses
        hit_rate = round((cache_hits / cache_total) * 100, 2) if cache_total else 0.0
        return {
            "connections": {
                "active": active_connections,
                "queued": queue_size,
                "total_requests": requests,
                "rate_limited": rate_limited_requests,
                "bad_requests": bad_requests,
                "server_errors": server_errors,
            },
            "performance": {
                "current_rps": current_rps,
                "recent_rps_samples": self.recent_rps_samples(),
                "uptime_seconds": uptime,
                "last_request_at": last_request_at,
                "bytes_sent": bytes_sent,
            },
            "cache": {
                **cache_stats,
                "hit_rate": hit_rate,
                "hits": cache_hits,
                "misses": cache_misses,
            },
        }

    def _prune_request_times(self, now: float) -> None:
        while self._request_times and now - self._request_times[0] > 1.0:
            self._request_times.popleft()

    def _current_rps_locked(self, now: float) -> int:
        self._prune_request_times(now)
        return len(self._request_times)


class RequestLogger:
    def __init__(self, log_path: str | Path) -> None:
        self.path = Path(log_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def write(self, record: RequestLogRecord) -> None:
        line = json.dumps(asdict(record), ensure_ascii=False)
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


class FileCache:
    def __init__(self, max_entries: int = 64) -> None:
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, path: Path, mtime_ns: int) -> CacheEntry | None:
        key = str(path)
        with self._lock:
            entry = self._entries.get(key)
            if not entry:
                self.misses += 1
                return None
            if entry.mtime_ns != mtime_ns:
                self.misses += 1
                self._entries.pop(key, None)
                return None
            self._entries.move_to_end(key)
            self.hits += 1
            return entry

    def put(self, entry: CacheEntry) -> None:
        key = entry.path
        with self._lock:
            self._entries[key] = entry
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
                self.evictions += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "capacity": self.max_entries,
                "cache_hits": self.hits,
                "cache_misses": self.misses,
                "evictions": self.evictions,
            }


class RateLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = max(1, int(limit))
        self.window_seconds = float(window_seconds)
        self._lock = threading.Lock()
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, ip: str) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            bucket = self._requests[ip]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, int(self.window_seconds - (now - bucket[0]) + 0.5))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            active_ips = len(self._requests)
        return {
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "tracked_ips": active_ips,
        }
