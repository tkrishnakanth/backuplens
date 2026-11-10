"""Runtime introspection of Photos.sqlite variants (ZASSET / ZGENERICASSET)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .errors import UnsupportedPhotosSchema


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]).upper() for row in conn.execute(f"PRAGMA table_info({quote_ident(table)})")}


def table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


@dataclass(frozen=True)
class PhotosSchema:
    asset_table: str
    asset_columns: frozenset[str]
    attributes_table: str | None
    attributes_columns: frozenset[str]
    album_table: str | None
    album_columns: frozenset[str]
    join_table: str | None
    join_album_column: str | None
    join_asset_column: str | None
    moment_table: str | None
    moment_columns: frozenset[str]

    def has(self, column: str) -> bool:
        return column.upper() in self.asset_columns

    def attr(self, column: str) -> bool:
        return column.upper() in self.attributes_columns


def detect_schema(conn: sqlite3.Connection) -> PhotosSchema:
    names = table_names(conn)
    asset_table = "ZASSET" if "ZASSET" in names else "ZGENERICASSET" if "ZGENERICASSET" in names else None
    if asset_table is None:
        raise UnsupportedPhotosSchema("No ZASSET or ZGENERICASSET table in Photos.sqlite")
    asset_columns = table_columns(conn, asset_table)
    if "Z_PK" not in asset_columns:
        raise UnsupportedPhotosSchema("The asset table has no Z_PK column")

    attributes_table = "ZADDITIONALASSETATTRIBUTES" if "ZADDITIONALASSETATTRIBUTES" in names else None
    attributes_columns = table_columns(conn, attributes_table) if attributes_table else set()
    if attributes_table and "ZASSET" not in attributes_columns:
        attributes_table, attributes_columns = None, set()

    album_table = "ZGENERICALBUM" if "ZGENERICALBUM" in names else None
    album_columns = table_columns(conn, album_table) if album_table else set()
    if album_table and "ZTITLE" not in album_columns:
        album_table, album_columns = None, set()

    join_table = join_album = join_asset = None
    for name in sorted(names):
        if not name.upper().startswith("Z_"):
            continue
        columns = table_columns(conn, name)
        album_col = next((c for c in sorted(columns) if "ALBUM" in c), None)
        asset_col = next((c for c in sorted(columns) if "ASSET" in c), None)
        if album_col and asset_col and album_col != asset_col:
            join_table, join_album, join_asset = name, album_col, asset_col
            break

    moment_table = "ZMOMENT" if "ZMOMENT" in names and "ZMOMENT" in asset_columns else None
    moment_columns = table_columns(conn, moment_table) if moment_table else set()

    return PhotosSchema(
        asset_table=asset_table,
        asset_columns=frozenset(asset_columns),
        attributes_table=attributes_table,
        attributes_columns=frozenset(attributes_columns),
        album_table=album_table,
        album_columns=frozenset(album_columns),
        join_table=join_table,
        join_album_column=join_album,
        join_asset_column=join_asset,
        moment_table=moment_table,
        moment_columns=frozenset(moment_columns),
    )
