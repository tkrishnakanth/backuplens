"""Turn an export request into a concrete list of files to write."""

from __future__ import annotations

from pathlib import Path

from backend.backup import Session
from backend.photos import LibraryIndex
from backend.photos.dates import local_day

from .models import ExportItem, ExportPlan, ExportRequest
from .paths import sanitize_component


def _assets_for(index: LibraryIndex, request: ExportRequest) -> tuple[list, list[str]]:
    if request.ids is not None:
        assets = []
        skipped = []
        for asset_id in request.ids:
            asset = index.asset(asset_id)
            if asset is None:
                skipped.append(asset_id)
            else:
                assets.append(asset)
        return assets, skipped
    scope = request.scope or {"kind": "category", "key": "all", "type": "all"}
    kind = scope.get("kind")
    media_type = scope.get("type", "all")
    try:
        if kind == "album":
            assets = index.query(album=scope["id"], media_type=media_type)
        elif kind == "moment":
            assets = index.query(moment=scope["id"], media_type=media_type)
        else:
            assets = index.query(scope=scope.get("key", "all"), media_type=media_type)
    except (KeyError, ValueError):
        return [], []
    return assets, []


def _is_heic(path: str) -> bool:
    return Path(path).suffix.lower() in (".heic", ".heif")


def build_plan(index: LibraryIndex, session: Session, request: ExportRequest) -> ExportPlan:
    assets, skipped_ids = _assets_for(index, request)
    plan = ExportPlan(skipped_ids=skipped_ids)
    options = request.options

    for asset in assets:
        if not asset.file_id:
            plan.skipped_ids.append(asset.id)
            continue
        convert = bool(options.convert_heic_to_jpeg and _is_heic(asset.rel_path) and asset.kind == "photo")
        filename = asset.filename
        if convert:
            filename = f"{Path(filename).stem}.JPG"
        albums = index.album_titles(asset.id)
        plan.items.append(
            ExportItem(
                asset_id=asset.id,
                file_id=asset.file_id,
                filename=sanitize_component(filename),
                rel_path=asset.rel_path,
                size=int(asset.size or 0),
                kind="original",
                taken_at=asset.taken_at,
                tz_offset=asset.tz_offset,
                album=albums[0] if albums else None,
                is_heic=_is_heic(asset.rel_path),
                convert=convert,
                moment=asset.moment_title,
            )
        )
        base = Path(asset.filename).stem

        if options.include_live_video and asset.live_video_file_id:
            record = session.file_record(asset.live_video_file_id)
            suffix = Path(record.relative_path).suffix or ".MOV"
            plan.items.append(
                ExportItem(
                    asset_id=asset.id,
                    file_id=asset.live_video_file_id,
                    filename=sanitize_component(f"{base}{suffix}"),
                    rel_path=record.relative_path,
                    size=int(record.size or 0),
                    kind="live",
                    taken_at=asset.taken_at,
                    tz_offset=asset.tz_offset,
                    album=albums[0] if albums else None,
                    moment=asset.moment_title,
                )
            )

        if options.include_edited and asset.edited_file_id:
            record = session.file_record(asset.edited_file_id)
            suffix = Path(record.relative_path).suffix or ".AAE"
            plan.items.append(
                ExportItem(
                    asset_id=asset.id,
                    file_id=asset.edited_file_id,
                    filename=sanitize_component(f"{base}{suffix}"),
                    rel_path=record.relative_path,
                    size=int(record.size or 0),
                    kind="edited",
                    taken_at=asset.taken_at,
                    tz_offset=asset.tz_offset,
                    album=albums[0] if albums else None,
                    moment=asset.moment_title,
                )
            )
    return plan


def output_relative(item: ExportItem, layout: str) -> Path:
    """Relative output path for a layout. The writer joins it to the destination safely."""
    if layout == "by-date":
        day = local_day(item.taken_at, item.tz_offset)
        if day == "unknown":
            return Path("Unknown date") / item.filename
        year = day[:4]
        return Path(year) / day / item.filename
    if layout == "by-album":
        folder = sanitize_component(item.album) if item.album else "Uncategorized"
        return Path(folder) / item.filename
    if layout == "original-path":
        parts = [sanitize_component(part) for part in Path(item.rel_path).parts if part not in ("", ".", "..")]
        return Path(*parts)
    return Path(item.filename)
