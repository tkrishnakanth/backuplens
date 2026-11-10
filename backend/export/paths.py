"""Destination validation, safe path joins and conflict naming."""

from __future__ import annotations

import os
import re
from pathlib import Path

from backend.backup.errors import BadDestination

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def sanitize_component(value: str) -> str:
    cleaned = _INVALID.sub("_", value).strip().rstrip(" .")
    if not cleaned:
        cleaned = "unnamed"
    if cleaned.upper() in _RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def is_inside(child: Path, parent: Path) -> bool:
    try:
        child_real = os.path.realpath(child)
        parent_real = os.path.realpath(parent)
        return os.path.commonpath([child_real, parent_real]) == parent_real
    except (ValueError, OSError):
        return False


def prepare_destination(destination: Path, backup_dir: Path) -> Path:
    base = destination.expanduser().resolve()
    if is_inside(base, backup_dir):
        raise BadDestination("Refusing to export inside the backup folder")
    if base.exists() and not base.is_dir():
        raise BadDestination("The destination is not a folder")
    try:
        base.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BadDestination("The destination folder cannot be created") from exc
    probe = base / ".backuplens-write-test"
    try:
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as exc:
        raise BadDestination("The destination folder is not writable") from exc
    return base


def safe_join(base: Path, relative: Path | str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise BadDestination("Unsafe export path")
    candidate = base / relative_path
    base_real = os.path.realpath(base)
    candidate_real = os.path.realpath(candidate)
    try:
        if os.path.commonpath([base_real, candidate_real]) != base_real:
            raise BadDestination("Export path escapes the destination folder")
    except ValueError as exc:
        raise BadDestination("Export path escapes the destination folder") from exc
    return candidate


def resolve_conflict(path: Path, policy: str) -> Path | None:
    """Return the final path, or None when the file should be skipped."""
    if not path.exists():
        return path
    if policy == "skip":
        return None
    if policy == "overwrite":
        return path
    stem, suffix = path.stem, path.suffix
    counter = 1
    while True:
        candidate = path.with_name(f"{stem} ({counter}){suffix}")
        if not candidate.exists():
            return candidate
        counter += 1
