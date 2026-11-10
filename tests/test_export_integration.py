"""Integration tests for export against the real backup (20-file byte comparison)."""

from __future__ import annotations

import time
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from backend.app import create_app
from backend.backup.discovery import list_backups

pytestmark = pytest.mark.integration
TOKEN = "export-integration-token"


def _headers() -> dict[str, str]:
    return {"X-BackupLens-Token": TOKEN}


@pytest.fixture(scope="module")
def real_app(tmp_path_factory, backup_credentials):
    base = tmp_path_factory.mktemp("export-app")
    app = create_app(
        {
            "TESTING": True,
            "TOKEN": TOKEN,
            "PORT": 5000,
            "DISCOVERY": list_backups,
            "CONFIG_PATH": base / "config.json",
            "CACHE_DIR": base / "cache",
            "DISCOVERY_WITH_SIZE": False,
        }
    )
    client = app.test_client()
    backups = client.get("/api/backups", headers=_headers()).get_json()["backups"]
    path, password = backup_credentials
    target = next((item for item in backups if item["path"] == str(Path(path).resolve())), backups[0])
    response = client.post(
        "/api/session/open",
        headers=_headers(),
        json={"backupId": target["id"], "password": password},
    )
    assert response.status_code == 200
    state = response.get_json()
    deadline = time.perf_counter() + 60
    while time.perf_counter() < deadline and state["indexState"] == "building":
        time.sleep(0.05)
        state = client.get("/api/session", headers=_headers()).get_json()
    assert state["indexState"] == "ready", state
    yield app
    app.extensions["backuplens"].session_manager.close()
    app.extensions["backuplens"].jobs.close()


@pytest.fixture
def client(real_app):
    return real_app.test_client()


def _wait_job(client, job_id: str, timeout: float = 180.0) -> dict:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        job = client.get(f"/api/jobs/{job_id}", headers=_headers()).get_json()
        if job["state"] not in ("queued", "running"):
            return job
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} did not finish")


def _assets(client, scope: str, limit: int) -> list[list]:
    return client.get(
        "/api/library/assets", headers=_headers(), query_string={"scope": scope, "limit": limit}
    ).get_json()["items"]


def _detail(client, asset_id: str) -> dict:
    return client.get(f"/api/library/assets/{asset_id}", headers=_headers()).get_json()


def _small_ids(client, count: int) -> list[str]:
    ids = [row[0] for row in _assets(client, "all", 400)]
    small = []
    seen_names = set()
    for asset_id in ids:
        detail = _detail(client, asset_id)
        if not detail.get("fileId") or not detail.get("size"):
            continue
        if detail["size"] >= 3_000_000:
            continue
        if detail["filename"] in seen_names:
            continue
        seen_names.add(detail["filename"])
        small.append(asset_id)
        if len(small) == count:
            break
    assert len(small) == count
    return small


def _run_export(client, payload: dict) -> dict:
    response = client.post("/api/export", headers=_headers(), json=payload)
    assert response.status_code == 202, response.get_data(as_text=True)
    return _wait_job(client, response.get_json()["jobId"])


def test_export_20_files_byte_identical(real_app, client, tmp_path: Path) -> None:
    ids = _small_ids(client, 20)
    destination = tmp_path / "export20"
    job = _run_export(
        client,
        {
            "ids": ids,
            "destination": str(destination),
            "options": {"layout": "flat", "onConflict": "rename", "setFileDates": True},
        },
    )
    assert job["state"] == "done", job
    assert job["done"] == 20
    assert job["errors"] == []

    session = real_app.extensions["backuplens"].session_manager.session
    for asset_id in ids:
        detail = _detail(client, asset_id)
        output = destination / detail["filename"]
        assert output.is_file(), detail["filename"]
        assert output.read_bytes() == session.read_file(detail["fileId"])
        assert int(output.stat().st_mtime) == detail["takenAt"]
    report = (destination / "export-report.txt").read_text(encoding="utf-8")
    assert "Exported: 20" in report
    assert not list(destination.rglob("*.part"))


def test_album_scope_and_conflict_policies(client, tmp_path: Path) -> None:
    destination = tmp_path / "conflicts"
    ids = _small_ids(client, 1)
    first = _run_export(
        client,
        {
            "ids": ids,
            "destination": str(destination),
            "options": {"onConflict": "skip"},
        },
    )
    assert first["done"] == 1
    filename = _detail(client, ids[0])["filename"]
    original = destination / filename
    assert original.exists()

    skipped = _run_export(
        client,
        {
            "ids": ids,
            "destination": str(destination),
            "options": {"onConflict": "skip"},
        },
    )
    assert skipped["state"] == "done"
    assert len([path for path in destination.iterdir() if path.is_file() and path.suffix != ".txt"]) == 1

    renamed = _run_export(
        client,
        {
            "ids": ids,
            "destination": str(destination),
            "options": {"onConflict": "rename"},
        },
    )
    assert renamed["state"] == "done"
    assert (destination / f"{original.stem} (1){original.suffix}").exists()

    # scope form: pick a small category that exists in the current library
    sidebar = client.get("/api/library/sidebar", headers=_headers()).get_json()
    small_category = next(
        (row for row in sidebar["categories"] if 0 < row["count"] <= 50 and row["key"] != "all"),
        None,
    )
    if small_category is None:
        pytest.skip("no small category available in this backup")
    scope_destination = tmp_path / "scope-export"
    scope_job = _run_export(
        client,
        {
            "scope": {"kind": "category", "key": small_category["key"], "type": "all"},
            "destination": str(scope_destination),
            "options": {},
        },
    )
    assert scope_job["state"] == "done"
    assert scope_job["done"] == scope_job["total"]


