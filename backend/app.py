"""BackupLens entry point: Flask app factory + Waitress launcher.

Run with::

    .venv\\Scripts\\python.exe backend\\app.py
"""

from __future__ import annotations

import argparse
import atexit
import secrets
import socket
import sys
import threading
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ""):
    sys.path.insert(0, str(ROOT))

from flask import Flask, send_from_directory  # noqa: E402

from backend.api.config_store import ConfigStore  # noqa: E402
from backend.api.errors import register_error_handlers  # noqa: E402
from backend.api.jobs import JobManager  # noqa: E402
from backend.api.logging_setup import configure_logging  # noqa: E402
from backend.api.routes.backups import bp as backups_bp  # noqa: E402
from backend.api.routes.export import bp as export_bp  # noqa: E402
from backend.api.routes.files import bp as files_bp  # noqa: E402
from backend.api.routes.jobs import bp as jobs_bp  # noqa: E402
from backend.api.routes.library import bp as library_bp  # noqa: E402
from backend.api.routes.media import bp as media_bp  # noqa: E402
from backend.api.routes.session import bp as session_bp  # noqa: E402
from backend.api.routes.settings import bp as settings_bp  # noqa: E402
from backend.api.security import install_security  # noqa: E402
from backend.api.session_manager import SessionManager  # noqa: E402
from backend.api.settings import read_settings  # noqa: E402
from backend.api.state import AppState  # noqa: E402
from backend.backup.discovery import list_backups  # noqa: E402
from backend.media.cache import DEFAULT_LIMIT_BYTES, MediaCache  # noqa: E402
from backend.version import APP_NAME, VERSION  # noqa: E402

BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", ROOT)) if getattr(sys, "frozen", False) else ROOT
DATA_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
FRONTEND_DIR = BUNDLE_ROOT / "frontend"
LOG_DIR = DATA_ROOT / "logs"


def create_app(config: dict | None = None) -> Flask:
    """Application factory. Tests pass a dict with ``TOKEN``, ``SESSION_OPEN`` and ``DISCOVERY``."""
    settings = dict(config or {})
    app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
    app.config.update(
        TESTING=False,
        GZIP_MIN_BYTES=1024,
        DISCOVERY_WITH_SIZE=True,
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    app.config.update(settings)
    app.config.setdefault("SECRET_KEY", secrets.token_urlsafe(32))

    token = str(app.config.get("TOKEN") or secrets.token_urlsafe(32))
    app.config["TOKEN"] = token
    port = app.config.get("PORT")
    port = int(port) if port else None

    config_store = app.config.get("CONFIG_STORE") or ConfigStore(app.config.get("CONFIG_PATH"))
    session_manager = SessionManager(app.config.get("SESSION_OPEN"), app.config.get("INDEX_BUILDER"))
    jobs = JobManager()
    settings = read_settings(config_store)
    if app.config.get("MEDIA_CACHE"):
        media_cache = app.config["MEDIA_CACHE"]
    elif app.config.get("CACHE_DIR"):
        media_cache = MediaCache(
            app.config.get("CACHE_DIR"),
            int(app.config.get("CACHE_LIMIT_BYTES") or DEFAULT_LIMIT_BYTES),
        )
    else:
        media_cache = MediaCache(settings["cacheLocation"], int(settings["cacheLimitBytes"]))
    state = AppState(
        token=token,
        port=port,
        config_store=config_store,
        session_manager=session_manager,
        jobs=jobs,
        discovery=app.config.get("DISCOVERY") or list_backups,
        frontend_dir=FRONTEND_DIR,
        media_cache=media_cache,
        persist_cache=bool(app.config.get("CACHE_PERSIST", False)),
    )
    app.extensions["backuplens"] = state

    register_error_handlers(app)
    install_security(app, token=token, port=port)
    app.register_blueprint(backups_bp)
    app.register_blueprint(session_bp)
    app.register_blueprint(library_bp)
    app.register_blueprint(media_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(jobs_bp)

    @app.get("/")
    def index():
        response = send_from_directory(state.frontend_dir, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/version")
    def version_info():
        return {"name": APP_NAME, "version": VERSION}

    if not app.config.get("TESTING"):
        configure_logging(app.config.get("LOG_DIR", LOG_DIR), token=token)
        atexit.register(_shutdown, state)

    app.logger.info("%s %s starting", APP_NAME, VERSION)
    return app


def _shutdown(state: AppState) -> None:
    try:
        state.session_manager.close()
    finally:
        state.jobs.close()
        if not state.persist_cache:
            state.media_cache.clear()


def find_free_port() -> int:
    """Ask the OS for a free loopback port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run BackupLens on 127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Port to use (0 = pick a free port)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    args = parser.parse_args(argv)

    port = args.port or find_free_port()
    app = create_app({"PORT": port})
    state: AppState = app.extensions["backuplens"]
    url = f"http://127.0.0.1:{port}/?t={state.token}"

    print(f"{APP_NAME} {VERSION} running at {url}", flush=True)
    print("Only this machine can connect. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=(url,)).start()

    from waitress import serve

    try:
        serve(app, host="127.0.0.1", port=port, threads=8)
    except KeyboardInterrupt:
        pass
    finally:
        _shutdown(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
