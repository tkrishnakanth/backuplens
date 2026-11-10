"""Helpers that build tiny synthetic iOS backups for unit tests."""

from __future__ import annotations

import plistlib
import sqlite3
from datetime import datetime
from pathlib import Path

UDID = "DEMO-UDID-00000001"


def file_blob(payload: bytes, *, mtime: float | None = 1_600_000_000.0) -> bytes:
    """Build a Manifest.db ``file`` blob in the NSKeyedArchiver shape FilePlist expects."""
    data = {"Size": len(payload), "ProtectionClass": 3, "Birth": mtime}
    if mtime is not None:
        data["LastModified"] = mtime
    archive = {
        "$version": 100000,
        "$archiver": "NSKeyedArchiver",
        "$top": {"root": plistlib.UID(1)},
        "$objects": ["$null", data],
    }
    return plistlib.dumps(archive, fmt=plistlib.FMT_BINARY)


def make_backup(
    root: Path,
    *,
    udid: str = UDID,
    encrypted: bool = False,
    last_backup: str = "2020-01-01T00:00:00",
    ios_version: str = "17.0",
) -> Path:
    """Create a minimal unencrypted backup with one readable CameraRoll file."""
    folder = root / udid
    folder.mkdir(parents=True)
    info = {
        "Device Name": "Test iPhone",
        "Display Name": "Test iPhone",
        "Product Type": "iPhone13,3",
        "Product Version": ios_version,
        "Build Version": "TESTBUILD",
        "Serial Number": "TESTSERIAL",
        "Unique Identifier": udid,
        "Last Backup Date": datetime.fromisoformat(last_backup),
    }
    (folder / "Info.plist").write_bytes(plistlib.dumps(info))
    (folder / "Manifest.plist").write_bytes(
        plistlib.dumps({"IsEncrypted": encrypted, "Version": "10.0"})
    )

    payload = b"hello backup payload\n"
    file_id = "ab" * 20
    conn = sqlite3.connect(folder / "Manifest.db")
    try:
        conn.execute(
            "CREATE TABLE Files (fileID TEXT, domain TEXT, relativePath TEXT, flags INTEGER, file BLOB)"
        )
        conn.execute(
            "INSERT INTO Files VALUES (?,?,?,?,?)",
            (file_id, "CameraRollDomain", "Media/DCIM/TESTAPPLE/TEST_0001.JPG", 1, file_blob(payload)),
        )
        conn.execute(
            "INSERT INTO Files VALUES (?,?,?,?,?)",
            ("cd" * 20, "HomeDomain", "Library/Preferences/test.plist", 1, file_blob(b"plain")),
        )
        conn.commit()
    finally:
        conn.close()

    payload_dir = folder / file_id[:2]
    payload_dir.mkdir()
    (payload_dir / file_id).write_bytes(payload)
    plain_dir = folder / ("cd" * 20)[:2]
    plain_dir.mkdir()
    (plain_dir / ("cd" * 20)).write_bytes(b"plain")
    return folder


def add_directory_row(folder: Path, file_id: str, domain: str, relative_path: str) -> None:
    conn = sqlite3.connect(folder / "Manifest.db")
    try:
        conn.execute(
            "INSERT INTO Files VALUES (?,?,?,?,?)",
            (file_id, domain, relative_path, 2, file_blob(b"", mtime=None)),
        )
        conn.commit()
    finally:
        conn.close()
