"""Synthetic session/index objects for media tests (no real backup)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from backend.backup import FileRecord
from backend.photos import Asset, LibraryIndex


class FakeSession:
    def __init__(
        self,
        tmp_path: Path,
        files: dict[str, tuple[bytes, str]],
        *,
        encrypted: bool = False,
    ) -> None:
        self.tmp_path = tmp_path
        self.files = files
        self.is_encrypted = encrypted
        self.info = SimpleNamespace(udid="TEST-UDID")
        self.backup_dir = tmp_path / "backup"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tmp_path / "work"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self._payloads: dict[str, Path] = {}
        for file_id, (data, _relative) in files.items():
            payload = self.backup_dir / file_id[:2] / file_id
            payload.parent.mkdir(parents=True, exist_ok=True)
            payload.write_bytes(data if encrypted else data)
            self._payloads[file_id] = payload

    def read_file(self, file_id: str, *, max_bytes: int = 64 * 1024 * 1024) -> bytes:
        data, _relative = self.files[file_id]
        if len(data) > max_bytes:
            from backend.backup import PayloadTooLarge

            raise PayloadTooLarge("too large")
        return data

    def file_record(self, file_id: str) -> FileRecord:
        data, relative = self.files[file_id]
        payload = self._payloads.get(file_id)
        if payload is not None and not payload.exists():
            payload = None
        return FileRecord(
            file_id=file_id,
            domain="CameraRollDomain",
            relative_path=relative,
            size=len(data),
            mtime=1_600_000_000,
            backup_path=payload,
        )

    def extract_file(self, file_id: str, dest_path: str | Path) -> Path:
        dest = Path(dest_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.files[file_id][0])
        return dest


class FakeIndex:
    def __init__(self, assets: list[Asset]) -> None:
        self._assets = {asset.id: asset for asset in assets}

    def asset(self, asset_id: str) -> Asset | None:
        return self._assets.get(asset_id)


def make_asset(
    asset_id: str = "a1",
    *,
    file_id: str = "aa" * 20,
    filename: str = "TEST_0001.HEIC",
    directory: str = "DCIM/TESTAPPLE",
    kind: str = "photo",
    thumb_file_id: str | None = None,
    live_video_file_id: str | None = None,
    pk: int = 1,
) -> Asset:
    return Asset(
        id=asset_id,
        pk=pk,
        file_id=file_id,
        rel_path=f"Media/{directory}/{filename}",
        directory=directory,
        filename=filename,
        original_name=filename,
        kind=kind,
        taken_at=1_700_000_000,
        tz_offset=3600,
        thumb_file_id=thumb_file_id,
        live_video_file_id=live_video_file_id,
    )


def index_of(*assets: Asset) -> LibraryIndex:
    return LibraryIndex(list(assets), [], [])
