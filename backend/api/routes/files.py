"""Raw file explorer routes (read-only; no replace/delete)."""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.export.paths import prepare_destination
from backend.files import (
    FileBrowseError,
    ids_matching,
    is_file_id,
    list_domains,
    raw_file,
    run_raw_export,
    search,
    tree,
)

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("files", __name__, url_prefix="/api/files")


def _state() -> AppState:
    return current_app.extensions["backuplens"]


def _session():
    manager = _state().session_manager
    if manager.session is None:
        raise ApiError("session_not_open", "Open a backup first", 409)
    return manager.session


def _int_arg(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = request.args.get(name)
    if raw is None or raw == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ApiError("bad_request", f"{name} must be an integer", 400) from exc
    return max(minimum, min(maximum, value))


@bp.get("/domains")
def domains():
    return jsonify({"domains": list_domains(_session())})


@bp.get("/tree")
def tree_route():
    domain = request.args.get("domain", "")
    path = request.args.get("path", "")
    try:
        return jsonify(tree(_session(), domain, path))
    except FileBrowseError as exc:
        raise ApiError("bad_request", str(exc), 400) from exc


@bp.get("/search")
def search_route():
    try:
        result = search(
            _session(),
            domain=request.args.get("domain", ""),
            path=request.args.get("path", ""),
            sort=request.args.get("sort", "path"),
            direction=request.args.get("dir", "asc"),
            limit=_int_arg("limit", 200, 1, 5000),
            offset=_int_arg("offset", 0, 0, 10_000_000),
        )
    except FileBrowseError as exc:
        raise ApiError("bad_request", str(exc), 400) from exc
    return jsonify(result)


@bp.get("/<file_id>/download")
def download(file_id: str):
    if not is_file_id(file_id):
        raise ApiError("bad_request", "Invalid file id", 400)
    media = raw_file(_session(), _state().media_cache, file_id)
    response = send_file(
        media.path,
        mimetype=media.mimetype,
        conditional=True,
        as_attachment=True,
        download_name=media.filename,
    )
    response.headers["Cache-Control"] = "private, max-age=0"
    return response


@bp.post("/export")
def export_files():
    session = _session()
    payload = request.get_json(silent=True) or {}
    destination_raw = payload.get("destination")
    if not isinstance(destination_raw, str) or not destination_raw.strip():
        raise ApiError("bad_request", "destination is required", 400)
    destination = Path(destination_raw).expanduser()
    if not destination.is_absolute():
        raise ApiError("bad_request", "destination must be an absolute path", 400)
    destination = prepare_destination(destination, session.backup_dir)

    ids = payload.get("ids")
    if ids is not None:
        if not isinstance(ids, list) or not ids or not all(isinstance(value, str) for value in ids):
            raise ApiError("bad_request", "ids must be a non-empty array of strings", 400)
        file_ids = [value for value in dict.fromkeys(ids) if is_file_id(value)]
        if not file_ids:
            raise ApiError("bad_request", "No valid file ids", 400)
    else:
        domain = payload.get("domain") or ""
        path = payload.get("path") or ""
        if not isinstance(domain, str) or not isinstance(path, str):
            raise ApiError("bad_request", "domain and path must be strings", 400)
        file_ids = ids_matching(session, domain=domain, path=path)
        if not file_ids:
            raise ApiError("no_items", "No files match this query", 400)

    conflict = payload.get("onConflict", "rename")
    if conflict not in ("skip", "rename", "overwrite"):
        raise ApiError("bad_request", "onConflict is invalid", 400)
    job = _state().jobs.create(
        "raw-export",
        lambda current: run_raw_export(current, file_ids, destination, session, conflict),
        total=len(file_ids),
    )
    return jsonify({"jobId": job.id, "total": len(file_ids)}), 202
