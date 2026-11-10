"""Build small synthetic Photos.sqlite databases that imitate iOS variants."""

from __future__ import annotations

import sqlite3
from pathlib import Path

FULL_SCHEMA = """
CREATE TABLE {asset} (
    Z_PK INTEGER PRIMARY KEY,
    Z_ENT INTEGER,
    Z_OPT INTEGER,
    ZDIRECTORY TEXT,
    ZFILENAME TEXT,
    ZKIND INTEGER,
    ZKINDSUBTYPE INTEGER,
    ZDATECREATED REAL,
    ZADDEDDATE REAL,
    ZFAVORITE INTEGER,
    ZHIDDEN INTEGER,
    ZTRASHEDSTATE INTEGER,
    ZPLAYBACKSTYLE INTEGER,
    ZSAVEDASSETTYPE INTEGER,
    ZDEPTHTYPE INTEGER,
    ZWIDTH INTEGER,
    ZHEIGHT INTEGER,
    ZDURATION REAL,
    ZLATITUDE REAL,
    ZLONGITUDE REAL,
    ZHASADJUSTMENTS INTEGER,
    ZMOMENT INTEGER,
    ZVISIBILITYSTATE INTEGER,
    ZORIENTATION INTEGER
);
CREATE TABLE ZADDITIONALASSETATTRIBUTES (
    Z_PK INTEGER PRIMARY KEY,
    ZASSET INTEGER,
    ZORIGINALFILENAME TEXT,
    ZORIGINALFILESIZE INTEGER,
    ZTIMEZONEOFFSET INTEGER,
    ZORIGINALWIDTH INTEGER,
    ZORIGINALHEIGHT INTEGER
);
CREATE TABLE ZGENERICALBUM (Z_PK INTEGER PRIMARY KEY, ZTITLE TEXT, ZKIND INTEGER);
CREATE TABLE Z_26ASSETS (Z_26ALBUMS INTEGER, Z_3ASSETS INTEGER);
CREATE TABLE ZMOMENT (Z_PK INTEGER PRIMARY KEY, ZTITLE TEXT, ZTIMEZONEOFFSET INTEGER);
"""

MINIMAL_SCHEMA = """
CREATE TABLE {asset} (
    Z_PK INTEGER PRIMARY KEY,
    ZDIRECTORY TEXT,
    ZFILENAME TEXT,
    ZKIND INTEGER,
    ZKINDSUBTYPE INTEGER,
    ZDATECREATED REAL,
    ZTRASHEDSTATE INTEGER
);
"""


