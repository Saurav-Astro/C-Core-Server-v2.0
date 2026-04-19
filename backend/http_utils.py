from __future__ import annotations

import json
import mimetypes
import urllib.parse
from dataclasses import dataclass
from email.utils import formatdate
from pathlib import Path
from typing import Any


class HttpRequestError(ValueError):
    """Raised when a request cannot be parsed."""


STATUS_TEXT: dict[int, str] = {
    200: "OK",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    408: "Request Timeout",
    413: "Payload Too Large",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


@dataclass(slots=True)
class HttpRequest:
    method: str
    target: str
    path: str
    query: dict[str, list[str]]
    version: str
    headers: dict[str, str]
    body: bytes
    client_ip: str
    client_port: int


def parse_http_request(raw_bytes: bytes, client_addr: tuple[str, int]) -> HttpRequest:
    if not raw_bytes:
        raise HttpRequestError("Empty request")

    try:
        text = raw_bytes.decode("iso-8859-1")
    except UnicodeDecodeError as exc:
        raise HttpRequestError("Unable to decode request") from exc

    head, _, _ = text.partition("\r\n\r\n")
    lines = head.split("\r\n")
    if not lines or not lines[0].strip():
        raise HttpRequestError("Missing request line")

    parts = lines[0].split()
    if len(parts) != 3:
        raise HttpRequestError("Invalid request line")

    method, target, version = parts
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        if ":" not in line:
            continue
        name, value = line.split(":", 1)
        headers[name.strip().lower()] = value.strip()

    split_target = urllib.parse.urlsplit(target)
    path = urllib.parse.unquote(split_target.path or "/")
    if not path.startswith("/"):
        path = f"/{path}"

    body = raw_bytes.split(b"\r\n\r\n", 1)[1] if b"\r\n\r\n" in raw_bytes else b""
    return HttpRequest(
        method=method.upper(),
        target=target,
        path=path,
        query=urllib.parse.parse_qs(split_target.query, keep_blank_values=True),
        version=version.upper(),
        headers=headers,
        body=body,
        client_ip=client_addr[0],
        client_port=int(client_addr[1]),
    )


def guess_content_type(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(str(path))
    return content_type or "application/octet-stream"


def safe_join(base_dir: Path, request_path: str) -> Path | None:
    clean = request_path.lstrip("/")
    target = (base_dir / clean).resolve()
    base_resolved = base_dir.resolve()
    if target == base_resolved or base_resolved in target.parents:
        return target
    return None


def build_response(
    status_code: int,
    body: bytes | str = b"",
    *,
    content_type: str = "text/plain; charset=utf-8",
    headers: dict[str, str] | None = None,
    reason: str | None = None,
    server_name: str = "OSLevelThreadedServer/1.0",
) -> bytes:
    if isinstance(body, str):
        body = body.encode("utf-8")

    response_headers = {
        "Date": formatdate(timeval=None, usegmt=True),
        "Server": server_name,
        "Content-Length": str(len(body)),
        "Content-Type": content_type,
        "Connection": "close",
    }
    if headers:
        response_headers.update(headers)

    status_text = reason or STATUS_TEXT.get(status_code, "OK")
    lines = [f"HTTP/1.1 {status_code} {status_text}"]
    lines.extend(f"{key}: {value}" for key, value in response_headers.items())
    return ("\r\n".join(lines) + "\r\n\r\n").encode("iso-8859-1") + body


def json_response(
    status_code: int,
    payload: Any,
    *,
    headers: dict[str, str] | None = None,
    server_name: str = "OSLevelThreadedServer/1.0",
) -> bytes:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return build_response(
        status_code,
        body,
        content_type="application/json; charset=utf-8",
        headers=headers,
        server_name=server_name,
    )


def cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Max-Age": "600",
    }
