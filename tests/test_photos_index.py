"""Unit tests for the normalised photo library index (both schema variants)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from backend.photos.index import LibraryIndex, build_index
from backend.photos.loader import load_photos
from tests.photos_fixtures import demo_file_map, make_photos_db


def build(tmp_path: Path, *, variant: str = "ZASSET", minimal: bool = False):
    db = make_photos_db(tmp_path / "Photos.sqlite", variant=variant, minimal=minimal)
    assets, albums, moments = load_photos(db, demo_file_map())
    return LibraryIndex(assets, albums, moments)


@pytest.fixture
def index(tmp_path: Path) -> LibraryIndex:
    return build(tmp_path)


def test_asset_order_and_mapping(index: LibraryIndex) -> None:
    assert [asset.pk for asset in index.assets] == list(range(1, 10))
    first = index.asset("a1")
    assert first is not None
    assert first.filename == "TEST_0001.HEIC"
    assert first.file_id == "11" * 20
    assert first.thumb_file_id == "01" * 20
    assert first.live_video_file_id == "aa" * 20
    assert first.edited_file_id == "bb" * 20
    assert first.tz_offset == 3600
    assert first.width == 4032 and first.height == 3024
    assert first.size == 1_278_801
    assert first.lat == pytest.approx(16.3)
    assert first.moment_title == "Place A"
    assert first.in_camera_roll is True


def test_category_counts(index: LibraryIndex) -> None:
    counts = {row["key"]: row["count"] for row in index.sidebar()["categories"]}
    assert counts == {
        "all": 9,
        "camera_roll": 7,
        "photos": 7,
        "videos": 1,
        "favorites": 1,
        "live": 1,
        "portrait": 1,
        "panoramas": 1,
        "timelapse": 1,
        "slomo": 1,
        "screenshots": 1,
        "hidden": 1,
        "trashed": 1,
    }


def test_albums_and_moments(index: LibraryIndex) -> None:
    sidebar = index.sidebar()
    albums = {album["title"]: album["count"] for album in sidebar["albums"]}
    assert albums == {"Album A": 2, "Album B": 0}
    moments = {moment["title"]: moment["count"] for moment in sidebar["moments"]}
    assert moments == {"Place B": 2, "Place A": 1}
    assert [moment["title"] for moment in sidebar["moments"]] == ["Place A", "Place B"]
    assert index.query(album="al10")[0].pk == 1
    assert len(index.query(album="al10")) == 2
    assert len(index.query(moment="mo2")) == 2


def test_filters_and_search(index: LibraryIndex) -> None:
    assert len(index.query(scope="camera_roll", media_type="video")) == 1
    assert len(index.query(scope="photos", media_type="video")) == 0
    assert len(index.query(scope="all")) == 8  # trashed hidden from the All grid
    assert [asset.pk for asset in index.query(q="uuid")] == [4]
    assert len(index.query(scope="photos", limit=2)) == 2
    from_ts = index.asset("a2").taken_at if index.asset("a2") else None
    assert from_ts is not None
    recent = index.query(scope="all", from_ts=from_ts)
    assert [asset.id for asset in recent] == ["a1", "a2"]
    with pytest.raises(KeyError):
        index.query(scope="nope")  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        index.query(album="missing")


def test_compact_rows_and_detail(index: LibraryIndex) -> None:
    rows = index.compact(index.query(scope="all", limit=1))
    assert rows[0][0] == "a1"
    assert rows[0][3] == "p"
    assert rows[0][6] & 1  # favorite flag
    detail = index.asset_detail(index.asset("a1"))  # type: ignore[arg-type]
    assert detail["filename"] == "TEST_0001.HEIC"
    assert detail["takenAtIso"].endswith("Z")
    assert detail["albums"] == ["Album A"]
    assert detail["moment"] == "Place A"
    assert detail["liveVideoFileId"] == "aa" * 20


def test_date_groups_use_timezone(index: LibraryIndex) -> None:
    groups = index.date_groups(index.query(scope="all", limit=1))
    assert len(groups) == 1
    assert groups[0]["date"] == "2023-03-08"
    assert groups[0]["label"].startswith("Wed, Mar 8")


def test_older_generic_asset_variant(tmp_path: Path) -> None:
    generic = build(tmp_path, variant="ZGENERICASSET")
    assert len(generic.assets) == 9
    counts = {row["key"]: row["count"] for row in generic.sidebar()["categories"]}
    assert counts["camera_roll"] == 7
    assert counts["portrait"] == 1


def test_minimal_schema_falls_back_to_subtype_and_directory(tmp_path: Path) -> None:
    minimal = build(tmp_path, minimal=True)
    counts = {row["key"]: row["count"] for row in minimal.sidebar()["categories"]}
    assert counts["all"] == 4
    assert counts["camera_roll"] == 3
    assert counts["photos"] == 3
    assert counts["videos"] == 1
    assert counts["portrait"] == 1  # ZKINDSUBTYPE=3 fallback
    assert counts["screenshots"] == 0
    assert minimal.sidebar()["albums"] == []
    assert minimal.sidebar()["moments"] == []
    assert minimal.asset("a1").tz_offset is None  # type: ignore[union-attr]


class FakeSession:
    def __init__(self, db_path: Path, work_dir: Path) -> None:
        self.db_path = db_path
        self.temp_dir = work_dir
        self.stages: list[str] = []

    def find_file_id(self, relative_path: str, domain: str | None = None) -> str | None:
        if relative_path == "Media/PhotoData/Photos.sqlite":
            return "ff" * 20
        return None

    def extract_file(self, file_id: str, dest_path) -> Path:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.db_path, dest)
        return dest

    def manifest_query(self, sql: str, params=()):
        return [
            {"fileID": file_id, "relativePath": rel_path}
            for rel_path, file_id in demo_file_map().items()
        ]


def test_build_index_extracts_and_reports_progress(tmp_path: Path) -> None:
    db = make_photos_db(tmp_path / "Photos.sqlite")
    session = FakeSession(db, tmp_path / "work")
    stages: list[str] = []

    def progress(stage: str, done: int, total: int) -> None:
        stages.append(stage)

    index = build_index(session, progress)
    assert len(index.assets) == 9
    assert index.asset("a1").file_id == "11" * 20  # type: ignore[union-attr]
    assert stages[0] == "extracting"
    assert "reading" in stages
    assert "resolving" in stages
    assert stages[-1] == "ready"


def test_build_index_missing_photos_db(tmp_path: Path) -> None:
    class NoLibrarySession(FakeSession):
        def find_file_id(self, relative_path: str, domain: str | None = None) -> str | None:
            return None

    from backend.photos.errors import PhotosDatabaseMissing

    session = NoLibrarySession(make_photos_db(tmp_path / "Photos.sqlite"), tmp_path / "work")
    with pytest.raises(PhotosDatabaseMissing):
        build_index(session)
