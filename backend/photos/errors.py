"""Typed errors raised by the photo library index."""

from __future__ import annotations

from backend.backup.errors import BackupError


class LibraryError(BackupError):
    code = "library_error"
    status = 500


class PhotosDatabaseMissing(LibraryError):
    code = "library_missing"
    status = 404


class UnsupportedPhotosSchema(LibraryError):
    code = "unsupported_library"
    status = 400
