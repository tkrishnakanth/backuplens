"""Normalised photo library index and query helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from .dates import day_label, local_day, unix_to_iso
from .errors import PhotosDatabaseMissing
from .loader import load_photos
from .models import CATEGORIES, Album, Asset, Moment

Progress = Callable[[str, int, int], None]

PHOTO_DB_PATH = "Media/PhotoData/Photos.sqlite"
PHOTO_DOMAIN = "CameraRollDomain"
THUMBNAIL_SUFFIX = "5005.JPG"


def _category_predicate(key: str):
    if key == "all":
        return lambda asset: True
    if key == "camera_roll":
        return lambda asset: asset.in_camera_roll and not asset.trashed
    if key == "photos":
        return lambda asset: asset.kind == "photo" and not asset.trashed
    if key == "videos":
        return lambda asset: asset.kind == "video" and not asset.trashed
    if key == "favorites":
        return lambda asset: asset.favorite and not asset.trashed
    if key == "live":
        return lambda asset: asset.is_live and not asset.trashed
    if key == "portrait":
        return lambda asset: asset.is_portrait and not asset.trashed
    if key == "panoramas":
        return lambda asset: asset.is_panorama and not asset.trashed
    if key == "timelapse":
        return lambda asset: asset.is_timelapse and not asset.trashed
    if key == "slomo":
        return lambda asset: asset.is_slomo and not asset.trashed
    if key == "screenshots":
        return lambda asset: asset.is_screenshot and not asset.trashed
    if key == "hidden":
        return lambda asset: asset.hidden
    if key == "trashed":
        return lambda asset: asset.trashed
    raise KeyError(key)


class LibraryIndex:
    """In-memory normalised library. Built once per open backup."""

    def __init__(self, assets: list[Asset], albums: list[Album], moments: list[Moment]) -> None:
        self.assets = assets
        self.albums = albums
        self.moments = moments
        self.by_id = {asset.id: asset for asset in assets}
        self._album_by_id = {album.id: album for album in albums}
        self._moment_by_id = {moment.id: moment for moment in moments}
        self._categories = {
            key: [asset for asset in assets if _category_predicate(key)(asset)]
            for key, _label in CATEGORIES
        }
        self._album_titles: dict[str, list[str]] = {}
        for album in albums:
            for asset_id in album.asset_ids:
                self._album_titles.setdefault(asset_id, []).append(album.title)
        for titles in self._album_titles.values():
            titles.sort(key=str.casefold)

    # ----------------------------------------------------------------- lookup
    def sidebar(self) -> dict[str, object]:
        return {
            "categories": [
                {"key": key, "label": label, "count": len(self._categories[key])}
                for key, label in CATEGORIES
            ],
            "albums": [
                {"id": album.id, "title": album.title, "count": len(album.asset_ids)}
                for album in self.albums
            ],
            "moments": [
                {"id": moment.id, "title": moment.title, "count": len(moment.asset_ids)}
                for moment in self.moments
            ],
            "assetCount": len(self.assets),
        }

    def category_count(self, key: str) -> int:
        return len(self._categories[key])

    def query(
        self,
        *,
        scope: str = "all",
        album: str | None = None,
        moment: str | None = None,
        media_type: str = "all",
        from_ts: int | None = None,
        to_ts: int | None = None,
        q: str | None = None,
        limit: int | None = None,
    ) -> list[Asset]:
        """Filter the library. Raises ``KeyError`` for an unknown album/moment."""
        if album and moment:
            raise ValueError("album and moment are mutually exclusive")
        if album:
            selected = self._album_by_id.get(album)
            if selected is None:
                raise KeyError("album")
            allowed = set(selected.asset_ids)
            base = [asset for asset in self.assets if asset.id in allowed]
        elif moment:
            selected_moment = self._moment_by_id.get(moment)
            if selected_moment is None:
                raise KeyError("moment")
            allowed = set(selected_moment.asset_ids)
            base = [asset for asset in self.assets if asset.id in allowed]
        else:
            if scope not in self._categories:
                raise KeyError("scope")
            base = self._categories[scope]
            if scope == "all":
                # The sidebar count includes trashed assets, but the
                # All grid hides deleted photos, exactly as the reference screenshot does.
                base = [asset for asset in base if not asset.trashed]

        needle = q.casefold() if q else None
        results: list[Asset] = []
        for asset in base:
            if media_type == "photo" and asset.kind != "photo":
                continue
            if media_type == "video" and asset.kind != "video":
                continue
            if from_ts is not None and (asset.taken_at is None or asset.taken_at < from_ts):
                continue
            if to_ts is not None and (asset.taken_at is None or asset.taken_at > to_ts):
                continue
            if needle is not None:
                haystack = f"{asset.filename}\n{asset.original_name or ''}".casefold()
                if needle not in haystack:
                    continue
            results.append(asset)
            if limit is not None and len(results) >= limit:
                break
        return results

    def asset(self, asset_id: str) -> Asset | None:
        return self.by_id.get(asset_id)

    def album_titles(self, asset_id: str) -> list[str]:
        return list(self._album_titles.get(asset_id, []))

    def asset_detail(self, asset: Asset) -> dict[str, object]:
        return {
            "id": asset.id,
            "fileId": asset.file_id,
            "thumbFileId": asset.thumb_file_id,
            "liveVideoFileId": asset.live_video_file_id,
            "editedFileId": asset.edited_file_id,
            "filename": asset.filename,
            "originalName": asset.original_name,
            "kind": asset.kind,
            "takenAt": asset.taken_at,
            "takenAtIso": unix_to_iso(asset.taken_at),
            "timezoneOffset": asset.tz_offset,
            "width": asset.width,
            "height": asset.height,
            "duration": asset.duration,
            "size": asset.size,
            "favorite": asset.favorite,
            "hidden": asset.hidden,
            "trashed": asset.trashed,
            "isLive": asset.is_live,
            "isPortrait": asset.is_portrait,
            "isPanorama": asset.is_panorama,
            "isTimelapse": asset.is_timelapse,
            "isSlomo": asset.is_slomo,
            "isScreenshot": asset.is_screenshot,
            "inCameraRoll": asset.in_camera_roll,
            "hasAdjustments": asset.has_adjustments,
            "latitude": asset.lat,
            "longitude": asset.lon,
            "relPath": asset.rel_path,
            "moment": asset.moment_title,
            "albums": list(self._album_titles.get(asset.id, [])),
        }

    def compact(self, assets: Iterable[Asset]) -> list[list[object]]:
        """Compact row format from project-docs/ARCHITECTURE.md §7.5 (flag bits in ADR-006)."""
        rows: list[list[object]] = []
        for asset in assets:
            rows.append(
                [
                    asset.id,
                    asset.filename,
                    asset.taken_at or 0,
                    asset.media_kind,
                    asset.width,
                    asset.height,
                    asset.flags(),
                    round(float(asset.duration or 0.0), 3),
                    asset.size or 0,
                    asset.tz_offset,
                ]
            )
        return rows

    def date_groups(self, assets: Iterable[Asset] | None = None) -> list[dict[str, object]]:
        """Local-day groups, newest first, with display labels for the grid headers."""
        groups: dict[str, int] = {}
        source = assets if assets is not None else self.assets
        for asset in source:
            day = local_day(asset.taken_at, asset.tz_offset)
            groups[day] = groups.get(day, 0) + 1
        return [
            {"date": day, "label": day_label(day), "count": count}
            for day, count in groups.items()
        ]


def build_index(session, progress: Progress | None = None) -> LibraryIndex:
    """Extract ``Photos.sqlite`` from the backup and build a :class:`LibraryIndex`."""

    def report(stage: str, done: int, total: int) -> None:
        if progress:
            progress(stage, done, total)

    report("extracting", 0, 1)
    photo_id = session.find_file_id(PHOTO_DB_PATH, PHOTO_DOMAIN)
    if not photo_id:
        raise PhotosDatabaseMissing("Photos.sqlite is not present in this backup")
    work_dir = Path(session.temp_dir) / "photos"
    work_dir.mkdir(parents=True, exist_ok=True)
    db_path = work_dir / "Photos.sqlite"
    session.extract_file(photo_id, db_path)
    for suffix in ("-wal", "-shm"):
        sibling_id = session.find_file_id(PHOTO_DB_PATH + suffix, PHOTO_DOMAIN)
        if sibling_id:
            session.extract_file(sibling_id, work_dir / f"Photos.sqlite{suffix}")
    if not db_path.is_file():
        raise PhotosDatabaseMissing("Photos.sqlite could not be extracted")
    report("extracting", 1, 1)

    rows = session.manifest_query(
        "SELECT fileID, relativePath FROM Files WHERE domain=? AND flags=1",
        (PHOTO_DOMAIN,),
    )
    file_map = {str(row["relativePath"]): str(row["fileID"]) for row in rows}
    report("reading", 0, 0)
    assets, albums, moments = load_photos(db_path, file_map, progress)
    index = LibraryIndex(assets, albums, moments)
    report("ready", len(assets), len(assets))
    return index
