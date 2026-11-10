"""Per-OS data, cache and log locations."""

from __future__ import annotations

import os
from pathlib import Path


def _env_path(name: str) -> Path | None:
    value = os.environ.get(name)
    return Path(value) if value else None


def default_data_dir() -> Path:
    override = _env_path("BACKUPLENS_DATA_DIR")
    if override:
        return override
    if os.name == "nt":
        base = _env_path("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return base / "BackupLens"
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Application Support" / "BackupLens"
    base = _env_path("XDG_DATA_HOME") or (Path.home() / ".local" / "share")
    return base / "backuplens"


def default_cache_dir() -> Path:
    if os.name == "nt":
        base = _env_path("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return base / "BackupLens" / "cache"
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Caches" / "BackupLens"
    base = _env_path("XDG_CACHE_HOME") or (Path.home() / ".cache")
    return base / "backuplens"


def default_log_dir() -> Path:
    return default_data_dir() / "logs"


def sys_platform() -> str:
    import sys

    return sys.platform


def ensure_private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path
