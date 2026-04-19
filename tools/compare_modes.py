from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = ROOT / "backend" / "server.py"
LOAD_TEST_SCRIPT = ROOT / "tools" / "load_test.py"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare single-thread and multi-thread server performance")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--single-port", type=int, default=8081)
    parser.add_argument("--multi-port", type=int, default=8082)
    parser.add_argument("--clients", type=int, default=30)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--path", default=None, help="Single path to benchmark")
    parser.add_argument("--paths", default=None, help="Comma-separated paths to benchmark")
    parser.add_argument("--benchmark-delay", type=int, default=25, help="Delay in ms for the benchmark endpoint")
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--multi-threads", type=int, default=8)
    return parser


def wait_for_port(host: str, port: int, timeout_seconds: float) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.25)
    raise TimeoutError(f"Server did not open {host}:{port} within {timeout_seconds} seconds")


def launch_server(port: int, threads: int, host: str) -> subprocess.Popen[str]:
    command = [
        sys.executable,
        str(SERVER_SCRIPT),
        "--host",
        host,
        "--port",
        str(port),
        "--threads",
        str(threads),
    ]
    return subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def run_load_test(host: str, port: int, clients: int, requests: int, path: str | None, paths: str | None) -> dict[str, object]:
    command = [
        sys.executable,
        str(LOAD_TEST_SCRIPT),
        "--host",
        host,
        "--port",
        str(port),
        "--clients",
        str(clients),
        "--requests",
        str(requests),
        "--json",
    ]
    if path:
        command.extend(["--path", path])
    elif paths:
        command.extend(["--paths", paths])

    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


def stop_server(proc: subprocess.Popen[str]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def pretty_row(label: str, summary: dict[str, object]) -> str:
    return (
        f"{label:<14} "
        f"RPS={summary['requests_per_second']:<10} "
        f"Avg={summary['avg_latency_ms']:<10} "
        f"P95={summary['p95_latency_ms']:<10} "
        f"Success={summary['success_rate_pct']}%"
    )


def main() -> None:
    args = build_parser().parse_args()
    single_proc: subprocess.Popen[str] | None = None
    multi_proc: subprocess.Popen[str] | None = None
    benchmark_path = f"/api/benchmark?delay_ms={args.benchmark_delay}"
    selected_path = args.path or (benchmark_path if not args.paths else None)

    try:
        single_proc = launch_server(args.single_port, 1, args.host)
        wait_for_port(args.host, args.single_port, args.startup_timeout)
        single = run_load_test(
            args.host,
            args.single_port,
            args.clients,
            args.requests,
            selected_path,
            args.paths,
        )
        stop_server(single_proc)
        single_proc = None

        multi_proc = launch_server(args.multi_port, args.multi_threads, args.host)
        wait_for_port(args.host, args.multi_port, args.startup_timeout)
        multi = run_load_test(
            args.host,
            args.multi_port,
            args.clients,
            args.requests,
            selected_path,
            args.paths,
        )
        stop_server(multi_proc)
        multi_proc = None

        single_rps = float(single["requests_per_second"])
        multi_rps = float(multi["requests_per_second"])
        gain = ((multi_rps - single_rps) / single_rps * 100) if single_rps else 0.0

        print("Single-thread vs multi-thread comparison")
        print(pretty_row("Single", single))
        print(pretty_row("Multi", multi))
        print(f"Throughput gain: {gain:.2f}%")
    finally:
        if single_proc is not None:
            stop_server(single_proc)
        if multi_proc is not None:
            stop_server(multi_proc)


if __name__ == "__main__":
    main()
