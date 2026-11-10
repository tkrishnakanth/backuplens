"""Unit tests for export planning, atomic writing, conflicts, layouts, report and ZIP."""

from __future__ import annotations

import threading
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from backend.backup.errors import BadDestination
from backend.export import (
    build_plan,
    create_zip,
    parse_request,
    prepare_destination,
    run_export,
    safe_join,
)
from backend.export.errors import NoItems
from backend.photos import Album, LibraryIndex
from backend.photos.dates import local_day
from PIL import Image
from tests.media_fixtures import FakeSession, index_of, make_asset


class Job:
    def __init__(self, total: int) -> None:
        self.total = total
        self.done = 0
        self.bytes_done = 0
        self.current_file = None
        self.errors: list[str] = []
        self.message = None
        self.cancel_event = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()


def jpeg_bytes(color=(40, 80, 160), size=(64, 48)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, color).save(buffer, "JPEG")
    return buffer.getvalue()


def setup(tmp_path: Path, *, live: bool = False, edited: bool = False, album: bool = False):
    file_id = "aa" * 20
    live_id = "bb" * 20
    edited_id = "cc" * 20
    files = {file_id: (jpeg_bytes(), "Media/DCIM/TESTAPPLE/TEST_0001.HEIC")}
    if live:
        files[live_id] = (b"live-movie", "Media/DCIM/TESTAPPLE/TEST_0001.MOV")
    if edited:
        files[edited_id] = (b"aae-data", "Media/DCIM/TESTAPPLE/TEST_0001.AAE")
    asset = make_asset(file_id=file_id)
    asset.size = len(files[file_id][0])
    asset.live_video_file_id = live_id if live else None
    asset.edited_file_id = edited_id if edited else None
    albums = []
    if album:
        albums.append(Album(id="al1", pk=1, title="Album A", asset_ids=[asset.id]))
    index = LibraryIndex([asset], albums, [])
    session = FakeSession(tmp_path, files)
    return index, session


def request_for(tmp_path: Path, **overrides):
    payload = {
        "destination": str(tmp_path / "out"),
        "ids": ["a1"],
        "options": {"setFileDates": True},
    }
    payload.update(overrides)
    return parse_request(payload)


def test_parse_request_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        parse_request({})
    with pytest.raises(ValueError):
        parse_request({"destination": "relative/path"})
    with pytest.raises(ValueError):
        parse_request({"destination": str(tmp_path), "options": {"layout": "nope"}})
    with pytest.raises(ValueError):
        parse_request({"destination": str(tmp_path), "ids": []})
    parsed = parse_request({"destination": str(tmp_path)})
    assert parsed.scope == {"kind": "category", "key": "all", "type": "all"}


def test_export_writes_original_and_report(tmp_path: Path) -> None:
    index, session = setup(tmp_path)
    request = request_for(tmp_path)
    plan = build_plan(index, session, request)
    assert len(plan.items) == 1
    destination = prepare_destination(request.destination, session.backup_dir)
    job = Job(len(plan.items))
    run_export(job, plan, destination, request.options, session)

    output = destination / "TEST_0001.HEIC"
    assert output.read_bytes() == jpeg_bytes()
    assert job.done == 1
    assert job.errors == []
    assert int(output.stat().st_mtime) == 1_700_000_000
    report = (destination / "export-report.txt").read_text(encoding="utf-8")
    assert "Exported: 1" in report
    assert "Cancelled: no" in report


def test_heic_to_jpeg_conversion(tmp_path: Path) -> None:
    index, session = setup(tmp_path)
    request = request_for(tmp_path, options={"convertHeicToJpeg": True})
    plan = build_plan(index, session, request)
    assert plan.items[0].filename.endswith(".JPG")
    destination = prepare_destination(request.destination, session.backup_dir)
    run_export(Job(1), plan, destination, request.options, session)
    output = destination / "TEST_0001.JPG"
    assert output.exists()
    with Image.open(output) as image:
        assert image.format == "JPEG"


def test_live_and_edited_companions(tmp_path: Path) -> None:
    index, session = setup(tmp_path, live=True, edited=True)
    request = request_for(tmp_path, options={"includeLiveVideo": True, "includeEdited": True})
    plan = build_plan(index, session, request)
    assert [item.kind for item in plan.items] == ["original", "live", "edited"]
    assert [item.filename for item in plan.items] == [
        "TEST_0001.HEIC",
        "TEST_0001.MOV",
        "TEST_0001.AAE",
    ]
    destination = prepare_destination(request.destination, session.backup_dir)
    run_export(Job(3), plan, destination, request.options, session)
    assert (destination / "TEST_0001.MOV").read_bytes() == b"live-movie"
    assert (destination / "TEST_0001.AAE").read_bytes() == b"aae-data"


def test_layouts(tmp_path: Path) -> None:
    index, session = setup(tmp_path, album=True)
    destination = prepare_destination(tmp_path / "out", session.backup_dir)

    by_date = request_for(tmp_path, options={"layout": "by-date"})
    run_export(Job(1), build_plan(index, session, by_date), destination, by_date.options, session)
    day = local_day(1_700_000_000, 3600)
    assert (destination / day[:4] / day / "TEST_0001.HEIC").exists()

    by_album = request_for(tmp_path, options={"layout": "by-album"})
    run_export(Job(1), build_plan(index, session, by_album), destination, by_album.options, session)
    assert (destination / "Album A" / "TEST_0001.HEIC").exists()

    original = request_for(tmp_path, options={"layout": "original-path"})
    run_export(Job(1), build_plan(index, session, original), destination, original.options, session)
    assert (destination / "Media" / "DCIM" / "TESTAPPLE" / "TEST_0001.HEIC").exists()


