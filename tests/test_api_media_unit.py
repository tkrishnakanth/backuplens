"""Media route contract tests that do not need the real backup."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app
from tests.api_fixtures import app_config, auth_headers


def test_media_requires_an_open_session(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    response = client.get("/api/media/a1/thumb", headers=auth_headers())
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "session_not_open"


def test_cache_stats_and_clear(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    cache = app.extensions["backuplens"].media_cache
    (cache.root / "junk.bin").write_bytes(b"x" * 1024)

    stats = client.get("/api/cache/stats", headers=auth_headers()).get_json()
    assert stats["files"] == 1
    assert stats["bytes"] == 1024

    cleared = client.post("/api/cache/clear", headers=auth_headers())
    assert cleared.status_code == 200
    assert cleared.get_json()["freedBytes"] == 1024
    assert cache.stats()["files"] == 0
