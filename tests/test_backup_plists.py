"""Unit tests for plist metadata parsing and folder sizing."""

from __future__ import annotations

from pathlib import Path

import pytest
from backend.backup.errors import ManifestMissing, NotABackup
from backend.backup.plists import (
    folder_size,
    is_backup_folder,
    is_encrypted,
    load_plist,
    read_backup_info,
)
from tests.backup_fixtures import make_backup


def test_read_backup_info_from_synthetic_backup(tmp_path: Path) -> None:
    folder = make_backup(tmp_path)
    info = read_backup_info(folder, with_size=False)
    assert info.device_name == "Test iPhone"
    assert info.product_type == "iPhone13,3"
    assert info.ios_version == "17.0"
    assert info.udid == folder.name
    assert info.encrypted is False
    assert info.to_dict()["lastBackup"] == "2020-01-01T00:00:00Z"


def test_folder_size_counts_nested_files(tmp_path: Path) -> None:
    folder = make_backup(tmp_path)
    size = folder_size(folder)
    assert size > 100
    assert size == sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())


def test_is_backup_folder_and_encryption_flag(tmp_path: Path) -> None:
    folder = make_backup(tmp_path)
    assert is_backup_folder(folder)
    assert is_encrypted(folder) is False
    (folder / "Manifest.db").unlink()
    assert is_backup_folder(folder) is False


def test_missing_plist_raises_typed_error(tmp_path: Path) -> None:
    folder = make_backup(tmp_path)
    (folder / "Manifest.plist").unlink()
    with pytest.raises(ManifestMissing):
        load_plist(folder / "Manifest.plist")
    with pytest.raises(ManifestMissing):
        read_backup_info(folder)


def test_unreadable_plist_raises_not_a_backup(tmp_path: Path) -> None:
    folder = make_backup(tmp_path)
    (folder / "Manifest.plist").write_bytes(b"not a plist")
    with pytest.raises(NotABackup):
        load_plist(folder / "Manifest.plist")
