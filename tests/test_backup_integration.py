"""Integration tests against the real backup (skipped without BACKUP_PATH/BACKUP_PASSWORD)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from backend.backup import open_backup
from backend.backup.errors import BadDestination, WrongPassword
from iphone_backup_decrypt import EncryptedBackup

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def real_session(backup_credentials):
    path, password = backup_credentials
    session = open_backup(path, password, with_size=False)
    yield session
    session.close()


def _close_library(library: EncryptedBackup) -> None:
    try:
        library._cleanup()
    finally:
        for attr in ("_temporary_folder", "_temp_manifest_db_conn", "_temp_decrypted_manifest_db_path"):
            if hasattr(library, attr):
                setattr(library, attr, None)


def test_real_backup_metadata(real_session) -> None:
    info = real_session.info
    assert info.encrypted is True
    assert info.device_name
    assert info.product_type
    assert info.ios_version
    assert real_session.is_encrypted is True
    assert real_session.manifest_scalar("SELECT count(*) FROM Files") > 50_000
    assert real_session.manifest_scalar(
        "SELECT count(*) FROM Files WHERE domain='CameraRollDomain' AND flags=1"
    ) > 4_000


def test_first_five_files_match_library_byte_for_byte(real_session, backup_credentials) -> None:
    path, password = backup_credentials
    rows = real_session.manifest_query(
        "SELECT fileID FROM Files WHERE domain='CameraRollDomain' AND flags=1 "
        "AND relativePath LIKE 'Media/DCIM/%' ORDER BY relativePath LIMIT 80"
    )
    picks = []
    for row in rows:
        record = real_session.file_record(row["fileID"])
        if 1_000 <= record.size <= 1_000_000:
            picks.append(record)
        if len(picks) == 5:
            break
    assert len(picks) == 5, "expected five small CameraRoll files"

    library = EncryptedBackup(backup_directory=path, passphrase=password)
    try:
        for record in picks:
            expected = library.extract_file_as_bytes(
                relative_path=record.relative_path, domain_like=record.domain
            )
            actual = real_session.read_file(record.file_id)
            assert actual == expected, f"mismatch for {record.relative_path}"
            assert len(actual) == record.size
    finally:
        _close_library(library)


def test_extract_file_matches_read_file(real_session, tmp_path: Path) -> None:
    rows = real_session.manifest_query(
        "SELECT fileID FROM Files WHERE domain='CameraRollDomain' AND flags=1 "
        "AND relativePath LIKE 'Media/DCIM/%' ORDER BY relativePath LIMIT 200"
    )
    record = next(
        real_session.file_record(row["fileID"])
        for row in rows
        if 0 < real_session.file_record(row["fileID"]).size <= 5_000_000
    )
    dest = tmp_path / "one.bin"
    real_session.extract_file(record.file_id, dest)
    assert dest.read_bytes() == real_session.read_file(record.file_id)
    with pytest.raises(BadDestination):
        real_session.extract_file(record.file_id, real_session.backup_dir / "should-not-exist.bin")


def test_real_wrong_password_is_typed_and_never_logged(
    backup_credentials, caplog, capsys
) -> None:
    path, password = backup_credentials
    caplog.set_level(logging.DEBUG)
    with pytest.raises(WrongPassword):
        open_backup(path, password + "-definitely-wrong")
    captured = capsys.readouterr()
    combined = caplog.text + captured.out + captured.err
    assert password not in combined


def test_reads_do_not_modify_the_backup(real_session, tmp_path: Path) -> None:
    rows = real_session.manifest_query(
        "SELECT fileID FROM Files WHERE domain='CameraRollDomain' AND flags=1 "
        "ORDER BY relativePath LIMIT 3"
    )
    records = [real_session.file_record(row["fileID"]) for row in rows]
    before = {
        str(record.backup_path): (record.backup_path.stat().st_size, record.backup_path.stat().st_mtime)
        for record in records
    }
    manifest_before = real_session.manifest_path.stat().st_mtime

    for record in records:
        real_session.read_file(record.file_id, max_bytes=200_000_000)
        real_session.extract_file(record.file_id, tmp_path / record.file_id)

    for path, signature in before.items():
        stat = Path(path).stat()
        assert (stat.st_size, stat.st_mtime) == signature
    assert real_session.manifest_path.stat().st_mtime == manifest_before
