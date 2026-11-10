"""Shared fake objects for HTTP contract tests (no real backup access)."""

from __future__ import annotations

from pathlib import Path

from backend.backup import BackupInfo
from backend.backup.errors import WrongPassword

TOKEN = "test-token-123"
PASSWORD = "correct-horse-battery"


class FakeSession:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class StubIndex:
    """Minimal index used by API contract tests that do not exercise the library."""

    def sidebar(self):
        return {"categories": [], "albums": [], "moments": [], "assetCount": 0}

    def query(self, **kwargs):
        return []

    def compact(self, assets):
        return []

    def asset(self, asset_id):
        return None

    def asset_detail(self, asset):
        return {}


def fake_open(path: str, password: str | None = None):
    if password == PASSWORD:
        return FakeSession()
    raise WrongPassword("Incorrect backup password")


def fake_discovery(extra_paths=(), *, with_size: bool = True) -> list[BackupInfo]:
    return [
        BackupInfo(
            id="backup-one",
            path=str(Path("C:/Backups") / "backup-one"),
            device_name="Test iPhone",
            product_type="iPhone13,3",
            ios_version="17.0",
            udid="DEMO-UDID-00000001",
            encrypted=True,
        )
    ]


def app_config(tmp_path: Path, **overrides):
    from backend.api.config_store import ConfigStore

    config = {
        "TESTING": True,
        "TOKEN": TOKEN,
        "PORT": 5000,
        "SESSION_OPEN": fake_open,
        "INDEX_BUILDER": lambda session, progress=None: StubIndex(),
        "DISCOVERY": fake_discovery,
        "CONFIG_STORE": ConfigStore(tmp_path / "config.json"),
        "CACHE_DIR": tmp_path / "cache",
        "GZIP_MIN_BYTES": 1024,
    }
    config.update(overrides)
    return config


def auth_headers(**extra: str) -> dict[str, str]:
    headers = {"X-BackupLens-Token": TOKEN}
    headers.update(extra)
    return headers
