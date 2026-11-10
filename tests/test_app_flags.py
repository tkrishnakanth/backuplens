"""Launcher flags, health/quit control and the frozen-artifact smoke test."""

from __future__ import annotations

from pathlib import Path

from backend.app import create_app, run_smoke_test
from backend.version import VERSION
from tests.api_fixtures import app_config, auth_headers


def test_version_flag(capsys) -> None:
    from backend.app import main

    assert main(["--version"]) == 0
    assert VERSION in capsys.readouterr().out


def test_health_is_unauthenticated_but_quit_is_protected(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    client = app.test_client()
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.get_json() == {"status": "ok", "name": "BackupLens", "version": VERSION}

    denied = client.post("/api/app/quit", json={})
    assert denied.status_code == 401
    bad_origin = client.post(
        "/api/app/quit", headers=auth_headers(Origin="http://evil.example"), json={}
    )
    assert bad_origin.status_code == 403
    accepted = client.post("/api/app/quit", headers=auth_headers(), json={})
    assert accepted.status_code == 200
    assert app.extensions["backuplens"].shutdown_event.is_set()


def test_data_dir_override_uses_local_config_and_cache(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    app = create_app({"TESTING": True, "TOKEN": "t", "DATA_DIR": data_dir, "DISCOVERY": lambda *a, **k: []})
    state = app.extensions["backuplens"]
    assert state.data_dir == data_dir
    assert state.config_store.path == data_dir / "config.json"
    assert state.media_cache.root == data_dir / "cache"


def test_smoke_test_decodes_bundled_heic() -> None:
    sample = Path("tests/assets/sample.heic")
    assert sample.is_file() and sample.stat().st_size > 100
    assert run_smoke_test() == 0
