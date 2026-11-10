"""End-to-end API test against the real backup (integration marker)."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path

import pytest
from backend.app import create_app
from backend.backup.discovery import list_backups

pytestmark = pytest.mark.integration
TOKEN = "integration-token"


@pytest.fixture
def real_app(tmp_path: Path, backup_credentials):
    app = create_app(
        {
            "TESTING": True,
            "TOKEN": TOKEN,
            "PORT": 5000,
            "DISCOVERY": list_backups,
            "CONFIG_PATH": tmp_path / "config.json",
            "DISCOVERY_WITH_SIZE": False,
            "CACHE_DIR": tmp_path / "cache",
        }
    )
    yield app
    app.extensions["backuplens"].session_manager.close()
    app.extensions["backuplens"].jobs.close()



def _reference_counts():
    """Exact reference counts are local-only; tests skip them when the file is absent."""
    path = os.environ.get("BACKUPLENS_REFERENCE_COUNTS")
    if not path or not Path(path).is_file():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None

def _headers() -> dict[str, str]:
    return {"X-BackupLens-Token": TOKEN}


def _open_real(client, target, password) -> dict:
    opened = client.post(
        "/api/session/open",
        headers=_headers(),
        json={"backupId": target["id"], "password": password},
    )
    assert opened.status_code == 200
    body = opened.get_json()
    assert body["open"] is True
    assert body["backup"]["id"] == target["id"]

    deadline = time.perf_counter() + 60
    state = body
    while time.perf_counter() < deadline and state["indexState"] == "building":
        time.sleep(0.05)
        state = client.get("/api/session", headers=_headers()).get_json()
    assert state["indexState"] == "ready", state
    return state


def test_real_backup_open_and_close(real_app, backup_credentials, caplog) -> None:
    path, password = backup_credentials
    caplog.set_level(logging.DEBUG)
    client = real_app.test_client()

    listing = client.get("/api/backups", headers=_headers())
    assert listing.status_code == 200
    backups = listing.get_json()["backups"]
    assert backups, "no backups discovered"
    target = next((item for item in backups if item["path"] == str(Path(path).resolve())), backups[0])
    assert target["encrypted"] is True
    assert target["iosVersion"]

    wrong = client.post(
        "/api/session/open",
        headers=_headers(),
        json={"backupId": target["id"], "password": password + "-wrong"},
    )
    assert wrong.status_code == 401
    assert wrong.get_json()["error"]["code"] == "wrong_password"

    _open_real(client, target, password)

    sidebar = client.get("/api/library/sidebar", headers=_headers()).get_json()
    counts = {row["key"]: row["count"] for row in sidebar["categories"]}
    reference = _reference_counts()
    if reference:
        assert counts == reference["categories"], "counts differ from the local reference file"
        if reference.get("albums"):
            albums = {album["title"]: album["count"] for album in sidebar["albums"]}
            assert albums == reference["albums"]
    else:
        assert counts["all"] >= counts["trashed"]
        assert counts["all"] >= counts["photos"]
        assert counts["all"] >= counts["videos"]
        assert counts["trashed"] >= 0 and counts["hidden"] >= 0

    assets = client.get(
        "/api/library/assets", headers=_headers(), query_string={"scope": "all", "limit": 5}
    ).get_json()
    assert assets["count"] == 5
    assert len(assets["items"][0]) == 10
    asset_id = assets["items"][0][0]

    thumb = client.get(f"/api/media/{asset_id}/thumb?size=320", headers=_headers())
    assert thumb.status_code == 200
    assert thumb.headers["Content-Type"] == "image/jpeg"
    assert thumb.data.startswith(b"\xff\xd8")
    assert "immutable" in thumb.headers["Cache-Control"]
    thumb.close()

    preview = client.get(f"/api/media/{asset_id}/preview", headers=_headers())
    assert preview.status_code == 200
    assert preview.data.startswith(b"\xff\xd8")
    preview.close()

    partial = client.get(
        f"/api/media/{asset_id}/original",
        headers={**_headers(), "Range": "bytes=0-99"},
    )
    assert partial.status_code == 206
    assert len(partial.data) == 100
    assert partial.headers["Content-Range"].startswith("bytes 0-99/")
    assert partial.headers["Accept-Ranges"] == "bytes"
    partial.close()

    live_list = client.get(
        "/api/library/assets", headers=_headers(), query_string={"scope": "live", "limit": 1}
    ).get_json()
    assert live_list["count"] == 1
    live_id = live_list["items"][0][0]
    live = client.get(
        f"/api/media/{live_id}/live",
        headers={**_headers(), "Range": "bytes=0-49"},
    )
    assert live.status_code == 206
    assert len(live.data) == 50
    live.close()

    videos = client.get(
        "/api/library/assets", headers=_headers(), query_string={"scope": "videos", "limit": 1}
    ).get_json()
    video_id = videos["items"][0][0]
    video = client.get(
        f"/api/media/{video_id}/original",
        headers={**_headers(), "Range": "bytes=0-499"},
    )
    assert video.status_code == 206
    assert len(video.data) == 500
    assert video.headers["Content-Type"].startswith("video/")
    video.close()

    # Throughput: first 100 thumbnails cold, then the same 100 warm.
    hundred = client.get(
        "/api/library/assets", headers=_headers(), query_string={"scope": "all", "limit": 100}
    ).get_json()["items"]
    start = time.perf_counter()
    for row in hundred:
        response = client.get(f"/api/media/{row[0]}/thumb?size=320", headers=_headers())
        assert response.status_code == 200
        response.close()
    cold = time.perf_counter() - start
    start = time.perf_counter()
    for row in hundred:
        response = client.get(f"/api/media/{row[0]}/thumb?size=320", headers=_headers())
        assert response.status_code == 200
        response.close()
    warm = time.perf_counter() - start
    print(f"\n100 thumbnails: cold={cold:.2f}s warm={warm:.2f}s")
    assert warm < cold

    stats = client.get("/api/cache/stats", headers=_headers()).get_json()
    assert stats["files"] > 0
    cleared = client.post("/api/cache/clear", headers=_headers())
    assert cleared.status_code == 200
    assert client.get("/api/cache/stats", headers=_headers()).get_json()["files"] == 0

    closed = client.post("/api/session/close", headers=_headers(), json={})
    assert closed.get_json()["open"] is False
    assert password not in caplog.text


def test_index_page_is_served_with_csp(real_app) -> None:
    client = real_app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "BackupLens" in response.get_data(as_text=True)
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]