def test_live_video_and_edited_companions(client, tmp_path: Path) -> None:
    live_assets = _assets(client, "live", 1)
    if not live_assets:
        pytest.skip("no Live Photos in this backup")
    live = live_assets[0][0]
    detail = _detail(client, live)
    destination = tmp_path / "live"
    job = _run_export(
        client,
        {
            "ids": [live],
            "destination": str(destination),
            "options": {"includeLiveVideo": True},
        },
    )
    assert job["done"] == 2
    names = {path.name for path in destination.iterdir() if path.is_file() and path.suffix != ".txt"}
    assert detail["filename"] in names
    assert any(name.upper().endswith(".MOV") for name in names)


def test_heic_to_jpeg(client, tmp_path: Path) -> None:
    candidates = [row[0] for row in _assets(client, "photos", 400)]
    chosen = None
    for asset_id in candidates:
        detail = _detail(client, asset_id)
        if detail["filename"].upper().endswith((".HEIC", ".HEIF")) and (detail["size"] or 0) < 20_000_000:
            chosen = detail
            break
    assert chosen is not None
    destination = tmp_path / "jpeg"
    job = _run_export(
        client,
        {
            "ids": [chosen["id"]],
            "destination": str(destination),
            "options": {"convertHeicToJpeg": True},
        },
    )
    assert job["done"] == 1
    output = destination / f"{Path(chosen['filename']).stem}.JPG"
    assert output.exists()
    assert output.read_bytes().startswith(b"\xff\xd8")


def test_refuses_destination_inside_backup(client, real_app, tmp_path: Path) -> None:
    backup_dir = real_app.extensions["backuplens"].session_manager.session.backup_dir
    destination = backup_dir / "should-not-exist"
    response = client.post(
        "/api/export",
        headers=_headers(),
        json={"ids": _small_ids(client, 1), "destination": str(destination)},
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "bad_destination"
    assert not destination.exists()


def test_zip_stream(client, real_app) -> None:
    ids = _small_ids(client, 3)
    response = client.post("/api/export/zip", headers=_headers(), json={"ids": ids})
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/zip")
    session = real_app.extensions["backuplens"].session_manager.session
    with zipfile.ZipFile(BytesIO(response.data)) as archive:
        assert len(archive.namelist()) == 3
        contents = {archive.read(name) for name in archive.namelist()}
    expected = {session.read_file(_detail(client, asset_id)["fileId"]) for asset_id in ids}
    assert contents == expected


def test_raw_files_api(client, real_app, tmp_path: Path) -> None:
    domains = client.get("/api/files/domains", headers=_headers())
    assert domains.status_code == 200
    assert any(row["domain"] == "CameraRollDomain" for row in domains.get_json()["domains"])

    tree = client.get(
        "/api/files/tree",
        headers=_headers(),
        query_string={"domain": "CameraRollDomain", "path": "Media/DCIM"},
    )
    assert tree.status_code == 200
    names = {entry["name"] for entry in tree.get_json()["entries"]}
    assert any(name.endswith("APPLE") for name in names)

    search = client.get(
        "/api/files/search",
        headers=_headers(),
        query_string={
            "domain": "CameraRollDomain",
            "path": "Media/DCIM/%.JPG",
            "sort": "size",
            "dir": "desc",
            "limit": 5,
        },
    )
    assert search.status_code == 200
    results = search.get_json()["items"]
    assert results
    sizes = [item["size"] for item in results]
    assert sizes == sorted(sizes, reverse=True)

    file_id = results[0]["fileId"]
    download = client.get(
        f"/api/files/{file_id}/download",
        headers={**_headers(), "Range": "bytes=0-99"},
    )
    assert download.status_code == 206
    assert len(download.data) == 100
    assert "attachment" in download.headers["Content-Disposition"]
    download.close()

    destination = tmp_path / "raw-files"
    response = client.post(
        "/api/files/export",
        headers=_headers(),
        json={"ids": [item["fileId"] for item in results[:3]], "destination": str(destination)},
    )
    assert response.status_code == 202
    job = _wait_job(client, response.get_json()["jobId"])
    assert job["state"] == "done"
    assert job["done"] == len(results[:3])
    exported = [path for path in destination.rglob("*") if path.is_file() and path.name != "raw-export-report.txt"]
    assert len(exported) == len(results[:3])
    session = real_app.extensions["backuplens"].session_manager.session
    for item in results[:3]:
        record = session.file_record(item["fileId"])
        assert record.size >= 0

    traversal = client.get(
        "/api/files/tree",
        headers=_headers(),
        query_string={"domain": "CameraRollDomain", "path": "../../etc"},
    )
    assert traversal.status_code == 400
    bad_id = client.get("/api/files/not-a-file-id/download", headers=_headers())
    assert bad_id.status_code == 400


def test_cancel_mid_run(client, tmp_path: Path) -> None:
    ids = [row[0] for row in _assets(client, "all", 300)]
    destination = tmp_path / "cancel"
    response = client.post(
        "/api/export",
        headers=_headers(),
        json={"ids": ids, "destination": str(destination), "options": {"onConflict": "rename"}},
    )
    assert response.status_code == 202
    job_id = response.get_json()["jobId"]
    time.sleep(0.2)
    client.post(f"/api/jobs/{job_id}/cancel", headers=_headers())
    job = _wait_job(client, job_id)
    assert job["state"] == "cancelled", job
    assert not list(destination.rglob("*.part"))
    report = (destination / "export-report.txt").read_text(encoding="utf-8")
    assert "Cancelled: yes" in report
