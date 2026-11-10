"""Job status/cancel placeholders (exports and indexing attach to the same manager)."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify

from ..errors import ApiError
from ..state import AppState

bp = Blueprint("jobs", __name__, url_prefix="/api")


def _jobs():
    state: AppState = current_app.extensions["backuplens"]
    return state.jobs


@bp.get("/jobs/<job_id>")
def job_status(job_id: str):
    try:
        job = _jobs().get(job_id)
    except KeyError as exc:
        raise ApiError("job_not_found", "Unknown job id", 404) from exc
    return jsonify(job.to_dict())


@bp.post("/jobs/<job_id>/cancel")
def cancel_job(job_id: str):
    try:
        job = _jobs().cancel(job_id)
    except KeyError as exc:
        raise ApiError("job_not_found", "Unknown job id", 404) from exc
    return jsonify(job.to_dict())
