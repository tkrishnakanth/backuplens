"""Localhost-only request security: token, Host/Origin checks, CSP, gzip, access log."""

from __future__ import annotations

import gzip
import hmac
import time
from urllib.parse import urlencode, urlsplit

from flask import Flask, Response, current_app, g, redirect, request

from .errors import error_response

TOKEN_COOKIE = "bl_token"
TOKEN_HEADER = "X-BackupLens-Token"
ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}

CSP = "default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:"


def _host_parts(host_header: str) -> tuple[str | None, int | None]:
    try:
        parsed = urlsplit(f"//{host_header}")
        return parsed.hostname, parsed.port
    except ValueError:
        return None, None


def _allowed_host(host_header: str, port: int | None) -> bool:
    hostname, request_port = _host_parts(host_header)
    if hostname not in ALLOWED_HOSTNAMES:
        return False
    if port is not None and request_port is not None and request_port != port:
        return False
    return True


def _allowed_origin(origin: str, port: int | None) -> bool:
    try:
        parsed = urlsplit(origin)
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if parsed.hostname not in ALLOWED_HOSTNAMES:
        return False
    if port is not None and parsed.port is not None and parsed.port != port:
        return False
    return True


def _strip_token_from_url() -> str:
    params = [(key, value) for key, value in request.args.items(multi=True) if key != "t"]
    query = urlencode(params)
    return request.path + (f"?{query}" if query else "")


def _set_token_cookie(response: Response, token: str, *, secure: bool) -> None:
    response.set_cookie(
        TOKEN_COOKIE,
        token,
        httponly=True,
        samesite="Strict",
        secure=secure,
        path="/",
    )


def _token_from_request(token: str) -> str | None:
    supplied = request.cookies.get(TOKEN_COOKIE)
    if not supplied:
        supplied = request.headers.get(TOKEN_HEADER)
    if not supplied:
        supplied = request.args.get("t")
    if supplied and hmac.compare_digest(supplied, token):
        return supplied
    return None


def install_security(app: Flask, *, token: str, port: int | None = None, secure_cookie: bool = False) -> None:
    """Install all request guards and response headers on ``app``."""

    @app.before_request
    def _guard():  # type: ignore[no-untyped-def]
        g.request_started = time.perf_counter()
        if not _allowed_host(request.host, port):
            return error_response("bad_host", "Requests must target 127.0.0.1 or localhost", 403)

        state = current_app.extensions.get("backuplens")
        if state is not None:
            state.last_request = time.time()
        if request.path == "/api/health":
            return None

        supplied = _token_from_request(token)
        if supplied is not None and request.args.get("t"):
            g.issue_token_cookie = True
        if request.path.startswith("/api/"):
            if supplied is None:
                return error_response("unauthorized", "Missing or invalid token", 401)
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                origin = request.headers.get("Origin")
                if origin and not _allowed_origin(origin, port):
                    return error_response("bad_origin", "Cross-origin request rejected", 403)
                if request.headers.get("Sec-Fetch-Site") == "cross-site":
                    return error_response("bad_origin", "Cross-origin request rejected", 403)
        else:
            if supplied is not None and request.args.get("t"):
                response = redirect(_strip_token_from_url(), code=302)
                _set_token_cookie(response, token, secure=secure_cookie)
                return response
        return None

    @app.after_request
    def _headers(response: Response):  # type: ignore[no-untyped-def]
        response.headers.setdefault("Content-Security-Policy", CSP)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")

        if getattr(g, "issue_token_cookie", False):
            _set_token_cookie(response, token, secure=secure_cookie)

        if response.mimetype == "application/json":
            response.headers.setdefault("Cache-Control", "no-store")
            _maybe_gzip(response)

        if not app.config.get("TESTING_ACCESS_LOG_SILENT", False):
            elapsed_ms = (time.perf_counter() - getattr(g, "request_started", time.perf_counter())) * 1000
            app.logger.info("%s %s -> %s (%.0f ms)", request.method, request.path, response.status_code, elapsed_ms)
        return response


def _maybe_gzip(response: Response) -> None:
    """Gzip JSON payloads (asset lists exceed 600 KB) without extra dependencies."""
    if response.direct_passthrough or response.headers.get("Content-Encoding"):
        return
    accept = request.headers.get("Accept-Encoding", "")
    if "gzip" not in accept.lower():
        return
    data = response.get_data()
    minimum = int(current_app.config.get("GZIP_MIN_BYTES", 1024))
    if len(data) < minimum or not data:
        return
    compressed = gzip.compress(data, 6)
    if len(compressed) >= len(data):
        return
    response.set_data(compressed)
    response.headers["Content-Encoding"] = "gzip"
    response.headers["Content-Length"] = str(len(compressed))
    response.headers.add("Vary", "Accept-Encoding")
