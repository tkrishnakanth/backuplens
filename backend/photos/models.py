"""Normalised photo-library models (project-docs/ARCHITECTURE.md §6.3)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Asset:
    id: str
    pk: int
    file_id: str | None
    rel_path: str
    directory: str
    filename: str
    original_name: str | None
    kind: str  # "photo" | "video"
    taken_at: int | None
    tz_offset: int | None
    width: int = 0
    height: int = 0
    duration: float | None = None
    size: int | None = None
    favorite: bool = False
    hidden: bool = False
    trashed: bool = False
    is_live: bool = False
    is_portrait: bool = False
    is_panorama: bool = False
    is_timelapse: bool = False
    is_slomo: bool = False
    is_screenshot: bool = False
    in_camera_roll: bool = False
    has_adjustments: bool = False
    live_video_file_id: str | None = None
    edited_file_id: str | None = None
    thumb_file_id: str | None = None
    lat: float | None = None
    lon: float | None = None
    moment_title: str | None = None
    moment_pk: int | None = None

    @property
    def media_kind(self) -> str:
        return "v" if self.kind == "video" else "p"

    def flags(self) -> int:
        """Bitmask used by the compact asset list; documented in ADR-006."""
        bits = (
            self.favorite,
            self.hidden,
            self.trashed,
            self.is_live,
            self.is_portrait,
            self.is_panorama,
            self.is_timelapse,
            self.is_slomo,
            self.is_screenshot,
        )
        value = 0
        for index, flag in enumerate(bits):
            if flag:
                value |= 1 << index
        return value


@dataclass(slots=True)
class Album:
    id: str
    pk: int
    title: str
    asset_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Moment:
    id: str
    title: str
    asset_ids: list[str] = field(default_factory=list)


# Sidebar order and labels (project-docs/UI_SPEC.md §4).
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("all", "All"),
    ("camera_roll", "Camera Roll"),
    ("photos", "Photos"),
    ("videos", "Videos"),
    ("favorites", "Favorites"),
    ("live", "Live Photos"),
    ("portrait", "Portrait"),
    ("panoramas", "Panoramas"),
    ("timelapse", "Time-lapse"),
    ("slomo", "Slo-mo"),
    ("screenshots", "Screenshots"),
    ("hidden", "Hidden"),
    ("trashed", "Trashed"),
)
