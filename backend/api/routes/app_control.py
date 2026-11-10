"""Health and quit endpoints used by installers and the hamburger menu."""

from __future__ import annotations

import time

from flask import Blueprint, current_app, jsonify

from backend.version import APP_NAME, VERSION

from ..state import AppState

bp = Blueprint("app_control", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "name": APP_NAME, "version": VERSION})


@bp.post("/app/quit")
def quit_app():
    state: AppState = current_app.extensions["backuplens"]
    state.last_request = time.time()
    state.shutdown_event.set()
    return jsonify({"quitting": True})
