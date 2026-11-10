"""Read-only plist access for iOS backups."""

from __future__ import annotations

import os
import plistlib
from pathlib import Path
from typing import Any

from .errors import ManifestMissing, NotABackup
from .models import BackupInfo

INFO_PLIST = "Info.plist"
MANIFEST_PLIST = "Manifest.plist"
MANIFEST_DB = "Manifest.db"


def load_plist(path: str | Path) -> dict[str, Any]:
    """Load a binary/XML plist file and return its top-level dictionary."""
    try:
        with open(path, "rb") as handle:
            data = plistlib.load(handle)
    except FileNotFoundError as exc:
        raise ManifestMissing(f"Missing plist file: {Path(path).name}") from exc
    except (plistlib.InvalidFileException, OSError) as exc:
        raise NotABackup(f"Unreadable plist file: {Path(path).name}") from exc
    if not isinstance(data, dict):
        raise NotABackup(f"Unexpected plist content in {Path(path).name}")
    return data


def is_backup_folder(path: str | Path) -> bool:
    """Return True when a folder looks like an iOS backup (has both Manifest files)."""
    folder = Path(path)
    return folder.is_dir() and (folder / MANIFEST_PLIST).is_file() and (folder / MANIFEST_DB).is_file()


def is_encrypted(path: str | Path) -> bool:
    """Read ``IsEncrypted`` without decrypting anything."""
    manifest = load_plist(Path(path) / MANIFEST_PLIST)
    return bool(manifest.get("IsEncrypted"))


def read_backup_info(path: str | Path, *, with_size: bool = True) -> BackupInfo:
    """Build a :class:`BackupInfo` from ``Info.plist`` and ``Manifest.plist``.

    Only metadata is read; no backup file is decrypted. Missing optional keys are
    tolerated because Apple has renamed several of them over the years.
    """
    folder = Path(path).resolve()
    if not folder.is_dir():
        raise NotABackup("Backup folder does not exist")
    info = load_plist(folder / INFO_PLIST) if (folder / INFO_PLIST).is_file() else {}
    manifest = load_plist(folder / MANIFEST_PLIST)

    udid = _first(info, "Unique Identifier", "Target Identifier") or (
        folder.name if "-" in folder.name or len(folder.name) >= 40 else None
    )
    backup = BackupInfo(
        id=str(folder.name),
        path=str(folder),
        device_name=_first(info, "Device Name"),
        display_name=_first(info, "Display Name"),
        product_type=_first(info, "Product Type"),
        ios_version=_first(info, "Product Version"),
        build_version=_first(info, "Build Version"),
        serial_number=_first(info, "Serial Number"),
        imei=_first(info, "IMEI"),
        udid=udid,
        last_backup=_as_datetime(info.get("Last Backup Date")),
        encrypted=bool(manifest.get("IsEncrypted")),
        manifest_version=manifest.get("Version"),
        size_bytes=0,
    )
    if with_size:
        backup.size_bytes = folder_size(folder)
    return backup


def folder_size(folder: Path) -> int:
    """Sum the sizes of all regular files below ``folder`` (read-only, best effort)."""
    total = 0
    stack = [folder]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                    except OSError:
                        continue
        except OSError:
            continue
    return total


def _first(info: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = info.get(key)
        if value not in (None, ""):
            return str(value)
    return None


def _as_datetime(value: object):
    from datetime import datetime

    return value if isinstance(value, datetime) else None
