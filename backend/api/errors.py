"""Consistent JSON error model for the HTTP layer."""

from __future__ import annotations

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response as WerkzeugResponse

from backend.backup.errors import BackupError


class ApiError(Exception):
    """An error that maps to ``{"error": {"code", "message"}}``."""

    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(code: str, message: str, status: int) -> Response:
    response = jsonify({"error": {"code": code, "message": message}})
    response.status_code = status
    return response


def _wants_json() -> bool:
    return request.path.startswith("/api/") or request.is_json


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(exc: ApiError) -> Response:
        return error_response(exc.code, exc.message, exc.status)

    @app.errorhandler(BackupError)
    def _backup_error(exc: BackupError) -> Response:
        return error_response(exc.code, exc.message, exc.status)

    @app.errorhandler(HTTPException)
    def _http_error(exc: HTTPException) -> Response | WerkzeugResponse | tuple[str, int]:
        if _wants_json():
            code = (exc.name or "http_error").lower().replace(" ", "_")
            return error_response(code, exc.description or exc.name or "HTTP error", exc.code or 500)
        return exc.get_response()

    @app.errorhandler(Exception)
    def _unexpected(exc: Exception) -> Response | tuple[str, int]:
        app.logger.exception("Unhandled error on %s", request.path)
        if _wants_json():
            return error_response("internal_error", "Unexpected server error", 500)
        return "Unexpected server error", 500
