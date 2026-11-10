"""Logging with a hard secret-redaction filter.

The app never logs request bodies and never logs the backup password. This filter is
defence in depth: any registered secret (the launch token, the environment password if
present) is replaced before a record reaches a handler.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_SECRETS: set[str] = set()
_REDACTED = "[redacted]"

# The password, when present, is used by the test session to unlock the real backup.
# Never log it even if a future code path accidentally interpolates it.
_env_password = os.environ.get("BACKUP_PASSWORD")
if _env_password:
    _SECRETS.add(_env_password)


def register_secret(value: str | None) -> None:
    if value:
        _SECRETS.add(value)


class RedactingFilter(logging.Filter):
    """Replace every registered secret in the formatted message."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # noqa: BLE001 - never break logging
            return True
        redacted = message
        for secret in _SECRETS:
            if secret and secret in redacted:
                redacted = redacted.replace(secret, _REDACTED)
        if redacted != message:
            record.msg = redacted
            record.args = None
        return True


def configure_logging(log_dir: str | Path | None = None, *, token: str | None = None) -> None:
    """Configure console + rotating file logging once per process."""
    register_secret(token)
    root = logging.getLogger()
    if getattr(root, "_backuplens_configured", False):
        return
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S"
    )
    redactor = RedactingFilter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(redactor)
    root.addHandler(console)

    if log_dir is not None:
        try:
            directory = Path(log_dir)
            directory.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                directory / "app.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            file_handler.addFilter(redactor)
            root.addHandler(file_handler)
        except OSError:
            root.warning("Could not create the log file; continuing with console logging only")

    root._backuplens_configured = True  # type: ignore[attr-defined]
