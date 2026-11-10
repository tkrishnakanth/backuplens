"""Discover iOS backups in the default Windows locations plus user-added paths."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from .errors import BackupError
from .models import BackupInfo
from .plists import MANIFEST_DB, MANIFEST_PLIST, is_backup_folder, read_backup_info


def default_backup_roots() -> list[Path]:
    """Return the standard Windows backup roots that exist on this machine.

    * Apple Devices app / Microsoft Store iTunes: ``%USERPROFILE%\\Apple\\MobileSync\\Backup``
    * Classic iTunes: ``%APPDATA%\\Apple Computer\\MobileSync\\Backup``
    """
    candidates: list[Path] = []
    profile = os.environ.get("USERPROFILE")
    appdata = os.environ.get("APPDATA")
    if profile:
        candidates.append(Path(profile) / "Apple" / "MobileSync" / "Backup")
    if appdata:
        candidates.append(Path(appdata) / "Apple Computer" / "MobileSync" / "Backup")
    return [path for path in candidates if path.is_dir()]


def _looks_like_backup(folder: Path) -> bool:
    return (folder / MANIFEST_PLIST).is_file() and (folder / MANIFEST_DB).is_file()


def _iter_candidate_folders(root: Path) -> Iterable[Path]:
    try:
        with os.scandir(root) as entries:
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        yield Path(entry.path)
                except OSError:
                    continue
    except OSError:
        return


def list_backups(
    extra_paths: Iterable[str | Path] = (),
    *,
    with_size: bool = True,
) -> list[BackupInfo]:
    """List every backup found in the default roots and in ``extra_paths``.

    ``extra_paths`` entries may be either a backup folder itself or a folder that
    contains backups. Unreadable/invalid folders are skipped rather than raising,
    because a single broken backup must not hide the others.
    """
    found: list[BackupInfo] = []
    seen: set[str] = set()

    def consider(folder: Path) -> None:
        try:
            resolved = str(folder.resolve())
        except OSError:
            return
        if resolved in seen or not is_backup_folder(folder):
            return
        seen.add(resolved)
        try:
            found.append(read_backup_info(folder, with_size=with_size))
        except BackupError:
            return

    for root in default_backup_roots():
        for folder in _iter_candidate_folders(root):
            consider(folder)

    for extra in extra_paths:
        path = Path(extra).expanduser()
        if not path.exists():
            continue
        if _looks_like_backup(path):
            consider(path)
        elif path.is_dir():
            for folder in _iter_candidate_folders(path):
                consider(folder)

    found.sort(key=lambda item: (item.last_backup is None, -(item.last_backup.timestamp() if item.last_backup else 0)))
    return found
