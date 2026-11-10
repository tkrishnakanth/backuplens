"""Thumbnail, preview and original-file delivery with a disk cache.

All content decryption goes through the backup :class:`Session` worker thread. Large
videos are decrypted once to a cache file and streamed from disk, never buffered in RAM.
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError

from backend.backup import FileRecord, PayloadTooLarge, Session
from backend.photos import Asset, LibraryIndex

from .cache import MediaCache
from .errors import AssetNotFound, MediaNotFound

try:  # HEIC/HEIF support; optional at runtime but pinned in requirements.txt
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:  # pragma: no cover - warning is enough; originals still export
    logging.getLogger(__name__).warning("pillow-heif is not installed; HEIC previews will use placeholders")

LOGGER = logging.getLogger(__name__)
_MIME = {
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".mov": "video/quicktime",
    ".mp4": "video/mp4",
    ".m4v": "video/x-m4v",
    ".aae": "application/octet-stream",
}
MAX_SOURCE_BYTES = 128 * 1024 * 1024
THUMB_QUALITY = 82
PREVIEW_QUALITY = 88
PREVIEW_MAX = 2048


def mimetype_for(path: str) -> str:
    return _MIME.get(Path(path).suffix.lower(), "application/octet-stream")


def _mimetype(path: str) -> str:
    return mimetype_for(path)


@dataclass(slots=True)
class MediaFile:
    path: Path
    filename: str
    mimetype: str


class MediaService:
    def __init__(self, session: Session, index: LibraryIndex, cache: MediaCache) -> None:
        self.session = session
        self.index = index
        self.cache = cache
        self.namespace = session.info.udid or session.backup_dir.name or "backup"
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()

    # ------------------------------------------------------------------ util
    def _lock(self, key: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(key, threading.Lock())

    def _asset(self, asset_id: str) -> Asset:
        asset = self.index.asset(asset_id)
        if asset is None:
            raise AssetNotFound("Unknown asset id")
        return asset

    @staticmethod
    def _image_from_bytes(data: bytes) -> Image.Image | None:
        try:
            image = Image.open(BytesIO(data))
            image.load()
            return image
        except (UnidentifiedImageError, OSError, ValueError):
            return None

    def _image_from_path(self, path: Path) -> Image.Image | None:
        try:
            image = Image.open(path)
            image.load()
            return image
        except (UnidentifiedImageError, OSError, ValueError):
            return None

    def _original_image(self, asset: Asset) -> Image.Image | None:
        if not asset.file_id:
            return None
        try:
            data = self.session.read_file(asset.file_id, max_bytes=MAX_SOURCE_BYTES)
            image = self._image_from_bytes(data)
            if image is not None:
                return image
        except PayloadTooLarge:
            suffix = Path(asset.rel_path).suffix
            temporary = self.cache.path(self.namespace, "tmp", asset.file_id, suffix)
            try:
                self.session.extract_file(asset.file_id, temporary)
                return self._image_from_path(temporary)
            except Exception:  # noqa: BLE001 - fallback to placeholder
                return None
            finally:
                temporary.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001 - missing/undecodable file
            return None
        return None

    def _thumb_image(self, asset: Asset) -> Image.Image | None:
        if not asset.thumb_file_id:
            return None
        try:
            data = self.session.read_file(asset.thumb_file_id, max_bytes=16 * 1024 * 1024)
        except Exception:  # noqa: BLE001
            return None
        return self._image_from_bytes(data)

    def _ffmpeg_poster(self, asset: Asset) -> Image.Image | None:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg or not asset.file_id:
            return None
        source = self.cache.path(self.namespace, "tmp", f"{asset.file_id}.src", Path(asset.rel_path).suffix)
        output = self.cache.path(self.namespace, "tmp", f"{asset.file_id}.poster.jpg")
        try:
            if not source.exists():
                self.session.extract_file(asset.file_id, source)
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-loglevel",
                    "error",
                    "-ss",
                    "1",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-vf",
                    r"scale=min(1600\,iw):-2",
                    str(output),
                ],
                check=True,
                timeout=30,
                capture_output=True,
            )
            return self._image_from_path(output)
        except (OSError, subprocess.SubprocessError):
            return None
        finally:
            source.unlink(missing_ok=True)
            output.unlink(missing_ok=True)

    def _save_jpeg(self, image: Image.Image, dest: Path, max_size: int, quality: int) -> None:
        prepared = ImageOps.exif_transpose(image)
        if prepared.mode in ("RGBA", "LA", "P"):
            rgba = prepared.convert("RGBA")
            background = Image.new("RGB", rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            prepared = background
        elif prepared.mode != "RGB":
            prepared = prepared.convert("RGB")
        prepared.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = Path(str(dest) + ".part")
        prepared.save(part, "JPEG", quality=quality, optimize=True, progressive=True)
        os.replace(part, dest)

    def _placeholder(self, dest: Path, size: int, *, video: bool) -> None:
        if dest.exists():
            return
        image = Image.new("RGB", (size, size), (31, 37, 45))
        draw = ImageDraw.Draw(image)
        if video:
            margin = size // 3
            draw.polygon(
                [(margin, margin), (margin, size - margin), (size - margin, size // 2)],
                fill=(226, 231, 237),
            )
        else:
            draw.ellipse(
                (size * 0.28, size * 0.24, size * 0.44, size * 0.4), fill=(97, 107, 119)
            )
            draw.polygon(
                [
                    (size * 0.2, size * 0.74),
                    (size * 0.42, size * 0.5),
                    (size * 0.58, size * 0.64),
                    (size * 0.7, size * 0.54),
                    (size * 0.82, size * 0.74),
                ],
                fill=(97, 107, 119),
            )
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = Path(str(dest) + ".part")
        image.save(part, "JPEG", quality=80, optimize=True)
        os.replace(part, dest)

    # --------------------------------------------------------------- thumbs
    def thumb(self, asset_id: str, size: int = 320) -> Path:
        asset = self._asset(asset_id)
        size = max(64, min(1024, int(size)))
        key = f"{asset.file_id or asset.pk}_{size}"
        dest = self.cache.path(self.namespace, "thumbs", key, ".jpg")
        if dest.exists():
            self.cache.touch(dest)
            return dest
        with self._lock(str(dest)):
            if dest.exists():
                return dest
            image = self._thumb_image(asset)
            if image is None and asset.kind == "photo":
                image = self._original_image(asset)
            if image is None and asset.kind == "video":
                image = self._ffmpeg_poster(asset)
            if image is None and asset.kind == "video":
                self._placeholder(dest, size, video=True)
            elif image is None:
                LOGGER.warning("Thumbnail could not be decoded for asset %s", asset.id)
                self._placeholder(dest, size, video=False)
            else:
                self._save_jpeg(image, dest, size, THUMB_QUALITY)
        self.cache.note_write()
        return dest

    # -------------------------------------------------------------- preview
    def preview(self, asset_id: str) -> Path:
        asset = self._asset(asset_id)
        key = f"{asset.file_id or asset.pk}_preview"
        dest = self.cache.path(self.namespace, "previews", key, ".jpg")
        if dest.exists():
            self.cache.touch(dest)
            return dest
        with self._lock(str(dest)):
            if dest.exists():
                return dest
            image = None
            if asset.kind == "photo":
                image = self._original_image(asset) or self._thumb_image(asset)
            else:
                image = self._thumb_image(asset) or self._ffmpeg_poster(asset)
            if image is None:
                self._placeholder(dest, PREVIEW_MAX, video=asset.kind == "video")
            else:
                self._save_jpeg(image, dest, PREVIEW_MAX, PREVIEW_QUALITY)
        self.cache.note_write()
        return dest

    # ------------------------------------------------------------- original
    def _original_for_record(self, record: FileRecord, filename: str) -> MediaFile:
        suffix = Path(record.relative_path).suffix.lower()
        mimetype = _mimetype(record.relative_path)
        if not self.session.is_encrypted and record.backup_path and record.backup_path.is_file():
            return MediaFile(path=record.backup_path, filename=filename, mimetype=mimetype)
        if record.backup_path is None or not record.backup_path.is_file():
            raise MediaNotFound("The payload file is missing from the backup")
        dest = self.cache.path(self.namespace, "originals", record.file_id, suffix)
        if dest.exists():
            self.cache.touch(dest)
            return MediaFile(path=dest, filename=filename, mimetype=mimetype)
        with self._lock(str(dest)):
            if not dest.exists():
                self.session.extract_file(record.file_id, dest)
        self.cache.note_write()
        return MediaFile(path=dest, filename=filename, mimetype=mimetype)

    def original(self, asset_id: str) -> MediaFile:
        asset = self._asset(asset_id)
        if not asset.file_id:
            raise MediaNotFound("No original file is indexed for this asset")
        record = self.session.file_record(asset.file_id)
        return self._original_for_record(record, asset.filename)

    def live(self, asset_id: str) -> MediaFile:
        asset = self._asset(asset_id)
        if not asset.live_video_file_id:
            raise MediaNotFound("This asset has no paired Live Photo video")
        record = self.session.file_record(asset.live_video_file_id)
        return self._original_for_record(record, Path(record.relative_path).name)
