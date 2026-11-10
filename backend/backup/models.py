"""Typed models returned by the backup core."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class BackupInfo:
    """Metadata read from ``Info.plist``/``Manifest.plist`` (no decryption needed)."""

    id: str
    path: str
    device_name: str | None = None
    display_name: str | None = None
    product_type: str | None = None
    ios_version: str | None = None
    build_version: str | None = None
    serial_number: str | None = None
    imei: str | None = None
    udid: str | None = None
    last_backup: datetime | None = None
    encrypted: bool = False
    manifest_version: int | str | None = None
    size_bytes: int = 0
    error: str | None = None
    extra: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        """JSON-friendly representation used by ``GET /api/backups``."""
        return {
            "id": self.id,
            "path": self.path,
            "deviceName": self.device_name,
            "displayName": self.display_name,
            "productType": self.product_type,
            "iosVersion": self.ios_version,
            "buildVersion": self.build_version,
            "serialNumber": self.serial_number,
            "imei": self.imei,
            "udid": self.udid,
            "lastBackup": _iso(self.last_backup),
            "encrypted": self.encrypted,
            "manifestVersion": self.manifest_version,
            "sizeBytes": self.size_bytes,
            "error": self.error,
        }


@dataclass(slots=True)
class FileRecord:
    """One row of ``Manifest.db.Files`` joined with its parsed metadata."""

    file_id: str
    domain: str
    relative_path: str
    size: int
    mtime: float | None
    flags: int = 1
    backup_path: Path | None = None
    plist_blob: bytes | None = None
