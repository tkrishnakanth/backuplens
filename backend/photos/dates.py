"""Core Data / local-day helpers for photo dates."""

from __future__ import annotations

from datetime import UTC, datetime

CORE_DATA_EPOCH = 978307200


def core_data_to_unix(value: float | int | None) -> int | None:
    """Convert a Core Data timestamp (seconds since 2001-01-01 UTC) to Unix seconds."""
    if value is None:
        return None
    return int(round(float(value) + CORE_DATA_EPOCH))


def unix_to_iso(value: int | float | None) -> str | None:
    if value is None:
        return None
    return datetime.fromtimestamp(float(value), tz=UTC).isoformat().replace("+00:00", "Z")


def machine_utc_offset(timestamp: int | float) -> int:
    """UTC offset in seconds that the machine's zone had at ``timestamp``."""
    local = datetime.fromtimestamp(float(timestamp)).astimezone()
    offset = local.utcoffset()
    return int(offset.total_seconds()) if offset else 0


def local_day(timestamp: int | float | None, tz_offset: int | None = None) -> str:
    """Return ``YYYY-MM-DD`` for the local calendar day of a capture timestamp.

    ``tz_offset`` is seconds east of UTC (as stored by iOS). When it is missing the
    machine's zone is used, matching project-docs/ARCHITECTURE.md §6.5.
    """
    if timestamp is None:
        return "unknown"
    offset = tz_offset if tz_offset is not None else machine_utc_offset(timestamp)
    local = datetime.fromtimestamp(float(timestamp) + offset, tz=UTC)
    return local.date().isoformat()


def day_label(day: str) -> str:
    """Format ``YYYY-MM-DD`` as ``Tue, Sep 10, 2024`` (UI header style)."""
    try:
        parsed = datetime.strptime(day, "%Y-%m-%d")
    except ValueError:
        return day
    return parsed.strftime("%a, %b %d, %Y").replace(" 0", " ")
