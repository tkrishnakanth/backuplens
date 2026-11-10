"""Export-specific typed errors."""

from __future__ import annotations

from backend.backup.errors import BackupError


class ExportError(BackupError):
    code = "export_error"
    status = 500


class NoItems(BackupError):
    code = "no_items"
    status = 400


class ZipTooLarge(BackupError):
    code = "zip_too_large"
    status = 413


class FolderPickerUnavailable(BackupError):
    code = "folder_picker_unavailable"
    status = 501
