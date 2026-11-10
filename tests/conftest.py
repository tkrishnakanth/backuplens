"""Shared pytest configuration.

Loads the local, git-ignored ``.env`` so integration tests can find the real
backup without the variables being exported globally. The password is only put
into ``os.environ``; it is never printed or written by this file.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_dotenv(ROOT / ".env")


@pytest.fixture(scope="session")
def backup_credentials() -> tuple[str, str]:
    """Return (BACKUP_PATH, BACKUP_PASSWORD) or skip integration tests."""
    path = os.environ.get("BACKUP_PATH")
    password = os.environ.get("BACKUP_PASSWORD")
    if not path or not password:
        pytest.skip("BACKUP_PATH/BACKUP_PASSWORD not set")
    if not Path(path).is_dir():
        pytest.skip("BACKUP_PATH does not point to an existing folder")
    return path, password
