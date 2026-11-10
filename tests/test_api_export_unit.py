"""Export route contract tests that do not need the real backup."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app
from backend.export.errors import FolderPickerUnavailable
from tests.api_fixtures import app_config, auth_headers


def test_export_requires_session(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    response = client.post(
        "/api/export",
        headers=auth_headers(),
        json={"destination": str(tmp_path / "out"), "ids": ["a1"]},
    )
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "session_not_open"


def test_zip_requires_session(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    response = client.post("/api/export/zip", headers=auth_headers(), json={"ids": ["a1"]})
    assert response.status_code == 409


def test_folder_picker_returns_path(tmp_path: Path, monkeypatch) -> None:
    from backend.api.routes import export as export_routes

    monkeypatch.setattr(export_routes, "pick_folder", lambda initial=None: str(tmp_path))
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    response = client.post("/api/fs/pick-folder", headers=auth_headers(), json={})
    assert response.status_code == 200
    assert response.get_json()["path"] == str(tmp_path)


def test_folder_picker_unavailable_is_501(tmp_path: Path, monkeypatch) -> None:
    from backend.api.routes import export as export_routes

    def broken(initial=None):
        raise FolderPickerUnavailable("no display")

    monkeypatch.setattr(export_routes, "pick_folder", broken)
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    response = client.post("/api/fs/pick-folder", headers=auth_headers(), json={})
    assert response.status_code == 501
    assert response.get_json()["error"]["code"] == "folder_picker_unavailable"
