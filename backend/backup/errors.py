"""Typed errors for the backup core.

Every error carries a stable ``code`` used by the HTTP layer to build the JSON
error envelope, so API code never has to string-match messages.
"""

from __future__ import annotations


class BackupError(Exception):
    """Base class for all backup-core failures."""

    code = "backup_error"
    status = 500

    def __init__(self, message: str = "") -> None:
        super().__init__(message or self.code)
        self.message = message or self.code


class NotABackup(BackupError):
    code = "not_a_backup"
    status = 400


class ManifestMissing(BackupError):
    code = "manifest_missing"
    status = 400


class WrongPassword(BackupError):
    code = "wrong_password"
    status = 401


class UnsupportedVersion(BackupError):
    code = "unsupported_backup"
    status = 400


class PayloadMissing(BackupError):
    code = "payload_missing"
    status = 404


class PayloadTooLarge(BackupError):
    code = "payload_too_large"
    status = 413


class SessionClosed(BackupError):
    code = "session_closed"
    status = 409


class BadDestination(BackupError):
    code = "bad_destination"
    status = 400
