"""Settings routes."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..settings import apply_patch, read_settings, validate_patch
from ..state import AppState

bp = Blueprint("settings", __name__, url_prefix="/api")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


@bp.get("/settings")
def get_settings():
    state = _state()
    settings = read_settings(state.config_store)
    settings["cacheLocation"] = str(state.media_cache.root)
    settings["cacheLimitBytes"] = state.media_cache.limit_bytes
    return jsonify(settings)


@bp.post("/settings")
def update_settings():
    state = _state()
    manager = state.session_manager
    backup_dir = manager.session.backup_dir if manager.session is not None else None
    patch = validate_patch(request.get_json(silent=True) or {}, backup_dir=backup_dir)
    return jsonify(apply_patch(state, patch))
