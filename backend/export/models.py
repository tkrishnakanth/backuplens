"""Validated export requests and options."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LAYOUTS = {"flat", "by-date", "by-album", "original-path"}
CONFLICTS = {"skip", "rename", "overwrite"}


@dataclass(slots=True)
class ExportOptions:
    convert_heic_to_jpeg: bool = False
    include_live_video: bool = False
    include_edited: bool = False
    layout: str = "flat"
    on_conflict: str = "skip"
    set_file_dates: bool = True


@dataclass(slots=True)
class ExportRequest:
    destination: Path
    options: ExportOptions
    ids: list[str] | None = None
    scope: dict[str, Any] | None = None


def _bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _validate_scope(scope: Any) -> dict[str, Any]:
    if not isinstance(scope, dict):
        raise ValueError("scope must be an object")
    kind = scope.get("kind")
    if kind not in ("category", "album", "moment"):
        raise ValueError("scope.kind must be category, album or moment")
    media_type = scope.get("type", "all")
    if media_type not in ("all", "photo", "video"):
        raise ValueError("scope.type must be all, photo or video")
    if kind == "category":
        key = scope.get("key", "all")
        if not isinstance(key, str) or not key:
            raise ValueError("scope.key is required")
        return {"kind": "category", "key": key, "type": media_type}
    identifier = scope.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError(f"scope.{kind} id is required")
    return {"kind": kind, "id": identifier, "type": media_type}


def parse_request(payload: Any) -> ExportRequest:
    """Parse and validate the JSON body of ``POST /api/export``."""
    if not isinstance(payload, dict):
        raise ValueError("A JSON object is required")
    destination_raw = payload.get("destination")
    if not isinstance(destination_raw, str) or not destination_raw.strip():
        raise ValueError("destination is required")
    destination = Path(destination_raw).expanduser()
    if not destination.is_absolute():
        raise ValueError("destination must be an absolute path")

    raw_options = payload.get("options") or {}
    if not isinstance(raw_options, dict):
        raise ValueError("options must be an object")
    layout = str(raw_options.get("layout", "flat"))
    if layout not in LAYOUTS:
        raise ValueError("options.layout is invalid")
    conflict = str(raw_options.get("onConflict", "skip"))
    if conflict not in CONFLICTS:
        raise ValueError("options.onConflict is invalid")
    options = ExportOptions(
        convert_heic_to_jpeg=_bool(raw_options.get("convertHeicToJpeg")),
        include_live_video=_bool(raw_options.get("includeLiveVideo")),
        include_edited=_bool(raw_options.get("includeEdited")),
        layout=layout,
        on_conflict=conflict,
        set_file_dates=_bool(raw_options.get("setFileDates"), default=True),
    )

    raw_ids = payload.get("ids")
    ids = None
    if raw_ids is not None:
        if not isinstance(raw_ids, list) or not raw_ids:
            raise ValueError("ids must be a non-empty array")
        seen: set[str] = set()
        ordered: list[str] = []
        for value in raw_ids:
            if not isinstance(value, str) or not value:
                raise ValueError("ids must contain strings")
            if value not in seen:
                seen.add(value)
                ordered.append(value)
        ids = ordered

    scope = None
    if payload.get("scope") is not None:
        scope = _validate_scope(payload.get("scope"))
    if ids is None and scope is None:
        scope = {"kind": "category", "key": "all", "type": "all"}

    return ExportRequest(destination=destination, options=options, ids=ids, scope=scope)


@dataclass(slots=True)
class ExportItem:
    asset_id: str
    file_id: str
    filename: str
    rel_path: str
    size: int
    kind: str  # original | live | edited
    taken_at: int | None
    tz_offset: int | None
    album: str | None
    is_heic: bool = False
    convert: bool = False
    moment: str | None = None


@dataclass(slots=True)
class ExportPlan:
    items: list[ExportItem] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)

    @property
    def total_bytes(self) -> int:
        return sum(item.size for item in self.items)
