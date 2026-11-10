"""Tests for the in-memory job manager and its HTTP surface."""

from __future__ import annotations

import time
from pathlib import Path

from backend.api.jobs import JobManager
from backend.app import create_app
from tests.api_fixtures import app_config, auth_headers


def _wait_for(predicate, timeout: float = 3.0) -> bool:
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        if predicate():
            return True
        time.sleep(0.01)
    return False


def test_job_completes_and_reports_progress() -> None:
    manager = JobManager(max_workers=1)
    try:
        def runner(job):
            job.total = 2
            for index in range(2):
                job.done = index + 1
                job.current_file = f"file-{index}"

        job = manager.create("test", runner, total=2)
        assert _wait_for(lambda: manager.get(job.id).state == "done")
        payload = manager.get(job.id).to_dict()
        assert payload["done"] == 2
        assert payload["total"] == 2
        assert payload["currentFile"] is None
    finally:
        manager.close()


def test_job_cancel_is_cooperative() -> None:
    manager = JobManager(max_workers=1)
    try:
        def runner(job):
            while not job.cancelled:
                time.sleep(0.01)

        job = manager.create("test", runner)
        manager.cancel(job.id)
        assert _wait_for(lambda: manager.get(job.id).state == "cancelled")
    finally:
        manager.close()


def test_failed_job_records_message() -> None:
    manager = JobManager(max_workers=1)
    try:
        def runner(job):
            raise RuntimeError("boom")

        job = manager.create("test", runner)
        assert _wait_for(lambda: manager.get(job.id).state == "failed")
        assert "RuntimeError" in manager.get(job.id).to_dict()["message"]
    finally:
        manager.close()


def test_job_http_status_and_cancel(tmp_path: Path) -> None:
    app = create_app(app_config(tmp_path))
    test_client = app.test_client()
    manager = app.extensions["backuplens"].jobs
    try:
        def runner(job):
            while not job.cancelled:
                time.sleep(0.01)

        job = manager.create("test", runner)
        status = test_client.get(f"/api/jobs/{job.id}", headers=auth_headers())
        assert status.status_code == 200
        assert status.get_json()["jobId"] == job.id

        cancelled = test_client.post(f"/api/jobs/{job.id}/cancel", headers=auth_headers())
        assert cancelled.status_code == 200
        assert _wait_for(lambda: manager.get(job.id).state == "cancelled")

        missing = test_client.get("/api/jobs/nope", headers=auth_headers())
        assert missing.status_code == 404
        assert missing.get_json()["error"]["code"] == "job_not_found"
    finally:
        manager.close()
