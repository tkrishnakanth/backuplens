"""Typed media errors."""

from __future__ import annotations

from backend.backup.errors import BackupError


class AssetNotFound(BackupError):
    code = "asset_not_found"
    status = 404


class MediaNotFound(BackupError):
    code = "media_not_found"
    status = 404
