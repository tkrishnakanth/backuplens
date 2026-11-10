"""``/api/backups`` discovery and user-added folders."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from backend.backup.plists import is_backup_folder, read_backup_info

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("backups", __name__, url_prefix="/api")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


@bp.get("/backups")
def list_backups_route():
    state = _state()
    with_size = bool(current_app.config.get("DISCOVERY_WITH_SIZE", True))
    backups = state.discovery(state.config_store.extra_backup_paths(), with_size=with_size)
    return jsonify({"backups": [backup.to_dict() for backup in backups]})


@bp.post("/backups/add")
def add_backup():
    payload = request.get_json(silent=True) or {}
    raw_path = payload.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ApiError("bad_request", "A backup folder path is required", 400)
    folder = Path(raw_path).expanduser()
    if not folder.is_dir() or not is_backup_folder(folder):
        raise ApiError("not_a_backup", "That folder is not an iOS backup", 400)
    info = read_backup_info(folder, with_size=False)
    _state().config_store.add_extra_backup_path(str(folder.resolve()))
    return jsonify({"backup": info.to_dict()}), 201