def test_conflict_policies(tmp_path: Path) -> None:
    index, session = setup(tmp_path)
    destination = prepare_destination(tmp_path / "out", session.backup_dir)
    original = destination / "TEST_0001.HEIC"
    original.write_bytes(b"old")

    skip = request_for(tmp_path, options={"onConflict": "skip"})
    job = Job(1)
    run_export(job, build_plan(index, session, skip), destination, skip.options, session)
    assert original.read_bytes() == b"old"
    assert job.done == 1

    rename = request_for(tmp_path, options={"onConflict": "rename"})
    run_export(Job(1), build_plan(index, session, rename), destination, rename.options, session)
    assert (destination / "TEST_0001 (1).HEIC").read_bytes() == jpeg_bytes()

    overwrite = request_for(tmp_path, options={"onConflict": "overwrite"})
    run_export(Job(1), build_plan(index, session, overwrite), destination, overwrite.options, session)
    assert original.read_bytes() == jpeg_bytes()


def test_cancel_stops_before_writing(tmp_path: Path) -> None:
    index, session = setup(tmp_path)
    request = request_for(tmp_path)
    destination = prepare_destination(request.destination, session.backup_dir)
    job = Job(1)
    job.cancel_event.set()
    run_export(job, build_plan(index, session, request), destination, request.options, session)
    assert not (destination / "TEST_0001.HEIC").exists()
    assert "Cancelled: yes" in (destination / "export-report.txt").read_text(encoding="utf-8")


def test_disk_full_error_is_collected(tmp_path: Path, monkeypatch) -> None:
    index, session = setup(tmp_path)
    request = request_for(tmp_path)
    destination = prepare_destination(request.destination, session.backup_dir)
    plan = build_plan(index, session, request)

    def failing_extract(file_id, dest_path):
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(session, "extract_file", failing_extract)
    job = Job(1)
    run_export(job, plan, destination, request.options, session)
    assert job.errors and "OSError" in job.errors[0]
    assert not (destination / "TEST_0001.HEIC").exists()
    assert not list(destination.rglob("*.part"))
    assert "Failed: 1" in (destination / "export-report.txt").read_text(encoding="utf-8")


def test_two_thousand_file_export_memory(tmp_path: Path) -> None:
    import tracemalloc

    files = {}
    assets = []
    for index in range(2000):
        file_id = f"{index + 1:040x}"
        filename = f"TEST_{index:05d}.JPG"
        files[file_id] = (b"x" * 1024, f"Media/DCIM/TESTAPPLE/{filename}")
        asset = make_asset(asset_id=f"a{index}", file_id=file_id, pk=index + 1, filename=filename)
        asset.size = 1024
        assets.append(asset)
    index_obj = LibraryIndex(assets, [], [])
    session = FakeSession(tmp_path, files)
    request = parse_request(
        {
            "destination": str(tmp_path / "bulk"),
            "ids": [asset.id for asset in assets],
            "options": {"onConflict": "rename"},
        }
    )
    plan = build_plan(index_obj, session, request)
    destination = prepare_destination(request.destination, session.backup_dir)
    job = Job(2000)

    tracemalloc.start()
    run_export(job, plan, destination, request.options, session)
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    assert job.done == 2000
    assert job.errors == []
    assert len([path for path in destination.iterdir() if path.suffix.upper() == ".JPG"]) == 2000
    assert peak < 100 * 1024 * 1024


def test_refuses_backup_destination_and_traversal(tmp_path: Path) -> None:
    _index, session = setup(tmp_path)
    with pytest.raises(BadDestination):
        prepare_destination(session.backup_dir / "export", session.backup_dir)
    with pytest.raises(BadDestination):
        safe_join(tmp_path / "out", "../escape.txt")
    with pytest.raises(BadDestination):
        safe_join(tmp_path / "out", "C:/absolute.txt")


def test_zip_creation_store_only_and_duplicates(tmp_path: Path) -> None:
    ids = ["aa" * 20, "bb" * 20, "cc" * 20]
    files = {
        ids[0]: (b"one", "Media/DCIM/TESTAPPLE/TEST_0001.JPG"),
        ids[1]: (b"two", "Media/DCIM/TESTAPPLE/TEST_0001.JPG"),
        ids[2]: (b"three", "Media/DCIM/TESTAPPLE/TEST_0001.JPG"),
    }
    assets = [
        make_asset(asset_id=f"a{i + 1}", file_id=file_id, pk=i + 1, filename="TEST_0001.JPG")
        for i, file_id in enumerate(ids)
    ]
    index = index_of(*assets)
    session = FakeSession(tmp_path, files)
    zip_path, count = create_zip(session, index, [asset.id for asset in assets])
    assert count == 3
    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()
        assert names == ["TEST_0001.JPG", "TEST_0001 (1).JPG", "TEST_0001 (2).JPG"]
        assert archive.read(names[0]) == b"one"
        for info in archive.infolist():
            assert info.compress_type == zipfile.ZIP_STORED
    with pytest.raises(NoItems):
        create_zip(session, index, ["missing"])
