"""Backup core: discovery, plist metadata, unlock, manifest and file access.

Public interface (mirrored in ARCHITECTURE.md §3):

* :func:`list_backups` -> ``list[BackupInfo]``
* :func:`open_backup` -> :class:`Session`
* :meth:`Session.manifest_query`, :meth:`Session.file_record`,
  :meth:`Session.read_file`, :meth:`Session.extract_file`, :meth:`Session.close`
"""

from __future__ import annotations

from .discovery import default_backup_roots, list_backups
from .errors import (
    BackupError,
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
from .plists import read_backup_info
from .session import MAX_IN_MEMORY_BYTES, Session, open_backup

__all__ = [
    "MAX_IN_MEMORY_BYTES",
    "BackupError",
    "BackupInfo",
    "BadDestination",
    "FileRecord",
    "ManifestMissing",
    "NotABackup",
    "PayloadMissing",
    "PayloadTooLarge",
    "Session",
    "SessionClosed",
    "UnsupportedVersion",
    "WrongPassword",
    "default_backup_roots",
    "list_backups",
    "open_backup",
    "read_backup_info",
]
