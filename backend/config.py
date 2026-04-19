from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CONFIG: dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 8080,
    "static_dir": "public",
    "log_dir": "../logs",
    "log_file": "server.log",
    "thread_count": 6,
    "max_queue_size": 128,
    "request_timeout_seconds": 5,
    "cache_size": 64,
    "rate_limit_requests": 60,
    "rate_limit_window_seconds": 10,
    "recent_log_limit": 200,
    "max_request_bytes": 16384,
    "backlog": 128,
    "sample_interval_seconds": 1,
    "server_name": "OSLevelThreadedServer/1.0",
}


def _resolve_path(base_dir: Path, raw_value: str | Path) -> Path:
    path = Path(raw_value)
    return path if path.is_absolute() else (base_dir / path).resolve()


@dataclass(slots=True)
class ServerConfig:
    base_dir: Path
    host: str
    port: int
    static_dir: Path
    log_dir: Path
    log_file: Path
    thread_count: int
    max_queue_size: int
    request_timeout_seconds: float
    cache_size: int
    rate_limit_requests: int
    rate_limit_window_seconds: float
    recent_log_limit: int
    max_request_bytes: int
    backlog: int
    sample_interval_seconds: float
    server_name: str

    @property
    def log_path(self) -> Path:
        return self.log_file if self.log_file.is_absolute() else (self.log_dir / self.log_file).resolve()


def load_config(
    config_path: str | Path | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> ServerConfig:
    server_dir = Path(__file__).resolve().parent
    config_file = Path(config_path).resolve() if config_path else server_dir / "config.json"
    base_dir = config_file.parent.resolve()

    data: dict[str, Any] = dict(DEFAULT_CONFIG)
    if config_file.exists():
        with config_file.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
            if isinstance(loaded, dict):
                data.update(loaded)

    if overrides:
        for key, value in overrides.items():
            if value is not None:
                data[key] = value

    static_dir = _resolve_path(base_dir, data["static_dir"])
    log_dir = _resolve_path(base_dir, data["log_dir"])
    log_file_raw = Path(data["log_file"])
    log_file = log_file_raw if log_file_raw.is_absolute() else (log_dir / log_file_raw).resolve()

    return ServerConfig(
        base_dir=base_dir,
        host=str(data["host"]),
        port=int(data["port"]),
        static_dir=static_dir,
        log_dir=log_dir,
        log_file=log_file,
        thread_count=max(1, int(data["thread_count"])),
        max_queue_size=max(1, int(data["max_queue_size"])),
        request_timeout_seconds=float(data["request_timeout_seconds"]),
        cache_size=max(1, int(data["cache_size"])),
        rate_limit_requests=max(1, int(data["rate_limit_requests"])),
        rate_limit_window_seconds=float(data["rate_limit_window_seconds"]),
        recent_log_limit=max(1, int(data["recent_log_limit"])),
        max_request_bytes=max(1024, int(data["max_request_bytes"])),
        backlog=max(1, int(data["backlog"])),
        sample_interval_seconds=max(0.25, float(data["sample_interval_seconds"])),
        server_name=str(data["server_name"]),
    )
