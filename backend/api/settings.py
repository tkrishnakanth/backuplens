"""User settings persisted in ``%LOCALAPPDATA%\\BackupLens\\config.json``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.media.cache import DEFAULT_LIMIT_BYTES, MediaCache, default_cache_root

from .config_store import ConfigStore
from .errors import ApiError

DEFAULT_SETTINGS: dict[str, Any] = {
    "cacheLimitBytes": DEFAULT_LIMIT_BYTES,
    "cacheLocation": str(default_cache_root()),
    "theme": "system",
    "dateGroupingZone": "capture",
    "thumbnailSize": 320,
}


def read_settings(store: ConfigStore) -> dict[str, Any]:
    saved = store.get("settings", {})
    merged = dict(DEFAULT_SETTINGS)
    if isinstance(saved, dict):
        for key in DEFAULT_SETTINGS:
            if key in saved:
                merged[key] = saved[key]
    return merged


def validate_patch(payload: Any, *, backup_dir: Path | None = None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ApiError("bad_request", "A JSON object is required", 400)
    patch: dict[str, Any] = {}
    if "theme" in payload:
        theme = payload["theme"]
        if theme not in ("light", "dark", "system"):
            raise ApiError("bad_request", "theme must be light, dark or system", 400)
        patch["theme"] = theme
    if "dateGroupingZone" in payload:
        zone = payload["dateGroupingZone"]
        if zone not in ("capture", "machine"):
            raise ApiError("bad_request", "dateGroupingZone must be capture or machine", 400)
        patch["dateGroupingZone"] = zone
    if "thumbnailSize" in payload:
        try:
            size = int(payload["thumbnailSize"])
        except (TypeError, ValueError) as exc:
            raise ApiError("bad_request", "thumbnailSize must be an integer", 400) from exc
        if size < 120 or size > 640:
            raise ApiError("bad_request", "thumbnailSize must be between 120 and 640", 400)
        patch["thumbnailSize"] = size
    if "cacheLimitBytes" in payload:
        try:
            limit = int(payload["cacheLimitBytes"])
        except (TypeError, ValueError) as exc:
            raise ApiError("bad_request", "cacheLimitBytes must be an integer", 400) from exc
        if limit < 16 * 1024 * 1024:
            raise ApiError("bad_request", "cacheLimitBytes must be at least 16 MB", 400)
        patch["cacheLimitBytes"] = limit
    if "cacheLocation" in payload:
        raw = payload["cacheLocation"]
        if not isinstance(raw, str) or not raw.strip():
            raise ApiError("bad_request", "cacheLocation must be a path", 400)
        location = Path(raw).expanduser()
        if not location.is_absolute():
            raise ApiError("bad_request", "cacheLocation must be an absolute path", 400)
        if backup_dir is not None:
            try:
                location.resolve().relative_to(backup_dir.resolve())
                raise ApiError("bad_request", "The cache cannot live inside the backup folder", 400)
            except ValueError:
                pass
        patch["cacheLocation"] = str(location)
    return patch


def apply_patch(state, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply validated settings, recreating the cache when needed."""
    store: ConfigStore = state.config_store
    current = read_settings(store)
    merged = {**current, **patch}
    merged["cacheLocation"] = patch.get("cacheLocation", str(state.media_cache.root))
    merged["cacheLimitBytes"] = int(patch.get("cacheLimitBytes", state.media_cache.limit_bytes))

    location = str(merged["cacheLocation"])
    limit = int(merged["cacheLimitBytes"])
    if Path(location).resolve() != state.media_cache.root.resolve():
        old_cache = state.media_cache
        new_cache = MediaCache(location, limit)
        state.media_cache = new_cache
        old_cache.clear()
    else:
        state.media_cache.limit_bytes = limit
        state.media_cache.enforce_limit()

    store.set("settings", merged)
    return merged
