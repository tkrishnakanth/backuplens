"""Read Photos.sqlite into normalised assets, albums and moments."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from pathlib import Path

from .dates import core_data_to_unix
from .models import Album, Asset, Moment
from .schema import PhotosSchema, detect_schema, quote_ident

Progress = Callable[[str, int, int], None]

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Z_PK", "pk"),
    ("ZDIRECTORY", "directory"),
    ("ZFILENAME", "filename"),
    ("ZKIND", "kind"),
    ("ZKINDSUBTYPE", "subtype"),
    ("ZDATECREATED", "created"),
    ("ZFAVORITE", "favorite"),
    ("ZHIDDEN", "hidden"),
    ("ZTRASHEDSTATE", "trashed"),
    ("ZSAVEDASSETTYPE", "savedtype"),
    ("ZDEPTHTYPE", "depth"),
    ("ZWIDTH", "width"),
    ("ZHEIGHT", "height"),
    ("ZDURATION", "duration"),
    ("ZLATITUDE", "lat"),
    ("ZLONGITUDE", "lon"),
    ("ZHASADJUSTMENTS", "has_adjustments"),
    ("ZISDETECTEDSCREENSHOT", "screenshot_flag"),
    ("ZMOMENT", "moment_pk"),
)

_ATTRIBUTE_COLUMNS: tuple[tuple[str, str], ...] = (
    ("ZORIGINALFILENAME", "original_name"),
    ("ZORIGINALFILESIZE", "original_size"),
    ("ZTIMEZONEOFFSET", "tz_offset"),
    ("ZORIGINALWIDTH", "orig_width"),
    ("ZORIGINALHEIGHT", "orig_height"),
)


def _expr(alias: str | None, columns: AbstractSet[str], column: str, output: str) -> str:
    if alias and column.upper() in columns:
        return f"{alias}.{quote_ident(column)} AS {quote_ident(output)}"
    return f"NULL AS {quote_ident(output)}"


def _asset_select(schema: PhotosSchema) -> str:
    parts = [_expr("a", schema.asset_columns, column, output) for column, output in _COLUMNS]
    for column, output in _ATTRIBUTE_COLUMNS:
        parts.append(_expr("aaa" if schema.attributes_table else None, schema.attributes_columns, column, output))
    select = ", ".join(parts)
    from_clause = f"FROM {quote_ident(schema.asset_table)} a"
    if schema.attributes_table:
        from_clause += (
            f" LEFT JOIN {quote_ident(schema.attributes_table)} aaa ON aaa.{quote_ident('ZASSET')}=a.{quote_ident('Z_PK')}"
        )
    order = (
        f"a.{quote_ident('ZDATECREATED')} DESC, a.{quote_ident('Z_PK')} DESC"
        if "ZDATECREATED" in schema.asset_columns
        else f"a.{quote_ident('Z_PK')} DESC"
    )
    return f"SELECT {select} {from_clause} ORDER BY {order}"


def _normalise_title(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\xa0", " ").strip()
    return text or None


def _load_moments(conn: sqlite3.Connection, schema: PhotosSchema) -> tuple[dict[int, str], dict[int, int | None]]:
    if not schema.moment_table:
        return {}, {}
    columns = schema.moment_columns
    title_expr = quote_ident("ZTITLE") if "ZTITLE" in columns else "NULL"
    tz_expr = quote_ident("ZTIMEZONEOFFSET") if "ZTIMEZONEOFFSET" in columns else "NULL"
    rows = conn.execute(
        f"SELECT {quote_ident('Z_PK')} AS pk, {title_expr} AS title, {tz_expr} AS tz_offset "
        f"FROM {quote_ident(schema.moment_table)}"
    )
    titles: dict[int, str] = {}
    offsets: dict[int, int | None] = {}
    for pk, title, tz_offset in rows:
        normalised = _normalise_title(title)
        if normalised:
            titles[int(pk)] = normalised
        offsets[int(pk)] = int(tz_offset) if tz_offset is not None else None
    return titles, offsets


def _directory_and_path(directory: object, filename: str) -> tuple[str, str]:
    folder = str(directory or "").strip().strip("/")
    if folder.startswith("Media/"):
        folder = folder[6:]
    rel_path = f"Media/{folder}/{filename}" if folder else f"Media/{filename}"
    return folder, rel_path


def _read_assets(
    conn: sqlite3.Connection, schema: PhotosSchema
) -> list[Asset]:
    moment_titles, moment_offsets = _load_moments(conn, schema)
    assets: list[Asset] = []
    for row in conn.execute(_asset_select(schema)):
        pk = int(row["pk"])
        subtype = int(row["subtype"]) if row["subtype"] is not None else None
        depth = int(row["depth"]) if row["depth"] is not None else None
        filename = str(row["filename"] or row["original_name"] or f"asset-{pk}")
        directory, rel_path = _directory_and_path(row["directory"], filename)
        moment_pk = int(row["moment_pk"]) if row["moment_pk"] is not None else None

        lat = float(row["lat"]) if row["lat"] is not None else None
        lon = float(row["lon"]) if row["lon"] is not None else None
        if lat is not None and abs(lat + 180.0) < 1e-6:
            lat = None
        if lon is not None and abs(lon + 180.0) < 1e-6:
            lon = None

        tz_offset = int(row["tz_offset"]) if row["tz_offset"] is not None else moment_offsets.get(moment_pk or -1)
        width = int(row["width"] or row["orig_width"] or 0)
        height = int(row["height"] or row["orig_height"] or 0)
        saved_type = int(row["savedtype"]) if row["savedtype"] is not None else None
        raw_directory = str(row["directory"] or "")
        in_camera_roll = saved_type == 3 if saved_type is not None else raw_directory.startswith("DCIM")

        asset = Asset(
            id=f"a{pk}",
            pk=pk,
            file_id=None,
            rel_path=rel_path,
            directory=directory,
            filename=filename,
            original_name=str(row["original_name"]) if row["original_name"] else None,
            kind="video" if row["kind"] == 1 else "photo",
            taken_at=core_data_to_unix(row["created"]),
            tz_offset=tz_offset,
            width=width,
            height=height,
            duration=float(row["duration"]) if row["duration"] is not None else None,
            size=int(row["original_size"]) if row["original_size"] is not None else None,
            favorite=bool(row["favorite"]),
            hidden=bool(row["hidden"]),
            trashed=bool(row["trashed"]),
            is_live=subtype == 2,
            is_portrait=(depth in (1, 2)) or subtype == 3,
            is_panorama=subtype == 1,
            is_timelapse=subtype == 102,
            is_slomo=subtype == 101,
            is_screenshot=bool(row["screenshot_flag"]) or subtype == 10,
            in_camera_roll=in_camera_roll,
            has_adjustments=bool(row["has_adjustments"]),
            lat=lat,
            lon=lon,
            moment_title=moment_titles.get(moment_pk) if moment_pk else None,
            moment_pk=moment_pk,
        )
        assets.append(asset)
    return assets


def _load_albums(conn: sqlite3.Connection, schema: PhotosSchema, assets: list[Asset]) -> list[Album]:
    if not (schema.album_table and schema.join_table and schema.join_album_column and schema.join_asset_column):
        return []
    columns = schema.album_columns
    kind_expr = quote_ident("ZKIND") if "ZKIND" in columns else "NULL"
    rows = conn.execute(
        f"SELECT {quote_ident('Z_PK')} AS pk, {quote_ident('ZTITLE')} AS title, {kind_expr} AS kind "
        f"FROM {quote_ident(schema.album_table)}"
    )
    user_albums: dict[int, str] = {}
    for pk, title, kind in rows:
        if kind is not None and int(kind) != 2:
            continue
        normalised = _normalise_title(title)
        if normalised:
            user_albums[int(pk)] = normalised
    if not user_albums:
        return []

    membership: dict[int, set[int]] = {pk: set() for pk in user_albums}
    pairs = conn.execute(
        f"SELECT {quote_ident(schema.join_album_column)} AS album_pk, "
        f"{quote_ident(schema.join_asset_column)} AS asset_pk FROM {quote_ident(schema.join_table)}"
    )
    for album_pk, asset_pk in pairs:
        if album_pk in membership and asset_pk is not None:
            membership[int(album_pk)].add(int(asset_pk))

    asset_order = [asset for asset in assets if not asset.trashed]
    albums = []
    for pk, title in user_albums.items():
        members = membership.get(pk, set())
        albums.append(
            Album(
                id=f"al{pk}",
                pk=pk,
                title=title,
                asset_ids=[asset.id for asset in asset_order if asset.pk in members],
            )
        )
    albums.sort(key=lambda album: album.title.casefold())
    return albums


@dataclass
class _MomentBucket:
    title: str
    ids: list[str] = field(default_factory=list)
    pks: set[int] = field(default_factory=set)


def _build_moments(assets: list[Asset]) -> list[Moment]:
    grouped: dict[str, _MomentBucket] = {}
    for asset in assets:
        if asset.trashed or not asset.moment_title:
            continue
        key = asset.moment_title.casefold()
        bucket = grouped.setdefault(key, _MomentBucket(title=asset.moment_title))
        bucket.ids.append(asset.id)
        bucket.pks.add(asset.pk)
    moments = []
    for bucket in grouped.values():
        moments.append(
            Moment(
                id=f"mo{min(bucket.pks)}",
                title=bucket.title,
                asset_ids=list(bucket.ids),
            )
        )
    moments.sort(key=lambda moment: moment.title.casefold())
    return moments


def _resolve_files(
    assets: list[Asset], file_map: Mapping[str, str], progress: Progress | None = None
) -> None:
    lower_map = {path.lower(): file_id for path, file_id in file_map.items()}
    total = len(assets)

    def lookup(relative_path: str) -> str | None:
        return file_map.get(relative_path) or lower_map.get(relative_path.lower())

    for index, asset in enumerate(assets):
        asset.file_id = lookup(asset.rel_path)
        directory = asset.directory
        asset.thumb_file_id = lookup(f"Media/PhotoData/Thumbnails/V2/{directory}/{asset.filename}/5005.JPG")
        if asset.is_live:
            base = asset.filename.rsplit(".", 1)[0]
            asset.live_video_file_id = lookup(f"Media/{directory}/{base}.MOV") or lookup(
                f"Media/{directory}/{base}.mov"
            )
        if asset.has_adjustments:
            base = asset.filename.rsplit(".", 1)[0]
            asset.edited_file_id = lookup(f"Media/{directory}/{base}.AAE") or lookup(
                f"Media/{directory}/{base}.aae"
            )
        if progress and (index % 250 == 0 or index == total - 1):
            progress("resolving", index + 1, total)


def load_photos(
    db_path: str | Path,
    file_map: Mapping[str, str],
    progress: Progress | None = None,
) -> tuple[list[Asset], list[Album], list[Moment]]:
    """Load a Photos.sqlite file into assets, user albums and place/moment groups."""
    conn = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only = ON")
        schema = detect_schema(conn)
        assets = _read_assets(conn, schema)
        if progress:
            progress("reading", len(assets), len(assets))
        albums = _load_albums(conn, schema, assets)
        _resolve_files(assets, file_map, progress)
        moments = _build_moments(assets)
        return assets, albums, moments
    finally:
        conn.close()
