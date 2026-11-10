"""Store-only ZIP creation for small selections (F-EXP-10)."""

from __future__ import annotations

import shutil
import uuid
import zipfile
from pathlib import Path

from backend.backup import Session
from backend.photos import LibraryIndex

from .errors import NoItems
from .paths import sanitize_component


def estimate_size(index: LibraryIndex, ids: list[str]) -> int:
    total = 0
    for asset_id in ids:
        asset = index.asset(asset_id)
        if asset is not None:
            total += int(asset.size or 0)
    return total


def _unique(name: str, used: set[str]) -> str:
    if name not in used:
        used.add(name)
        return name
    stem, suffix = Path(name).stem, Path(name).suffix
    counter = 1
    while True:
        candidate = f"{stem} ({counter}){suffix}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        counter += 1


def create_zip(session: Session, index: LibraryIndex, ids: list[str]) -> tuple[Path, int]:
    """Build a store-only ZIP in the session temp folder. Returns (path, file count)."""
    folder = Path(session.temp_dir) / f"zip-{uuid.uuid4().hex}"
    folder.mkdir(parents=True, exist_ok=True)
    zip_path = folder / "export.zip"
    used: set[str] = set()
    count = 0
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for index_no, asset_id in enumerate(ids):
                asset = index.asset(asset_id)
                if asset is None or not asset.file_id:
                    continue
                record = session.file_record(asset.file_id)
                suffix = Path(record.relative_path).suffix
                extracted = folder / f"{index_no}{suffix}"
                try:
                    session.extract_file(record.file_id, extracted)
                    arcname = _unique(sanitize_component(asset.filename), used)
                    archive.write(extracted, arcname=arcname)
                    count += 1
                finally:
                    extracted.unlink(missing_ok=True)
        if count == 0:
            raise NoItems("No files could be added to the ZIP")
        return zip_path, count
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
