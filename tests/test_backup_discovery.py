"""Unit tests for backup discovery."""

from __future__ import annotations

from pathlib import Path

from backend.backup import discovery
from tests.backup_fixtures import make_backup


def test_lists_backups_newest_first_and_skips_invalid(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "root"
    root.mkdir()
    older = make_backup(root, udid="DEMO-UDID-00000001", last_backup="2020-01-01T00:00:00")
    newer = make_backup(root, udid="DEMO-UDID-00000002", last_backup="2024-01-01T00:00:00")
    (root / "not-a-backup").mkdir()
    (root / "not-a-backup" / "Info.plist").write_bytes(b"junk")

    monkeypatch.setattr(discovery, "default_backup_roots", lambda: [])
    found = discovery.list_backups([root], with_size=False)

    assert [item.path for item in found] == [str(newer.resolve()), str(older.resolve())]


def test_accepts_a_backup_folder_directly(tmp_path: Path, monkeypatch) -> None:
    backup = make_backup(tmp_path)
    monkeypatch.setattr(discovery, "default_backup_roots", lambda: [])
    found = discovery.list_backups([backup], with_size=False)
    assert len(found) == 1
    assert found[0].udid == backup.name


def test_ignores_missing_extra_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(discovery, "default_backup_roots", lambda: [])
    assert discovery.list_backups([tmp_path / "nope"], with_size=False) == []


def test_default_backup_roots_returns_existing_directories(monkeypatch, tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    (profile / "Apple" / "MobileSync" / "Backup").mkdir(parents=True)
    monkeypatch.setenv("USERPROFILE", str(profile))
    monkeypatch.delenv("APPDATA", raising=False)
    roots = discovery.default_backup_roots()
    assert roots == [profile / "Apple" / "MobileSync" / "Backup"]