def make_photos_db(path: Path, *, variant: str = "ZASSET", minimal: bool = False) -> Path:
    conn = sqlite3.connect(path)
    try:
        schema = MINIMAL_SCHEMA if minimal else FULL_SCHEMA
        conn.executescript(schema.format(asset=variant))
        if minimal:
            rows = [
                (1, "DCIM/TESTAPPLE", "TEST_0001.HEIC", 0, 3, 700000000.0, 0),
                (2, "DCIM/TESTAPPLE", "TEST_0002.JPG", 0, 0, 699900000.0, 0),
                (3, "DCIM/TESTAPPLE", "TEST_0003.MOV", 1, 0, 699800000.0, 0),
                (4, "PhotoData/CPLAssets/group1", "UUID.JPG", 0, 0, 699700000.0, 0),
            ]
            conn.executemany(
                f"INSERT INTO {variant} VALUES (?,?,?,?,?,?,?)", rows
            )
        else:
            rows = [
                # pk, dir, file, kind, subtype, created, fav, hidden, trashed, playback, saved, depth,
                # w, h, duration, lat, lon, hasadj, moment, visibility, orientation
                (1, "DCIM/TESTAPPLE", "TEST_0001.HEIC", 0, 2, 700000000.0, 1, 0, 0, 3, 3, 0, 4032, 3024, 0.0, 16.3, 80.4, 1, 1, 0, 6),
                (2, "DCIM/TESTAPPLE", "TEST_0002.PNG", 0, 10, 699900000.0, 0, 0, 0, 1, 3, 0, 1170, 2532, 0.0, -180.0, -180.0, 0, 2, 0, 1),
                (3, "DCIM/TESTAPPLE", "TEST_0003.MOV", 1, 0, 699800000.0, 0, 0, 0, 4, 3, 0, 1920, 1080, 5.5, -180.0, -180.0, 0, 2, 0, 1),
                (4, "PhotoData/CPLAssets/group1", "UUID.JPG", 0, 0, 699700000.0, 0, 0, 0, 1, 6, 0, 960, 1280, 0.0, -180.0, -180.0, 0, None, 0, 1),
                (5, "DCIM/TESTAPPLE", "TEST_0005.HEIC", 0, 0, 699600000.0, 0, 0, 1, 1, 3, 0, 4032, 3024, 0.0, -180.0, -180.0, 0, 1, 0, 6),
                (6, "DCIM/TESTAPPLE", "TEST_0006.HEIC", 0, 1, 699500000.0, 0, 0, 0, 1, 3, 0, 8000, 2000, 0.0, -180.0, -180.0, 0, None, 0, 1),
                (7, "DCIM/TESTAPPLE", "TEST_0007.HEIC", 0, 101, 699400000.0, 0, 0, 0, 1, 3, 0, 1920, 1080, 0.0, -180.0, -180.0, 0, None, 0, 1),
                (8, "DCIM/TESTAPPLE", "TEST_0008.HEIC", 0, 102, 699300000.0, 0, 1, 0, 1, 3, 0, 1920, 1080, 0.0, -180.0, -180.0, 0, None, 0, 1),
                (9, "DCIM/TESTAPPLE", "TEST_0009.HEIC", 0, 0, 699200000.0, 0, 0, 0, 1, 3, 1, 4032, 3024, 0.0, -180.0, -180.0, 0, None, 0, 6),
            ]
            values = [
                (
                    r[0],  # Z_PK
                    1,  # Z_ENT
                    0,  # Z_OPT
                    r[1],  # directory
                    r[2],  # filename
                    r[3],  # kind
                    r[4],  # subtype
                    r[5],  # created
                    r[5],  # ZADDEDDATE
                    r[6],  # favorite
                    r[7],  # hidden
                    r[8],  # trashed
                    r[9],  # playback
                    r[10],  # saved asset type
                    r[11],  # depth
                    r[12],  # width
                    r[13],  # height
                    r[14],  # duration
                    r[15],  # lat
                    r[16],  # lon
                    r[17],  # has adjustments
                    r[18],  # moment
                    r[19],  # visibility
                    r[20],  # orientation
                )
                for r in rows
            ]
            placeholders = ",".join(["?"] * 24)
            conn.executemany(
                f"INSERT INTO {variant} VALUES ({placeholders})",
                values,
            )
            attributes = [
                (1, 1, "TEST_0001.HEIC", 1278801, 3600, 4032, 3024),
                (2, 2, "TEST_0002.PNG", 250000, 3600, 1170, 2532),
                (3, 3, "TEST_0003.MOV", 5000000, 3600, 1920, 1080),
                (4, 4, "UUID.JPG", 150000, -3600, 960, 1280),
                (5, 5, "TEST_0005.HEIC", 900000, 3600, 4032, 3024),
                (6, 6, "TEST_0006.HEIC", 800000, 3600, 8000, 2000),
                (7, 7, "TEST_0007.HEIC", 700000, 3600, 1920, 1080),
                (8, 8, "TEST_0008.HEIC", 600000, 3600, 1920, 1080),
                (9, 9, "TEST_0009.HEIC", 500000, 3600, 4032, 3024),
            ]
            conn.executemany(
                "INSERT INTO ZADDITIONALASSETATTRIBUTES VALUES (?,?,?,?,?,?,?)", attributes
            )
            conn.executemany(
                "INSERT INTO ZGENERICALBUM VALUES (?,?,?)",
                [(10, "Album A", 2), (11, "Album B", 2), (12, "System album", 1506)],
            )
            conn.executemany(
                "INSERT INTO Z_26ASSETS VALUES (?,?)",
                [(10, 1), (10, 2), (10, 5), (12, 3)],
            )
            conn.executemany(
                "INSERT INTO ZMOMENT VALUES (?,?,?)",
                [(1, "Place A", 3600), (2, "Place B", 3600)],
            )
        conn.commit()
    finally:
        conn.close()
    return path


def demo_file_map() -> dict[str, str]:
    """Manifest fileID map for the full fixture (thumbs, live photo and AAE sidecar)."""
    mapping = {
        "Media/DCIM/TESTAPPLE/TEST_0001.HEIC": "11" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0002.PNG": "22" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0003.MOV": "33" * 20,
        "Media/PhotoData/CPLAssets/group1/UUID.JPG": "44" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0005.HEIC": "55" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0006.HEIC": "66" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0007.HEIC": "77" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0008.HEIC": "88" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0009.HEIC": "99" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0001.MOV": "aa" * 20,
        "Media/DCIM/TESTAPPLE/TEST_0001.AAE": "bb" * 20,
    }
    for index, name in enumerate(
        [
            "TEST_0001.HEIC",
            "TEST_0002.PNG",
            "TEST_0003.MOV",
            "TEST_0005.HEIC",
            "TEST_0006.HEIC",
            "TEST_0007.HEIC",
            "TEST_0008.HEIC",
            "TEST_0009.HEIC",
        ],
        start=1,
    ):
        mapping[f"Media/PhotoData/Thumbnails/V2/DCIM/TESTAPPLE/{name}/5005.JPG"] = f"{index:02d}" * 20
    mapping["Media/PhotoData/Thumbnails/V2/PhotoData/CPLAssets/group1/UUID.JPG/5005.JPG"] = "cc" * 20
    return mapping
