"""Unit tests for Core Data timestamps and local-day grouping."""

from __future__ import annotations

from backend.photos.dates import (
    CORE_DATA_EPOCH,
    core_data_to_unix,
    day_label,
    local_day,
    machine_utc_offset,
    unix_to_iso,
)


def test_core_data_epoch_conversion() -> None:
    assert CORE_DATA_EPOCH == 978307200
    assert core_data_to_unix(0) == 978307200
    assert core_data_to_unix(None) is None
    assert core_data_to_unix(700000000.4) == 1678307200


def test_local_day_uses_ios_timezone() -> None:
    timestamp = core_data_to_unix(700000000)
    assert timestamp is not None
    assert local_day(timestamp, 6 * 3600) == "2023-03-09"
    assert local_day(timestamp, -6 * 3600) == "2023-03-08"
    assert local_day(None) == "unknown"


def test_local_day_falls_back_to_machine_zone() -> None:
    timestamp = 1678307200
    day = local_day(timestamp, None)
    assert len(day) == 10 and day.count("-") == 2
    assert isinstance(machine_utc_offset(timestamp), int)


def test_labels_and_iso() -> None:
    assert day_label("2023-03-09") == "Thu, Mar 9, 2023"
    assert day_label("2024-01-02") == "Tue, Jan 2, 2024"
    assert day_label("unknown") == "unknown"
    assert unix_to_iso(1678307200) == "2023-03-08T20:26:40Z"
