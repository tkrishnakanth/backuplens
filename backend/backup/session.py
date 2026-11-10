"""Backup session: unlock once, query the manifest from any thread, decrypt files.

Threading contract (ARCHITECTURE.md §5): the ``iphone_backup_decrypt`` object and its
SQLite connection are created **and used only** on a single worker thread. Every
library call is submitted to that worker. Metadata queries use separate read-only
SQLite connections, one per call/thread, against a decrypted manifest copy.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from iphone_backup_decrypt import EncryptedBackup
from iphone_backup_decrypt.exceptions import (
    BackupNotEncryptedError,
    IncorrectPassphraseError,
    NotABackupFolderError,
    UnsafeBackupError,
)
from iphone_backup_decrypt.utils import FilePlist, aes_decrypt_chunked, backup_file_path

from .errors import (
    BadDestination,
    ManifestMissing,
    NotABackup,
    PayloadMissing,
    PayloadTooLarge,
    SessionClosed,
    UnsupportedVersion,
    WrongPassword,
)
from .models import BackupInfo, FileRecord
from .plists import MANIFEST_DB, MANIFEST_PLIST, load_plist, read_backup_info

_FILE_ID = re.compile(r"[0-9a-fA-F]{40}")
MAX_IN_MEMORY_BYTES = 64 * 1024 * 1024


def _restrict_permissions(path: Path) -> None:
    """Best-effort user-only permissions for a temp folder (POSIX; no-op on FAT)."""
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass


def _validate_folder(folder: Path) -> None:
    if not folder.is_dir():
        raise NotABackup("The backup folder does not exist")
    if not (folder / MANIFEST_PLIST).is_file() or not (folder / MANIFEST_DB).is_file():
        raise ManifestMissing("The folder is not an iOS backup (Manifest.plist/Manifest.db missing)")


def _worker(executor: ThreadPoolExecutor, fn, *args):
    return executor.submit(fn, *args).result()


def _check_manifest(manifest_path: Path) -> None:
    try:
        conn = sqlite3.connect(f"{manifest_path.as_uri()}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='Files'"
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        raise UnsupportedVersion("The Manifest database is not readable") from exc
    if not row:
        raise UnsupportedVersion("The Manifest database has no Files table")


def open_backup(
    path: str | Path,
    password: str | None = None,
    *,
    with_size: bool = False,
    backup_factory=EncryptedBackup,
) -> Session:
    """Open an iOS backup (encrypted or not) and return a :class:`Session`.

    ``password`` is only used during unlock and is never stored on the session.
    ``backup_factory`` is injectable for tests.
    """
    folder = Path(path).expanduser().resolve()
    _validate_folder(folder)
    manifest_plist = load_plist(folder / MANIFEST_PLIST)
    encrypted = bool(manifest_plist.get("IsEncrypted"))
    info = read_backup_info(folder, with_size=with_size)

    temp_dir = Path(tempfile.mkdtemp(prefix="backuplens-session-"))
    _restrict_permissions(temp_dir)
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="backuplens-decrypt")
    library = None
    try:
        if encrypted:
            if not password:
                raise WrongPassword("This backup is encrypted; a password is required")
            secret = bytearray(password.encode("utf-8"))

            def _unlock() -> None:
                nonlocal library
                library = backup_factory(backup_directory=str(folder), passphrase=bytes(secret))
                library.test_decryption()
                library.save_manifest_file(str(temp_dir / MANIFEST_DB))

            try:
                _worker(executor, _unlock)
            finally:
                for index in range(len(secret)):
                    secret[index] = 0
                del secret
        else:
            _worker(executor, shutil.copy2, folder / MANIFEST_DB, temp_dir / MANIFEST_DB)
        _check_manifest(temp_dir / MANIFEST_DB)
    except IncorrectPassphraseError as exc:
        _discard(executor, temp_dir)
        raise WrongPassword("Incorrect backup password") from exc
    except NotABackupFolderError as exc:
        _discard(executor, temp_dir)
        raise NotABackup("The folder is not an iOS backup") from exc
    except (BackupNotEncryptedError, UnsafeBackupError) as exc:
        _discard(executor, temp_dir)
        raise UnsupportedVersion(f"Unsupported backup: {type(exc).__name__}") from exc
    except BaseException:
        _discard(executor, temp_dir)
        raise

    return Session(
        backup_dir=folder,
        info=info,
        manifest_path=temp_dir / MANIFEST_DB,
        temp_dir=temp_dir,
        executor=executor,
        library=library,
        encrypted=encrypted,
    )


def _discard(executor: ThreadPoolExecutor, temp_dir: Path) -> None:
    try:
        executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:  # pragma: no cover - Python < 3.9
        executor.shutdown(wait=False)
    shutil.rmtree(temp_dir, ignore_errors=True)


class Session:
    """An unlocked backup. Close it to remove all temporary decrypted data."""

    def __init__(
        self,
        *,
        backup_dir: Path,
        info: BackupInfo,
        manifest_path: Path,
        temp_dir: Path,
        executor: ThreadPoolExecutor,
        library: EncryptedBackup | None,
        encrypted: bool,
    ) -> None:
        self._backup_dir = backup_dir
        self._info = info
        self._manifest_path = manifest_path
        self._temp_dir = temp_dir
        self._executor = executor
        self._library = library
        self._encrypted = encrypted
        self._closed = threading.Event()

    # ------------------------------------------------------------------ state
    @property
    def backup_dir(self) -> Path:
        return self._backup_dir

    @property
    def info(self) -> BackupInfo:
        return self._info

    @property
    def manifest_path(self) -> Path:
        return self._manifest_path

    @property
    def temp_dir(self) -> Path:
        """Session-private scratch folder (decrypted manifest lives here too)."""
        return self._temp_dir

    @property
    def is_encrypted(self) -> bool:
        return self._encrypted

    @property
    def closed(self) -> bool:
        return self._closed.is_set()

    def _ensure_open(self) -> None:
        if self._closed.is_set():
            raise SessionClosed("The backup session is closed")

    # -------------------------------------------------------------- manifest
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"{self._manifest_path.as_uri()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        return conn

    def manifest_query(self, sql: str, params: tuple | list = ()) -> list[dict[str, Any]]:
        """Run one read-only query against the decrypted manifest copy."""
        self._ensure_open()
        conn = self._connect()
        try:
            rows = conn.execute(sql, tuple(params)).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def manifest_scalar(self, sql: str, params: tuple | list = ()) -> Any:
        rows = self.manifest_query(sql, params)
        if not rows:
            return None
        return next(iter(rows[0].values()))

    def iter_manifest(self, sql: str, params: tuple | list = ()):
        """Yield manifest rows one at a time without materialising the whole result."""
        self._ensure_open()
        conn = self._connect()
        try:
            for row in conn.execute(sql, tuple(params)):
                yield dict(row)
        finally:
            conn.close()

    def file_record(self, file_id: str) -> FileRecord:
        """Look up one regular file by its 40-hex fileID and parse its plist metadata."""
        self._ensure_open()
        if not isinstance(file_id, str) or not _FILE_ID.fullmatch(file_id):
            raise PayloadMissing("Invalid file id")
        file_id = file_id.lower()
        rows = self.manifest_query(
            "SELECT fileID, domain, relativePath, flags, file FROM Files "
            "WHERE fileID=? AND flags=1 LIMIT 1",
            (file_id,),
        )
        if not rows:
            raise PayloadMissing("File not found in the backup manifest")
        row = rows[0]
        blob = row.get("file")
        size = 0
        mtime = None
        if blob:
            try:
                parsed = FilePlist(blob)
                size = parsed.filesize
                mtime = parsed.mtime
            except Exception:  # noqa: BLE001 - malformed bplist must not crash listing
                size = 0
        return FileRecord(
            file_id=file_id,
            domain=str(row["domain"]),
            relative_path=str(row["relativePath"]),
            size=size,
            mtime=mtime,
            flags=int(row["flags"]),
            backup_path=Path(backup_file_path(str(self._backup_dir), file_id)),
            plist_blob=blob if isinstance(blob, bytes) else None,
        )

    def find_file_id(self, relative_path: str, domain: str | None = None) -> str | None:
        """Return the fileID for a domain/relative path, or None."""
        self._ensure_open()
        if domain:
            rows = self.manifest_query(
                "SELECT fileID FROM Files WHERE relativePath=? AND domain=? AND flags=1 LIMIT 1",
                (relative_path, domain),
            )
        else:
            rows = self.manifest_query(
                "SELECT fileID FROM Files WHERE relativePath=? AND flags=1 LIMIT 1",
                (relative_path,),
            )
        return str(rows[0]["fileID"]) if rows else None

    # ----------------------------------------------------------------- files
    def _is_inside_backup(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self._backup_dir)
            return True
        except (ValueError, OSError):
            return False

    def _prepare_destination(self, dest_path: str | Path) -> Path:
        dest = Path(dest_path).expanduser()
        if self._is_inside_backup(dest):
            raise BadDestination("Refusing to write inside the backup folder")
        dest.parent.mkdir(parents=True, exist_ok=True)
        return dest

    def _decrypt_to(self, record: FileRecord, dest: Path) -> None:
        """Worker-side decryption. Writes ``dest`` atomically via a ``.part`` file."""
        self._ensure_open()
        part = Path(str(dest) + ".part")
        try:
            if self._encrypted and record.backup_path is not None:
                file_plist = FilePlist(record.plist_blob) if record.plist_blob else None
                if file_plist is not None and file_plist.encryption_key is not None:
                    library = self._library
                    if library is None:
                        raise SessionClosed("The backup session is closed")
                    key = library.keybag.unwrap_key_for_class(
                        file_plist.protection_class, file_plist.encryption_key
                    )
                    aes_decrypt_chunked(
                        in_filename=str(record.backup_path), key=key, out_filepath=str(part)
                    )
                elif record.size == 0:
                    part.write_bytes(b"")
                else:
                    shutil.copyfile(record.backup_path, part)
            else:
                if record.backup_path is None:
                    raise PayloadMissing("The file has no on-disk payload")
                shutil.copyfile(record.backup_path, part)
            if record.mtime:
                os.utime(part, times=(record.mtime, record.mtime))
            os.replace(part, dest)
        finally:
            if part.exists():
                try:
                    part.unlink()
                except OSError:
                    pass

    def extract_file(self, file_id: str, dest_path: str | Path) -> Path:
        """Decrypt one file to ``dest_path`` and return the final path."""
        self._ensure_open()
        record = self.file_record(file_id)
        if record.backup_path is None or not record.backup_path.is_file():
            raise PayloadMissing("The file is missing from the backup payload")
        dest = self._prepare_destination(dest_path)
        _worker(self._executor, self._decrypt_to, record, dest)
        return dest

    def read_file(self, file_id: str, *, max_bytes: int = MAX_IN_MEMORY_BYTES) -> bytes:
        """Decrypt a file into memory. Refuses files above ``max_bytes``."""
        self._ensure_open()
        record = self.file_record(file_id)
        if record.size > max_bytes:
            raise PayloadTooLarge("File is too large to read into memory")
        if record.backup_path is None or not record.backup_path.is_file():
            raise PayloadMissing("The file is missing from the backup payload")
        handle = tempfile.NamedTemporaryFile(dir=self._temp_dir, delete=False, suffix=".bin")
        temp_path = Path(handle.name)
        handle.close()
        try:
            _worker(self._executor, self._decrypt_to, record, temp_path)
            return temp_path.read_bytes()
        finally:
            try:
                temp_path.unlink()
            except OSError:
                pass

    # ----------------------------------------------------------------- close
    def close(self) -> None:
        """Remove decrypted temporary data and stop the worker thread."""
        if self._closed.is_set():
            return
        self._closed.set()

        def _cleanup_library() -> None:
            library = self._library
            if library is None:
                return
            cleanup = getattr(library, "_cleanup", None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:  # noqa: BLE001 - cleanup must not mask close()
                    pass
            # Prevent the library's __del__ from trying to remove the folder again.
            for attr in (
                "_temporary_folder",
                "_temp_manifest_db_conn",
                "_temp_decrypted_manifest_db_path",
            ):
                if hasattr(library, attr):
                    setattr(library, attr, None)

        future = self._executor.submit(_cleanup_library)
        try:
            future.result(timeout=30)
        except Exception:  # noqa: BLE001
            pass
        self._executor.shutdown(wait=True)
        self._library = None
        shutil.rmtree(self._temp_dir, ignore_errors=True)

    def __enter__(self) -> Session:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
