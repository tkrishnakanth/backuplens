"""Atomic file writing and optional HEIC -> JPEG conversion."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image, ImageOps

from backend.backup import Session

from .models import ExportItem, ExportOptions
from .paths import resolve_conflict, safe_join
from .planner import output_relative

JPEG_QUALITY = 92


def _flatten(image: Image.Image) -> Image.Image:
    if image.mode in ("RGBA", "LA", "P"):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.split()[-1])
        return background
    if image.mode != "RGB":
        return image.convert("RGB")
    return image


def _convert_to_jpeg(session: Session, item: ExportItem, part: Path) -> None:
    temporary = Path(session.temp_dir) / "export-src" / f"{item.file_id}{Path(item.rel_path).suffix}"
    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        session.extract_file(item.file_id, temporary)
        with Image.open(temporary) as source:
            source.load()
            exif = source.getexif()
            oriented = ImageOps.exif_transpose(source)
            if exif:
                exif[274] = 1  # orientation already applied
            oriented = _flatten(oriented)
            oriented.save(
                part,
                "JPEG",
                quality=JPEG_QUALITY,
                optimize=True,
                progressive=True,
                exif=exif.tobytes() if exif else b"",
            )
    finally:
        temporary.unlink(missing_ok=True)


def write_item(
    session: Session,
    item: ExportItem,
    destination: Path,
    options: ExportOptions,
) -> Path | None:
    """Write one export item atomically. Returns None when skipped by conflict policy."""
    relative = output_relative(item, options.layout)
    final = safe_join(destination, relative)
    final.parent.mkdir(parents=True, exist_ok=True)
    resolved = resolve_conflict(final, options.on_conflict)
    if resolved is None:
        return None
    part = Path(str(resolved) + ".part")
    try:
        if options.convert_heic_to_jpeg and item.convert:
            _convert_to_jpeg(session, item, part)
        else:
            session.extract_file(item.file_id, part)
        os.replace(part, resolved)
        if options.set_file_dates and item.taken_at:
            os.utime(resolved, times=(item.taken_at, item.taken_at))
        return resolved
    except Exception:
        part.unlink(missing_ok=True)
        raise
