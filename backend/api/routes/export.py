"""Export routes: folder export jobs, ZIP download and the native folder picker."""

from __future__ import annotations

from flask import Blueprint, Response, current_app, jsonify, request, stream_with_context

from backend.export import (
    build_plan,
    create_zip,
    estimate_size,
    parse_request,
    prepare_destination,
    run_export,
)
from backend.export.errors import NoItems, ZipTooLarge
from backend.export.folders import pick_folder
from backend.export.paths import sanitize_component

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("export", __name__, url_prefix="/api")
ZIP_MAX_ITEMS = 500
ZIP_MAX_BYTES = 2 * 1024 * 1024 * 1024


def _state() -> AppState:
    return current_app.extensions["backuplens"]


def _session_and_index():
    manager = _state().session_manager
    if manager.session is None or manager.index is None:
        raise ApiError("session_not_open", "Open a backup and wait for the library index", 409)
    return manager.session, manager.index


@bp.post("/export")
def start_export():
    session, index = _session_and_index()
    payload = request.get_json(silent=True) or {}
    try:
        export_request = parse_request(payload)
    except ValueError as exc:
        raise ApiError("bad_request", str(exc), 400) from exc

    destination = prepare_destination(export_request.destination, session.backup_dir)
    plan = build_plan(index, session, export_request)
    if not plan.items:
        raise NoItems("There are no files to export in this selection")

    job = _state().jobs.create(
        "export",
        lambda current: run_export(current, plan, destination, export_request.options, session),
        total=len(plan.items),
    )
    return jsonify({"jobId": job.id, "total": len(plan.items)}), 202


@bp.post("/export/zip")
def export_zip():
    session, index = _session_and_index()
    payload = request.get_json(silent=True) or {}
    ids = payload.get("ids")
    if not isinstance(ids, list) or not ids or not all(isinstance(value, str) for value in ids):
        raise ApiError("bad_request", "ids must be a non-empty array of strings", 400)
    unique_ids = list(dict.fromkeys(ids))
    if len(unique_ids) > ZIP_MAX_ITEMS:
        raise ZipTooLarge(f"ZIP downloads are limited to {ZIP_MAX_ITEMS} items; use a folder export")
    if estimate_size(index, unique_ids) > ZIP_MAX_BYTES:
        raise ZipTooLarge("ZIP downloads are limited to 2 GB; use a folder export")

    zip_path, count = create_zip(session, index, unique_ids)
    size = zip_path.stat().st_size
    folder = zip_path.parent
    download_name = sanitize_component("BackupLens-export.zip")

    def generate():
        try:
            with open(zip_path, "rb") as handle:
                while chunk := handle.read(1024 * 256):
                    yield chunk
        finally:
            import shutil

            shutil.rmtree(folder, ignore_errors=True)

    response = Response(stream_with_context(generate()), mimetype="application/zip")
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    response.headers["Content-Length"] = str(size)
    response.headers["X-File-Count"] = str(count)
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.post("/fs/pick-folder")
def pick_folder_route():
    payload = request.get_json(silent=True) or {}
    initial = payload.get("initialDir") if isinstance(payload.get("initialDir"), str) else None
    path = pick_folder(initial)
    return jsonify({"path": path or None})

