"""BackupLens entry point: Flask app factory + Waitress launcher.

Run with::

    .venv\\Scripts\\python.exe backend\\app.py
"""

from __future__ import annotations

import argparse
import atexit
import importlib
import json
import os
import secrets
import socket
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
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
from backend.api.paths import default_data_dir, ensure_private_dir  # noqa: E402
from backend.api.routes.app_control import bp as app_control_bp  # noqa: E402
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

    data_dir = Path(app.config.get("DATA_DIR") or default_data_dir())
    ensure_private_dir(data_dir)
    app.config["DATA_DIR_EFFECTIVE"] = str(data_dir)
    config_store = app.config.get("CONFIG_STORE") or ConfigStore(
        app.config.get("CONFIG_PATH") or (data_dir / "config.json")
    )
    session_manager = SessionManager(app.config.get("SESSION_OPEN"), app.config.get("INDEX_BUILDER"))
    jobs = JobManager()
    app_settings = read_settings(config_store)
    if app.config.get("MEDIA_CACHE"):
        media_cache = app.config["MEDIA_CACHE"]
    elif app.config.get("CACHE_DIR"):
        media_cache = MediaCache(
            app.config.get("CACHE_DIR"),
            int(app.config.get("CACHE_LIMIT_BYTES") or DEFAULT_LIMIT_BYTES),
        )
    elif app.config.get("DATA_DIR"):
        media_cache = MediaCache(
            data_dir / "cache",
            int(app.config.get("CACHE_LIMIT_BYTES") or DEFAULT_LIMIT_BYTES),
        )
    else:
        media_cache = MediaCache(app_settings["cacheLocation"], int(app_settings["cacheLimitBytes"]))
    state = AppState(
        token=token,
        port=port,
        config_store=config_store,
        session_manager=session_manager,
        jobs=jobs,
        discovery=app.config.get("DISCOVERY") or list_backups,
        frontend_dir=FRONTEND_DIR,
        media_cache=media_cache,
        data_dir=data_dir,
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
    app.register_blueprint(app_control_bp)

    @app.get("/")
    def index():
        response = send_from_directory(state.frontend_dir, "index.html")
        response.headers["Cache-Control"] = "no-cache"
        return response

    @app.get("/version")
    def version_info():
        return {"name": APP_NAME, "version": VERSION}

    if not app.config.get("TESTING"):
        configure_logging(app.config.get("LOG_DIR", data_dir / "logs"), token=token)
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


def _health_ok(url: str, timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok" and payload.get("version") == VERSION
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _instance_path(data_dir: Path) -> Path:
    return data_dir / "instance.json"


def _read_instance(data_dir: Path) -> dict | None:
    path = _instance_path(data_dir)
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def _write_instance(data_dir: Path, payload: dict) -> None:
    path = _instance_path(data_dir)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    os.replace(temporary, path)


def _remove_instance(data_dir: Path, token: str) -> None:
    path = _instance_path(data_dir)
    data = _read_instance(data_dir)
    if data and data.get("token") == token:
        path.unlink(missing_ok=True)


def run_smoke_test() -> int:
    """Start a temporary server, check the UI/health, decode a synthetic HEIC, and exit."""
    try:
        for module in ("iphone_backup_decrypt", "PIL", "pillow_heif"):
            importlib.import_module(module)
        from PIL import Image

        sample = BUNDLE_ROOT / "tests" / "assets" / "sample.heic"
        if not sample.is_file():
            raise RuntimeError(f"smoke-test HEIC asset missing: {sample}")
        with tempfile.TemporaryDirectory(prefix="backuplens-smoke-") as temporary:
            with Image.open(sample) as image:
                image.load()
                image.thumbnail((48, 48))
                image.convert("RGB").save(Path(temporary) / "thumb.jpg", "JPEG")
            port = find_free_port()
            app = create_app(
                {"TESTING": True, "TOKEN": "smoke-token", "PORT": port, "DATA_DIR": Path(temporary) / "data"}
            )
            from waitress import create_server

            server = create_server(app, host="127.0.0.1", port=port, threads=2)
            thread = threading.Thread(target=server.run, name="backuplens-smoke", daemon=True)
            thread.start()
            try:
                health_url = f"http://127.0.0.1:{port}/api/health"
                deadline = time.time() + 10
                while time.time() < deadline and not _health_ok(health_url):
                    time.sleep(0.05)
                if not _health_ok(health_url):
                    raise RuntimeError("health endpoint did not become ready")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as response:
                    body = response.read().decode("utf-8", "replace")
                if "BackupLens" not in body:
                    raise RuntimeError("bundled frontend was not served")
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/js/main.js", timeout=5) as response:
                    if response.status != 200:
                        raise RuntimeError("frontend module was not served")
            finally:
                server.close()
                thread.join(timeout=5)
        print(f"{APP_NAME} {VERSION} smoke test passed")
        return 0
    except Exception as exc:  # noqa: BLE001 - print a clear failure and exit non-zero
        print(f"Smoke test failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run BackupLens on 127.0.0.1")
    parser.add_argument("--version", action="store_true", help="Print the version and exit")
    parser.add_argument("--port", type=int, default=0, help="Port to use (0 = pick a free port)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    parser.add_argument("--data-dir", type=str, default=None, help="Override the data/config/cache folder")
    parser.add_argument("--smoke-test", action="store_true", help="Run the built-artifact smoke test and exit")
    parser.add_argument(
        "--quit-after-idle",
        type=float,
        default=0.0,
        metavar="MINUTES",
        help="Quit after this many minutes without a request (0 = never)",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {VERSION}")
        return 0
    if args.smoke_test:
        return run_smoke_test()

    data_dir = Path(args.data_dir).expanduser().resolve() if args.data_dir else default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    existing = _read_instance(data_dir)
    if existing and existing.get("health") and _health_ok(str(existing["health"])):
        print(f"{APP_NAME} is already running at {existing.get('url')}", flush=True)
        if not args.no_browser and existing.get("url"):
            webbrowser.open(str(existing["url"]))
        return 0
    if existing:
        _instance_path(data_dir).unlink(missing_ok=True)

    port = args.port or find_free_port()
    app = create_app(
        {
            "PORT": port,
            "DATA_DIR": data_dir,
            "CACHE_PERSIST": bool(app_config_cache_persist()),
        }
    )
    state: AppState = app.extensions["backuplens"]
    url = f"http://127.0.0.1:{port}/?t={state.token}"
    health_url = f"http://127.0.0.1:{port}/api/health"
    _write_instance(data_dir, {"url": url, "health": health_url, "token": state.token})

    from waitress import create_server

    server = create_server(app, host="127.0.0.1", port=port, threads=8)
    threading.Thread(target=server.run, name="backuplens-server", daemon=True).start()

    print(f"{APP_NAME} {VERSION} running at {url}", flush=True)
    print(f"Data: {data_dir}", flush=True)
    print("Only this machine can connect. Use the menu > Quit BackupLens or Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()
    if args.quit_after_idle and args.quit_after_idle > 0:
        def _idle_monitor() -> None:
            timeout = args.quit_after_idle * 60
            while not state.shutdown_event.wait(2.0):
                if time.time() - state.last_request >= timeout:
                    state.shutdown_event.set()

        threading.Thread(target=_idle_monitor, name="backuplens-idle", daemon=True).start()

    try:
        while not state.shutdown_event.wait(0.5):
            pass
    except KeyboardInterrupt:
        pass
    finally:
        # The server thread is a daemon; finishing main exits the process. Running all
        # cleanup here guarantees decrypted temp data and the instance file are gone.
        _remove_instance(data_dir, state.token)
        _shutdown(state)
    return 0


def app_config_cache_persist() -> bool:
    """Optional opt-in for keeping the media cache between launches."""
    return os.environ.get("CACHE_PERSIST", "").strip().lower() in ("1", "true", "yes", "on")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
