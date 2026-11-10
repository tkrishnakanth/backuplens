"""Unit tests for settings validation, persistence and cache reconfiguration."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app
from tests.api_fixtures import app_config, auth_headers


def test_settings_defaults_and_persistence(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    defaults = client.get("/api/settings", headers=auth_headers()).get_json()
    assert defaults["theme"] == "system"
    assert defaults["dateGroupingZone"] == "capture"
    assert defaults["thumbnailSize"] == 320
    assert defaults["cacheLocation"] == str(app.extensions["backuplens"].media_cache.root)

    updated = client.post(
        "/api/settings",
        headers=auth_headers(),
        json={
            "theme": "dark",
            "dateGroupingZone": "machine",
            "thumbnailSize": 240,
            "cacheLimitBytes": 32 * 1024 * 1024,
        },
    )
    assert updated.status_code == 200
    payload = updated.get_json()
    assert payload["theme"] == "dark"
    assert payload["thumbnailSize"] == 240
    assert app.extensions["backuplens"].media_cache.limit_bytes == 32 * 1024 * 1024

    again = client.get("/api/settings", headers=auth_headers()).get_json()
    assert again["theme"] == "dark"
    assert again["dateGroupingZone"] == "machine"


def test_settings_validation_errors(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    for body in (
        {"theme": "neon"},
        {"dateGroupingZone": "mars"},
        {"thumbnailSize": 10},
        {"cacheLimitBytes": 1},
        {"cacheLocation": "relative/path"},
    ):
        response = client.post("/api/settings", headers=auth_headers(), json=body)
        assert response.status_code == 400, body
        assert response.get_json()["error"]["code"] == "bad_request"


def test_cache_location_can_change(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    state = app.extensions["backuplens"]
    old_root = state.media_cache.root
    old_root.mkdir(parents=True, exist_ok=True)
    (old_root / "junk.bin").write_bytes(b"x")
    new_root = tmp_path / "new-cache"

    response = client.post(
        "/api/settings", headers=auth_headers(), json={"cacheLocation": str(new_root)}
    )
    assert response.status_code == 200
    assert state.media_cache.root == new_root
    assert new_root.is_dir()
    assert not (old_root / "junk.bin").exists()
