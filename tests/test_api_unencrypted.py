"""F-BKP-04: open a non-encrypted backup through the HTTP API (synthetic backup)."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app
from backend.backup.plists import read_backup_info
from tests.backup_fixtures import make_backup


def test_open_unencrypted_backup_without_password(tmp_path: Path) -> None:
    backup = make_backup(tmp_path)
    info = read_backup_info(backup, with_size=False)
    app = create_app(
        {
            "TESTING": True,
            "TOKEN": "t",
            "PORT": 5000,
            "DISCOVERY": lambda extra_paths=(), *, with_size=True: [info],
            "CONFIG_STORE": None,
            "CONFIG_PATH": tmp_path / "config.json",
            "DISCOVERY_WITH_SIZE": False,
            "CACHE_DIR": tmp_path / "cache",
            "INDEX_BUILDER": lambda session, progress=None: None,
        }
    )
    client = app.test_client()
    headers = {"X-BackupLens-Token": "t"}
    try:
        response = client.post(
            "/api/session/open",
            headers=headers,
            json={"backupId": backup.name},
        )
        assert response.status_code == 200
        assert response.get_json()["open"] is True
        assert response.get_json()["backup"]["encrypted"] is False
    finally:
        app.extensions["backuplens"].session_manager.close()
        app.extensions["backuplens"].jobs.close()
