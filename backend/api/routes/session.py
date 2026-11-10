"""``/api/session`` open, inspect and close."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..errors import ApiError
from ..session_manager import AlreadyOpen
from ..state import AppState

bp = Blueprint("session", __name__, url_prefix="/api")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


@bp.post("/session/open")
def open_session():
    state = _state()
    payload = request.get_json(silent=True) or {}
    backup_id = payload.get("backupId")
    password = payload.get("password")
    if not isinstance(backup_id, str) or not backup_id:
        raise ApiError("bad_request", "backupId is required", 400)
    if password is not None and not isinstance(password, str):
        raise ApiError("bad_request", "password must be a string", 400)

    backups = state.discovery(state.config_store.extra_backup_paths(), with_size=False)
    match = next(
        (item for item in backups if backup_id in (item.id, item.path, item.udid)),
        None,
    )
    if match is None:
        raise ApiError("backup_not_found", "Unknown backup id", 404)
    try:
        snapshot = state.session_manager.open(match.path, password, match)
    except AlreadyOpen as exc:
        raise ApiError("already_open", "Close the current backup first", 409) from exc
    return jsonify(snapshot)


@bp.get("/session")
def session_state():
    return jsonify(_state().session_manager.snapshot())


@bp.post("/session/close")
def close_session():
    payload = request.get_json(silent=True) or {}
    purge_cache = bool(payload.get("purgeCache", False))
    snapshot = _state().session_manager.close()
    if purge_cache:
        _state().media_cache.clear()
    return jsonify(snapshot)
