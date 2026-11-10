"""Unit tests for Session: file access, path safety, threading and secrets."""

from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path

import pytest
from backend.backup.errors import (
    BadDestination,
    ManifestMissing,
    PayloadMissing,
    PayloadTooLarge,
    SessionClosed,
    WrongPassword,
)
from backend.backup.session import open_backup
from tests.backup_fixtures import UDID, make_backup

FILE_ID = "ab" * 20
SECRET = "Super-Secret-Backup-Passphrase-42"


class FakeEncryptedBackup:
    """Records which thread touched the 'library'; mimics clearing its passphrase."""

    instances: list[FakeEncryptedBackup] = []
    threads: set[int] = set()

    def __init__(self, *, backup_directory: str, passphrase: bytes) -> None:
        self.backup_directory = backup_directory
        self.passphrase = passphrase
        self.threads.add(threading.get_ident())
        FakeEncryptedBackup.instances.append(self)

    def test_decryption(self) -> bool:
        self.threads.add(threading.get_ident())
        self.passphrase = None  # type: ignore[assignment]
        return True

    def save_manifest_file(self, output_filename: str) -> None:
        self.threads.add(threading.get_ident())
        shutil.copy(Path(self.backup_directory) / "Manifest.db", output_filename)

    def _cleanup(self) -> None:
        self.threads.add(threading.get_ident())


class WrongPasswordBackup:
    def __init__(self, *, backup_directory: str, passphrase: bytes) -> None:
        self.passphrase = passphrase

    def test_decryption(self) -> bool:
        from iphone_backup_decrypt.exceptions import IncorrectPassphraseError

        raise IncorrectPassphraseError("Failed to decrypt keys: incorrect passphrase?")


@pytest.fixture
def synthetic_backup(tmp_path: Path) -> Path:
    return make_backup(tmp_path)


@pytest.fixture
def encrypted_backup(tmp_path: Path) -> Path:
    return make_backup(tmp_path, encrypted=True)


def test_open_unencrypted_and_read_files(synthetic_backup: Path) -> None:
    with open_backup(synthetic_backup) as session:
        assert session.is_encrypted is False
        assert session.info.device_name == "Test iPhone"
        assert session.manifest_scalar("SELECT count(*) FROM Files") == 2

        record = session.file_record(FILE_ID)
        assert record.relative_path == "Media/DCIM/TESTAPPLE/TEST_0001.JPG"
        assert record.size == len(b"hello backup payload\n")

        assert session.read_file(FILE_ID) == b"hello backup payload\n"


def test_extract_file_writes_bytes_and_mtime(synthetic_backup: Path, tmp_path: Path) -> None:
    dest = tmp_path / "export" / "photo.jpg"
    with open_backup(synthetic_backup) as session:
        returned = session.extract_file(FILE_ID, dest)
        assert returned == dest
        assert dest.read_bytes() == b"hello backup payload\n"
        assert int(dest.stat().st_mtime) == 1_600_000_000
        assert not Path(str(dest) + ".part").exists()


def test_extract_refuses_destination_inside_backup(synthetic_backup: Path) -> None:
    with open_backup(synthetic_backup) as session:
        with pytest.raises(BadDestination):
            session.extract_file(FILE_ID, synthetic_backup / "export.bin")


def test_invalid_and_unknown_file_ids(synthetic_backup: Path) -> None:
    with open_backup(synthetic_backup) as session:
        with pytest.raises(PayloadMissing):
            session.file_record("../../../etc/passwd")
        with pytest.raises(PayloadMissing):
            session.read_file("00" * 20)


def test_missing_payload_is_typed(synthetic_backup: Path) -> None:
    payload = synthetic_backup / FILE_ID[:2] / FILE_ID
    payload.unlink()
    with open_backup(synthetic_backup) as session:
        with pytest.raises(PayloadMissing):
            session.read_file(FILE_ID)


def test_read_file_size_guard(synthetic_backup: Path) -> None:
    with open_backup(synthetic_backup) as session:
        with pytest.raises(PayloadTooLarge):
            session.read_file(FILE_ID, max_bytes=3)


def test_manifest_missing(tmp_path: Path) -> None:
    folder = tmp_path / UDID
    folder.mkdir()
    with pytest.raises(ManifestMissing):
        open_backup(folder)


def test_encrypted_without_password_is_wrong_password(tmp_path: Path) -> None:
    folder = make_backup(tmp_path, encrypted=True)
    with pytest.raises(WrongPassword):
        open_backup(folder, None)


def test_library_calls_stay_on_one_worker_thread(encrypted_backup: Path) -> None:
    FakeEncryptedBackup.threads = set()
    session = open_backup(encrypted_backup, SECRET, backup_factory=FakeEncryptedBackup)
    try:
        assert len(FakeEncryptedBackup.threads) == 1
        worker = next(iter(FakeEncryptedBackup.threads))
        assert worker != threading.get_ident()
        assert any(
            thread.name.startswith("backuplens-decrypt") for thread in threading.enumerate()
        )
    finally:
        session.close()


def test_session_drops_password_reference(encrypted_backup: Path) -> None:
    session = open_backup(encrypted_backup, SECRET, backup_factory=FakeEncryptedBackup)
    try:
        dumped = repr({key: value for key, value in vars(session).items() if key != "_library"})
        assert SECRET not in dumped
        assert not any("password" in key.lower() for key in vars(session))
    finally:
        session.close()


def test_wrong_password_never_appears_in_logs_or_output(
    encrypted_backup: Path, caplog, capsys
) -> None:
    caplog.set_level(logging.DEBUG)
    with pytest.raises(WrongPassword) as excinfo:
        open_backup(encrypted_backup, SECRET, backup_factory=WrongPasswordBackup)
    captured = capsys.readouterr()
    assert SECRET not in caplog.text
    assert SECRET not in captured.out
    assert SECRET not in captured.err
    assert SECRET not in str(excinfo.value)


def test_close_removes_temp_and_blocks_queries(synthetic_backup: Path) -> None:
    session = open_backup(synthetic_backup)
    temp_dir = session.manifest_path.parent
    session.close()
    assert session.closed
    assert not temp_dir.exists()
    with pytest.raises(SessionClosed):
        session.manifest_query("SELECT 1")
    session.close()  # idempotent
