"""Disk cache for thumbnails, previews and decrypted originals with an LRU size cap."""

from __future__ import annotations

import os
import re
import shutil
import threading
from pathlib import Path

from backend.api.paths import default_cache_dir

DEFAULT_LIMIT_BYTES = 2 * 1024 * 1024 * 1024
_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def default_cache_root() -> Path:
    return default_cache_dir()


def _safe(value: str) -> str:
    cleaned = _SAFE.sub("_", value).strip("._")
    return cleaned or "default"


class MediaCache:
    """Namespaced by backup; evicts least-recently-used files above the size cap."""

    def __init__(self, root: str | Path | None = None, limit_bytes: int = DEFAULT_LIMIT_BYTES) -> None:
        self.root = Path(root) if root else default_cache_root()
        self.limit_bytes = max(16 * 1024 * 1024, int(limit_bytes))
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._writes = 0

    def path(self, namespace: str, kind: str, key: str, suffix: str = "") -> Path:
        folder = self.root / _safe(namespace) / _safe(kind)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / f"{_safe(key)}{suffix}"

    def touch(self, path: Path) -> None:
        try:
            os.utime(path, None)
        except OSError:
            pass

    def note_write(self) -> None:
        with self._lock:
            self._writes += 1
            should_enforce = self._writes % 25 == 0
        if should_enforce:
            self.enforce_limit()

    def enforce_limit(self, *, force: bool = False) -> int:
        """Delete oldest files until the cache is below the cap. Returns bytes freed."""
        with self._lock:
            entries: list[tuple[float, int, Path]] = []
            total = 0
            for path in self.root.rglob("*"):
                try:
                    if path.is_file():
                        stat = path.stat()
                        total += stat.st_size
                        entries.append((stat.st_mtime, stat.st_size, path))
                except OSError:
                    continue
            if total <= self.limit_bytes and not force:
                return 0
            target = int(self.limit_bytes * 0.92) if total > self.limit_bytes else 0
            freed = 0
            for _mtime, size, path in sorted(entries):
                if total - freed <= target:
                    break
                try:
                    path.unlink()
                    freed += size
                except OSError:
                    continue
            return freed

    def clear(self) -> int:
        """Remove every cached file; returns the number of bytes freed."""
        with self._lock:
            freed = 0
            for child in list(self.root.iterdir()):
                try:
                    if child.is_dir():
                        freed += sum(
                            item.stat().st_size for item in child.rglob("*") if item.is_file()
                        )
                        shutil.rmtree(child, ignore_errors=True)
                    else:
                        freed += child.stat().st_size
                        child.unlink(missing_ok=True)
                except OSError:
                    continue
            self.root.mkdir(parents=True, exist_ok=True)
            return freed

    def stats(self) -> dict[str, int]:
        count = 0
        total = 0
        for path in self.root.rglob("*"):
            try:
                if path.is_file():
                    count += 1
                    total += path.stat().st_size
            except OSError:
                continue
        return {"files": count, "bytes": total, "limitBytes": self.limit_bytes}
