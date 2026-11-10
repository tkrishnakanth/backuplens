"""Unit tests for thumbnail/preview generation, caching and streaming originals."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pytest
from backend.media.cache import MediaCache
from backend.media.errors import MediaNotFound
from backend.media.pipeline import MediaService
from PIL import Image
from tests.media_fixtures import FakeIndex, FakeSession, make_asset


def png_bytes(width: int = 400, height: int = 300, color=(200, 30, 30)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()


def jpeg_bytes(width: int = 120, height: int = 90, color=(20, 40, 220)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "JPEG")
    return buffer.getvalue()


def service_for(tmp_path: Path, assets, files, *, encrypted: bool = False, limit=None):
    session = FakeSession(tmp_path, files, encrypted=encrypted)
    index = FakeIndex(assets)
    cache = MediaCache(tmp_path / "cache", limit_bytes=limit or 64 * 1024 * 1024)
    return MediaService(session, index, cache), cache, session


def test_thumb_prefers_backup_thumbnail(tmp_path: Path) -> None:
    original_id, thumb_id = "aa" * 20, "bb" * 20
    files = {
        original_id: (png_bytes(color=(200, 30, 30)), "Media/DCIM/TESTAPPLE/TEST_0001.HEIC"),
        thumb_id: (jpeg_bytes(color=(20, 40, 220)), "Media/PhotoData/Thumbnails/V2/x/5005.JPG"),
    }
    asset = make_asset(thumb_file_id=thumb_id)
    service, _cache, _session = service_for(tmp_path, [asset], files)

    path = service.thumb("a1", 320)
    image = Image.open(path)
    assert image.format == "JPEG"
    assert max(image.size) <= 320
    red, green, blue = image.convert("RGB").getpixel((10, 10))
    assert blue > red and blue > green


def test_thumb_generates_from_original_when_no_backup_thumb(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (png_bytes(color=(10, 200, 10)), "Media/DCIM/TESTAPPLE/TEST_0001.PNG")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.PNG")
    service, _cache, _session = service_for(tmp_path, [asset], files)

    path = service.thumb("a1", 160)
    image = Image.open(path).convert("RGB")
    assert max(image.size) <= 160
    red, green, blue = image.getpixel((5, 5))
    assert green > red and green > blue


def test_preview_respects_2048_and_keeps_aspect(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (png_bytes(3200, 1600), "Media/DCIM/TESTAPPLE/TEST_0001.PNG")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.PNG")
    service, _cache, _session = service_for(tmp_path, [asset], files)
    path = service.preview("a1")
    image = Image.open(path)
    assert max(image.size) == 2048
    assert round(image.size[0] / image.size[1], 2) == 2.0


def test_exif_orientation_is_applied(tmp_path: Path) -> None:
    file_id = "aa" * 20
    image = Image.new("RGB", (100, 50), (50, 120, 50))
    exif = Image.Exif()
    exif[274] = 6  # rotate 90 CW
    buffer = BytesIO()
    image.save(buffer, "JPEG", exif=exif.tobytes())
    files = {file_id: (buffer.getvalue(), "Media/DCIM/TESTAPPLE/TEST_0001.JPG")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.JPG")
    service, _cache, _session = service_for(tmp_path, [asset], files)
    path = service.thumb("a1", 320)
    thumb = Image.open(path)
    assert thumb.size[0] < thumb.size[1]


def test_undecodable_original_returns_placeholder(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (b"this is not an image", "Media/DCIM/TESTAPPLE/TEST_0001.HEIC")}
    asset = make_asset(file_id=file_id)
    service, _cache, _session = service_for(tmp_path, [asset], files)
    path = service.thumb("a1", 320)
    image = Image.open(path)
    assert image.format == "JPEG"
    assert image.size == (320, 320)


def test_video_without_thumb_gets_placeholder(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (b"not a movie", "Media/DCIM/TESTAPPLE/TEST_0001.MOV")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.MOV", kind="video")
    service, _cache, _session = service_for(tmp_path, [asset], files)
    path = service.preview("a1")
    image = Image.open(path)
    assert image.format == "JPEG"
    assert image.size == (2048, 2048)


def test_missing_payload_gets_placeholder(tmp_path: Path) -> None:
    asset = make_asset(file_id="ee" * 20)
    service, _cache, _session = service_for(tmp_path, [asset], {})
    path = service.thumb("a1", 320)
    assert Image.open(path).format == "JPEG"


def test_cache_hit_does_not_regenerate(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (png_bytes(color=(200, 30, 30)), "Media/DCIM/TESTAPPLE/TEST_0001.PNG")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.PNG")
    service, _cache, session = service_for(tmp_path, [asset], files)
    first = service.thumb("a1", 160).read_bytes()

    session.files[file_id] = (png_bytes(color=(30, 30, 200)), "Media/DCIM/TESTAPPLE/TEST_0001.PNG")
    second = service.thumb("a1", 160).read_bytes()
    assert first == second


def test_cache_clear_and_lru_limit(tmp_path: Path) -> None:
    cache = MediaCache(tmp_path / "cache", limit_bytes=16 * 1024 * 1024)
    for index in range(4):
        path = cache.path("ns", "blobs", f"file{index}")
        path.write_bytes(b"x" * (6 * 1024 * 1024))
        cache.touch(path)
    freed = cache.enforce_limit(force=True)
    assert freed > 0
    assert cache.stats()["bytes"] <= 16 * 1024 * 1024
    freed_all = cache.clear()
    assert freed_all > 0
    assert cache.stats()["files"] == 0


def test_original_unencrypted_streams_payload_directly(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (b"original bytes", "Media/DCIM/TESTAPPLE/TEST_0001.HEIC")}
    asset = make_asset(file_id=file_id)
    service, _cache, session = service_for(tmp_path, [asset], files, encrypted=False)
    media = service.original("a1")
    assert media.path == session.file_record(file_id).backup_path
    assert media.filename == "TEST_0001.HEIC"
    assert media.mimetype == "image/heic"


def test_original_encrypted_is_cached(tmp_path: Path) -> None:
    file_id = "aa" * 20
    files = {file_id: (b"decrypted bytes", "Media/DCIM/TESTAPPLE/TEST_0001.MOV")}
    asset = make_asset(file_id=file_id, filename="TEST_0001.MOV", kind="video")
    service, cache, _session = service_for(tmp_path, [asset], files, encrypted=True)
    media = service.original("a1")
    assert media.path.read_bytes() == b"decrypted bytes"
    assert media.mimetype == "video/quicktime"
    assert media.path.parent.name == "originals"
    # second call reuses the cached file
    again = service.original("a1")
    assert again.path == media.path


def test_live_video_pairing(tmp_path: Path) -> None:
    still_id, live_id = "aa" * 20, "cc" * 20
    files = {
        still_id: (png_bytes(), "Media/DCIM/TESTAPPLE/TEST_0001.HEIC"),
        live_id: (b"live movie", "Media/DCIM/TESTAPPLE/TEST_0001.MOV"),
    }
    asset = make_asset(file_id=still_id, live_video_file_id=live_id)
    service, _cache, _session = service_for(tmp_path, [asset], files, encrypted=True)
    media = service.live("a1")
    assert media.path.read_bytes() == b"live movie"
    assert media.filename == "TEST_0001.MOV"

    missing = make_asset(asset_id="a2", file_id="dd" * 20, pk=2)
    service2, _c, _s = service_for(tmp_path / "second", [missing], {})
    with pytest.raises(MediaNotFound):
        service2.live("a2")
