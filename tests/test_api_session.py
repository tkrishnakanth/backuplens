"""Contract tests for backup discovery, adding folders, session open/close."""

from __future__ import annotations

import logging
from pathlib import Path

from backend.app import create_app
from tests.api_fixtures import PASSWORD, app_config, auth_headers
from tests.backup_fixtures import make_backup


def client(tmp_path: Path, **overrides):
    app = create_app(app_config(tmp_path, **overrides))
    return app.test_client(), app


def test_add_backup_folder_persists_in_config(tmp_path: Path) -> None:
    backup = make_backup(tmp_path)
    test_client, app = client(tmp_path)
    response = test_client.post(
        "/api/backups/add", headers=auth_headers(), json={"path": str(backup)}
    )
    assert response.status_code == 201
    assert response.get_json()["backup"]["iosVersion"] == "17.0"
    store = app.extensions["backuplens"].config_store
    assert str(backup.resolve()) in store.extra_backup_paths()


def test_add_backup_rejects_non_backup(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/backups/add", headers=auth_headers(), json={"path": str(plain)}
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "not_a_backup"


def test_add_backup_requires_path(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post("/api/backups/add", headers=auth_headers(), json={})
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "bad_request"


def test_session_is_closed_initially(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    payload = test_client.get("/api/session", headers=auth_headers()).get_json()
    assert payload == {"open": False, "backup": None, "indexState": "idle", "progress": None}


def test_open_wrong_password(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "wrong_password"


def test_open_unknown_backup(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/session/open", headers=auth_headers(), json={"backupId": "missing", "password": "x"}
    )
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "backup_not_found"


def test_open_requires_backup_id(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post("/api/session/open", headers=auth_headers(), json={})
    assert response.status_code == 400


def test_open_then_already_open_then_close(tmp_path: Path) -> None:
    test_client, app = client(tmp_path)
    first = test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": PASSWORD},
    )
    assert first.status_code == 200
    assert first.get_json()["open"] is True
    assert first.get_json()["indexState"] in ("building", "ready")
    assert "password" not in str(first.get_json()).lower()

    second = test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": PASSWORD},
    )
    assert second.status_code == 409
    assert second.get_json()["error"]["code"] == "already_open"

    closed = test_client.post("/api/session/close", headers=auth_headers(), json={})
    assert closed.status_code == 200
    assert closed.get_json()["open"] is False
    assert app.extensions["backuplens"].session_manager.session is None


def test_password_never_appears_in_logs(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.DEBUG)
    test_client, _ = client(tmp_path)
    test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": "wrong-secret-value"},
    )
    test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": PASSWORD},
    )
    assert "wrong-secret-value" not in caplog.text
    assert PASSWORD not in caplog.text


def test_session_snapshot_contains_no_secret(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": PASSWORD},
    )
    snapshot = test_client.get("/api/session", headers=auth_headers()).get_json()
    assert "password" not in str(snapshot).lower()
