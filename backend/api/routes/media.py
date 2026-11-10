"""Media pipeline: thumbnails, previews, Range-capable originals and cache actions."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request, send_file

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("media", __name__, url_prefix="/api")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


def _service():
    state = _state()
    manager = state.session_manager
    if manager.session is None or manager.index is None:
        raise ApiError("session_not_open", "Open a backup and wait for the library index", 409)
    from backend.media.pipeline import MediaService

    return MediaService(manager.session, manager.index, state.media_cache)


@bp.get("/media/<asset_id>/thumb")
def thumb(asset_id: str):
    size_raw = request.args.get("size", "320")
    try:
        size = int(size_raw)
    except ValueError as exc:
        raise ApiError("bad_request", "size must be an integer", 400) from exc
    path = _service().thumb(asset_id, size)
    response = send_file(path, mimetype="image/jpeg", conditional=True, max_age=31536000)
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response


@bp.get("/media/<asset_id>/preview")
def preview(asset_id: str):
    path = _service().preview(asset_id)
    response = send_file(path, mimetype="image/jpeg", conditional=True, max_age=86400)
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@bp.get("/media/<asset_id>/original")
def original(asset_id: str):
    media = _service().original(asset_id)
    response = send_file(
        media.path,
        mimetype=media.mimetype,
        conditional=True,
        as_attachment=False,
        download_name=media.filename,
        max_age=3600,
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@bp.get("/media/<asset_id>/live")
def live(asset_id: str):
    media = _service().live(asset_id)
    response = send_file(
        media.path,
        mimetype=media.mimetype,
        conditional=True,
        as_attachment=False,
        download_name=media.filename,
        max_age=3600,
    )
    response.headers["Cache-Control"] = "private, max-age=3600"
    return response


@bp.post("/cache/clear")
def clear_cache():
    freed = _state().media_cache.clear()
    return jsonify({"freedBytes": freed, **_state().media_cache.stats()})


@bp.get("/cache/stats")
def cache_stats():
    return jsonify(_state().media_cache.stats())
