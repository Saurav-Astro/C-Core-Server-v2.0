from __future__ import annotations

import argparse
import os

from config import load_config
from threaded_server import ThreadedHttpServer


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="OS-level multi-threaded web server")
    parser.add_argument("--config", default=None, help="Path to the JSON configuration file")
    parser.add_argument("--host", default=None, help="Bind host override")
    parser.add_argument("--port", type=int, default=None, help="Bind port override")
    parser.add_argument("--threads", type=int, default=None, help="Worker thread count override")
    parser.add_argument("--mode", choices=["single", "multi"], default=None, help="Shortcut to force single or multi-thread mode")
    parser.add_argument("--static-dir", default=None, help="Static file directory override")
    parser.add_argument("--log-dir", default=None, help="Log directory override")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    def _optional_int(raw_value: str | None) -> int | None:
        if raw_value is None or raw_value == "":
            return None
        try:
            return int(raw_value)
        except ValueError:
            return None

    render_mode = os.getenv("RENDER", "").lower() == "true"
    env_host = os.getenv("HOST")
    env_port = _optional_int(os.getenv("PORT"))
    env_threads = _optional_int(os.getenv("THREAD_COUNT"))

    if args.mode == "single":
        thread_count = 1
    elif args.threads is not None:
        thread_count = args.threads
    else:
        thread_count = env_threads

    overrides = {
        "host": args.host or env_host or ("0.0.0.0" if render_mode else None),
        "port": args.port if args.port is not None else env_port,
        "thread_count": thread_count,
        "static_dir": args.static_dir,
        "log_dir": args.log_dir,
    }
    config = load_config(args.config, overrides)
    server = ThreadedHttpServer(config)

    print(
        f"Starting {config.server_name} on http://{config.host}:{config.port} "
        f"with {config.thread_count} worker threads"
    )
    print(f"Static directory: {config.static_dir}")
    print(f"Log file: {config.log_path}")

    server.serve_forever()


if __name__ == "__main__":
    main()
