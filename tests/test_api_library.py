"""Contract tests for /api/library using a synthetic index."""

from __future__ import annotations

import time
from pathlib import Path

from backend.app import create_app
from backend.photos.index import LibraryIndex
from backend.photos.loader import load_photos
from tests.api_fixtures import PASSWORD, app_config, auth_headers
from tests.photos_fixtures import demo_file_map, make_photos_db

TOKEN = "test-token-123"


def _index(tmp_path: Path) -> LibraryIndex:
    db = make_photos_db(tmp_path / "Photos.sqlite")
    assets, albums, moments = load_photos(db, demo_file_map())
    return LibraryIndex(assets, albums, moments)


def _client(tmp_path: Path, index: LibraryIndex, **overrides):
    config = app_config(
        tmp_path,
        INDEX_BUILDER=lambda session, progress=None: index,
        **overrides,
    )
    app = create_app(config)
    return app.test_client(), app


def _open_and_wait(test_client, app, expected: str = "ready") -> None:
    test_client.post(
        "/api/session/open",
        headers=auth_headers(),
        json={"backupId": "backup-one", "password": PASSWORD},
    )
    deadline = time.perf_counter() + 5
    while time.perf_counter() < deadline:
        state = test_client.get("/api/session", headers=auth_headers()).get_json()
        if state["indexState"] == expected:
            return
        time.sleep(0.01)
    raise AssertionError(f"index never reached {expected}: {state}")


def test_library_requires_ready_index(tmp_path: Path) -> None:
    test_client, _ = _client(tmp_path, _index(tmp_path))
    response = test_client.get("/api/library/sidebar", headers=auth_headers())
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "index_not_ready"


def test_sidebar_counts(tmp_path: Path) -> None:
    test_client, app = _client(tmp_path, _index(tmp_path))
    try:
        _open_and_wait(test_client, app)
        payload = test_client.get("/api/library/sidebar", headers=auth_headers()).get_json()
        counts = {row["key"]: row["count"] for row in payload["categories"]}
        assert counts["all"] == 9
        assert counts["camera_roll"] == 7
        assert counts["trashed"] == 1
        assert payload["albums"][0]["title"] == "Album A"
        assert [moment["title"] for moment in payload["moments"]] == ["Place A", "Place B"]
        assert payload["assetCount"] == 9
    finally:
        app.extensions["backuplens"].session_manager.close()


def test_assets_compact_and_filters(tmp_path: Path) -> None:
    test_client, app = _client(tmp_path, _index(tmp_path))
    try:
        _open_and_wait(test_client, app)
        payload = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"scope": "all"}
        ).get_json()
        assert payload["v"] == 1
        assert payload["count"] == 8
        first = payload["items"][0]
        assert first[0] == "a1"
        assert first[1] == "TEST_0001.HEIC"
        assert first[3] == "p"
        assert len(first) == 10

        videos = test_client.get(
            "/api/library/assets",
            headers=auth_headers(),
            query_string={"scope": "photos", "type": "video"},
        ).get_json()
        assert videos["count"] == 0

        album = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"album": "al10"}
        ).get_json()
        assert album["count"] == 2

        moment = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"moment": "mo2"}
        ).get_json()
        assert moment["count"] == 2
    finally:
        app.extensions["backuplens"].session_manager.close()


def test_assets_validation_errors(tmp_path: Path) -> None:
    test_client, app = _client(tmp_path, _index(tmp_path))
    try:
        _open_and_wait(test_client, app)
        bad_type = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"type": "audio"}
        )
        assert bad_type.status_code == 400
        bad_scope = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"scope": "nope"}
        )
        assert bad_scope.status_code == 404
        assert bad_scope.get_json()["error"]["code"] == "scope_not_found"
        bad_album = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"album": "al999"}
        )
        assert bad_album.status_code == 404
        bad_limit = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"limit": "0"}
        )
        assert bad_limit.status_code == 400
        both = test_client.get(
            "/api/library/assets",
            headers=auth_headers(),
            query_string={"album": "al10", "moment": "mo2"},
        )
        assert both.status_code == 400
        bad_date = test_client.get(
            "/api/library/assets", headers=auth_headers(), query_string={"from": "yesterday"}
        )
        assert bad_date.status_code == 400
    finally:
        app.extensions["backuplens"].session_manager.close()


def test_asset_detail(tmp_path: Path) -> None:
    test_client, app = _client(tmp_path, _index(tmp_path))
    try:
        _open_and_wait(test_client, app)
        payload = test_client.get("/api/library/assets/a1", headers=auth_headers()).get_json()
        assert payload["id"] == "a1"
        assert payload["fileId"] == "11" * 20
        assert payload["albums"] == ["Album A"]
        assert payload["moment"] == "Place A"
        missing = test_client.get("/api/library/assets/a999", headers=auth_headers())
        assert missing.status_code == 404
        assert missing.get_json()["error"]["code"] == "asset_not_found"
    finally:
        app.extensions["backuplens"].session_manager.close()


def test_index_failure_is_reported(tmp_path: Path) -> None:
    def broken(session, progress=None):
        raise RuntimeError("cannot read Photos.sqlite")

    app = create_app(app_config(tmp_path, INDEX_BUILDER=broken))
    test_client = app.test_client()
    try:
        test_client.post(
            "/api/session/open",
            headers=auth_headers(),
            json={"backupId": "backup-one", "password": PASSWORD},
        )
        deadline = time.perf_counter() + 5
        while time.perf_counter() < deadline:
            state = test_client.get("/api/session", headers=auth_headers()).get_json()
            if state["indexState"] == "failed":
                break
            time.sleep(0.01)
        assert state["indexState"] == "failed"
        response = test_client.get("/api/library/sidebar", headers=auth_headers())
        assert response.status_code == 500
        assert response.get_json()["error"]["code"] == "index_failed"
    finally:
        app.extensions["backuplens"].session_manager.close()
