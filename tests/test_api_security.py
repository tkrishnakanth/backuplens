"""Contract tests for token, Host/Origin, CSP, gzip and the error model."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

from backend.api.security import CSP
from backend.app import create_app
from tests.api_fixtures import TOKEN, app_config, auth_headers


def client(tmp_path: Path, **overrides):
    app = create_app(app_config(tmp_path, **overrides))
    return app.test_client(), app


def test_api_without_token_is_rejected(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/backups")
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "unauthorized"


def test_api_with_wrong_token_is_rejected(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/backups", headers={"X-BackupLens-Token": "nope"})
    assert response.status_code == 401


def test_api_with_token_header_works(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/backups", headers=auth_headers())
    assert response.status_code == 200
    assert response.get_json()["backups"][0]["id"] == "backup-one"


def test_launch_url_sets_cookie_and_redirects_without_token(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get(f"/?t={TOKEN}")
    assert response.status_code == 302
    assert response.headers["Location"] == "/"
    cookies = response.headers.getlist("Set-Cookie")
    assert any("bl_token=" in cookie for cookie in cookies)
    assert any("HttpOnly" in cookie for cookie in cookies)
    assert any("SameSite=Strict" in cookie for cookie in cookies)

    # The test client keeps the cookie for the next request.
    assert test_client.get("/api/backups").status_code == 200


def test_bad_host_is_rejected(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/backups", headers=auth_headers(Host="evil.example"))
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "bad_host"


def test_bad_origin_on_post_is_rejected(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/session/close",
        headers=auth_headers(Origin="http://evil.example"),
        json={},
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "bad_origin"


def test_allowed_origin_on_post_is_accepted(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/session/close",
        headers=auth_headers(Origin="http://localhost:5000"),
        json={},
    )
    assert response.status_code == 200


def test_sec_fetch_cross_site_is_rejected(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.post(
        "/api/session/close",
        headers=auth_headers(**{"Sec-Fetch-Site": "cross-site"}),
        json={},
    )
    assert response.status_code == 403


def test_security_headers_and_csp(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/backups", headers=auth_headers())
    assert response.headers["Content-Security-Policy"] == CSP
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_gzip_json_when_requested(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path, GZIP_MIN_BYTES=0)
    response = test_client.get(
        "/api/backups", headers=auth_headers(**{"Accept-Encoding": "gzip"})
    )
    assert response.status_code == 200
    assert response.headers.get("Content-Encoding") == "gzip"
    decoded = gzip.decompress(response.data)
    assert json.loads(decoded)["backups"][0]["id"] == "backup-one"


def test_api_404_uses_json_envelope(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    response = test_client.get("/api/does-not-exist", headers=auth_headers())
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_version_endpoint(tmp_path: Path) -> None:
    test_client, _ = client(tmp_path)
    payload = test_client.get("/version", headers=auth_headers()).get_json()
    assert payload["name"] == "BackupLens"
    assert payload["version"]


def test_token_never_appears_in_logs(tmp_path: Path, caplog) -> None:
    test_client, _ = client(tmp_path)
    test_client.get(f"/?t={TOKEN}")
    test_client.get("/api/backups", headers=auth_headers())
    assert TOKEN not in caplog.text
