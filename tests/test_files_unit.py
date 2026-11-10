"""Unit tests for the raw file explorer and raw export job."""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path

import pytest
from backend.backup import open_backup
from backend.files import (
    FileBrowseError,
    escape_like,
    ids_matching,
    is_file_id,
    list_domains,
    raw_file,
    run_raw_export,
    search,
    tree,
)
from backend.media.cache import MediaCache
from tests.backup_fixtures import file_blob, make_backup


def add_file(folder: Path, domain: str, relative: str, data: bytes, *, mtime: float = 1_700_000_000) -> str:
    file_id = f"{abs(hash((domain, relative))) % (16**40):040x}"
    conn = sqlite3.connect(folder / "Manifest.db")
    try:
        conn.execute(
            "INSERT INTO Files VALUES (?,?,?,?,?)",
            (file_id, domain, relative, 1, file_blob(data, mtime=mtime)),
        )
        conn.commit()
    finally:
        conn.close()
    payload = folder / file_id[:2] / file_id
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(data)
    return file_id


@pytest.fixture
def raw_backup(tmp_path: Path):
    folder = make_backup(tmp_path)
    files = {
        ("CameraRollDomain", "Media/DCIM/TESTAPPLE/TEST_0002.MOV"): b"video-two",
        ("CameraRollDomain", "Media/DCIM/TESTAPPLE2/TEST_0003.JPG"): b"image-three",
        ("CameraRollDomain", "Media/PhotoData/Photos.sqlite"): b"sqlite-db",
        ("HomeDomain", "Library/SMS/sms.db"): b"sms-db",
        ("AppDomainGroup-group.net.whatsapp.ExampleChat.shared", "Message/Media/a.JPG"): b"wa-image",
    }
    ids = {}
    for (domain, relative), data in files.items():
        ids[relative] = add_file(folder, domain, relative, data)
    session = open_backup(folder)
    try:
        yield session, ids
    finally:
        session.close()


def test_domains_and_tree(raw_backup) -> None:
    session, _ids = raw_backup
    domains = {row["domain"]: row["count"] for row in list_domains(session)}
    assert domains["CameraRollDomain"] >= 4
    assert domains["HomeDomain"] >= 2

    root = tree(session, "CameraRollDomain")
    names = {entry["name"]: entry for entry in root["entries"]}
    assert names["Media"]["type"] == "dir"

    media = tree(session, "CameraRollDomain", "Media")
    assert {entry["name"] for entry in media["entries"]} == {"DCIM", "PhotoData"}

    dcim = tree(session, "CameraRollDomain", "Media/DCIM")
    assert {entry["name"] for entry in dcim["entries"]} == {"TESTAPPLE", "TESTAPPLE2"}

    files = tree(session, "CameraRollDomain", "Media/DCIM/TESTAPPLE")
    entries = {entry["name"]: entry for entry in files["entries"]}
    assert entries["TEST_0002.MOV"]["size"] == len(b"video-two")
    assert entries["TEST_0002.MOV"]["mtime"] == 1_700_000_000

    with pytest.raises(FileBrowseError):
        tree(session, "CameraRollDomain", "../escape")


def test_search_filters_sorting_and_escaping(raw_backup) -> None:
    session, ids = raw_backup
    result = search(session, domain="CameraRollDomain", path="Media/DCIM/%")
    assert result["total"] >= 3
    assert all(item["domain"] == "CameraRollDomain" for item in result["items"])
    assert all(item["path"].startswith("Media/DCIM/") for item in result["items"])

    mov = search(session, domain="CameraRollDomain", path="%.mov")
    assert any(item["name"] == "TEST_0002.MOV" for item in mov["items"])

    by_size = search(session, domain="CameraRollDomain", path="Media/DCIM/%", sort="size", direction="desc")
    assert by_size["items"][0]["size"] >= by_size["items"][-1]["size"]

    by_date = search(session, domain="CameraRollDomain", path="Media/DCIM/%", sort="date", direction="asc")
    assert by_date["items"]

    home = search(session, domain="HomeDomain", path="%sms%")
    assert home["total"] == 1
    assert home["items"][0]["name"] == "sms.db"

    assert ids_matching(session, domain="CameraRollDomain", path="Media/DCIM/%")
    assert is_file_id(ids["Media/DCIM/TESTAPPLE/TEST_0002.MOV"])
    assert escape_like("50%_x\\y") == "50\\%\\_x\\\\y"


def test_raw_file_and_export(raw_backup, tmp_path: Path) -> None:
    session, ids = raw_backup
    cache = MediaCache(tmp_path / "cache")
    file_id = ids["Media/DCIM/TESTAPPLE/TEST_0002.MOV"]
    media = raw_file(session, cache, file_id)
    assert media.filename == "TEST_0002.MOV"
    assert media.path.read_bytes() == b"video-two"

    class Job:
        total = 2
        done = 0
        bytes_done = 0
        current_file = None
        errors: list[str] = []
        message = None
        cancel_event = threading.Event()

        @property
        def cancelled(self):
            return self.cancel_event.is_set()

    destination = tmp_path / "raw-export"
    destination.mkdir()
    run_raw_export(
        Job(),
        [file_id, ids["Library/SMS/sms.db"]],
        destination,
        session,
    )
    assert (destination / "CameraRollDomain" / "Media" / "DCIM" / "TESTAPPLE" / "TEST_0002.MOV").read_bytes() == b"video-two"
    assert (destination / "HomeDomain" / "Library" / "SMS" / "sms.db").read_bytes() == b"sms-db"
    assert "Exported: 2" in (destination / "raw-export-report.txt").read_text(encoding="utf-8")
