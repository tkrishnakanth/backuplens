"""Photo library index: Photos.sqlite -> normalised assets, albums and moments."""

from __future__ import annotations

from .dates import CORE_DATA_EPOCH, core_data_to_unix, day_label, local_day, unix_to_iso
from .errors import LibraryError, PhotosDatabaseMissing, UnsupportedPhotosSchema
from .index import LibraryIndex, build_index
from .models import CATEGORIES, Album, Asset, Moment

__all__ = [
    "CATEGORIES",
    "CORE_DATA_EPOCH",
    "Album",
    "Asset",
    "LibraryError",
    "LibraryIndex",
    "Moment",
    "PhotosDatabaseMissing",
    "UnsupportedPhotosSchema",
    "build_index",
    "core_data_to_unix",
    "day_label",
    "local_day",
    "unix_to_iso",
]
