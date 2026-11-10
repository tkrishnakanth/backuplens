"""``/api/library`` sidebar, asset lists and asset details."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from flask import Blueprint, current_app, jsonify, request

from backend.photos.index import LibraryIndex

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("library", __name__, url_prefix="/api/library")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


def _index() -> LibraryIndex:
    manager = _state().session_manager
    if manager.index_state == "failed":
        message = (manager.snapshot().get("progress") or {}).get("message") or "Index build failed"
        raise ApiError("index_failed", str(message), 500)
    index = manager.index
    if index is None:
        raise ApiError("index_not_ready", "The library index is still being built", 409)
    return index


def _parse_time(value: str | None, *, end_of_day: bool = False) -> int | None:
    if value is None or value == "":
        return None
    text = value.strip()
    try:
        return int(text)
    except ValueError:
        pass
    try:
        if len(text) == 10:
            day = date.fromisoformat(text)
            moment = time.max if end_of_day else time.min
            return int(datetime.combine(day, moment, tzinfo=UTC).timestamp())
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return int(parsed.timestamp())
    except ValueError as exc:
        raise ApiError("bad_request", f"Invalid date/time value: {text}", 400) from exc


@bp.get("/sidebar")
def sidebar():
    return jsonify(_index().sidebar())


@bp.get("/assets")
def assets():
    index = _index()
    args = request.args
    scope = args.get("scope", "all")
    album = args.get("album")
    moment = args.get("moment")
    media_type = args.get("type", "all")
    if album and moment:
        raise ApiError("bad_request", "album and moment are mutually exclusive", 400)
    if media_type not in ("all", "photo", "video"):
        raise ApiError("bad_request", "type must be all, photo or video", 400)
    limit_raw = args.get("limit")
    limit = None
    if limit_raw:
        try:
            limit = int(limit_raw)
        except ValueError as exc:
            raise ApiError("bad_request", "limit must be an integer", 400) from exc
        if limit <= 0 or limit > 20_000:
            raise ApiError("bad_request", "limit must be between 1 and 20000", 400)
    q = args.get("q") or None
    if q is not None and len(q) > 200:
        raise ApiError("bad_request", "q is too long", 400)

    try:
        items = index.query(
            scope=scope,
            album=album,
            moment=moment,
            media_type=media_type,
            from_ts=_parse_time(args.get("from")),
            to_ts=_parse_time(args.get("to"), end_of_day=True),
            q=q,
            limit=limit,
        )
    except KeyError as exc:
        target = "album" if album else "moment" if moment else "scope"
        raise ApiError(f"{target}_not_found", f"Unknown {target}", 404) from exc
    except ValueError as exc:
        raise ApiError("bad_request", str(exc), 400) from exc

    return jsonify({"v": 1, "count": len(items), "items": index.compact(items)})


@bp.get("/assets/<asset_id>")
def asset_detail(asset_id: str):
    index = _index()
    asset = index.asset(asset_id)
    if asset is None:
        raise ApiError("asset_not_found", "Unknown asset id", 404)
    return jsonify(index.asset_detail(asset))
