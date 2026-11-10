"""Owns the single open :class:`Session`, the library index and their lifecycle."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from backend.backup import BackupInfo, Session, open_backup
from backend.photos.index import LibraryIndex, build_index

IndexBuilder = Callable[..., LibraryIndex]
Progress = Callable[[str, int, int], None]


class AlreadyOpen(Exception):
    """Raised when a second backup is opened without closing the first."""


class SessionManager:
    def __init__(
        self,
        open_func: Callable[..., Session] | None = None,
        index_builder: IndexBuilder | None = None,
    ) -> None:
        self._open_func = open_func or open_backup
        self._index_builder = index_builder or build_index
        self._lock = threading.RLock()
        self._session: Session | None = None
        self._info: BackupInfo | None = None
        self._index: LibraryIndex | None = None
        self._index_state = "idle"
        self._progress: dict[str, Any] | None = None
        self._generation = 0

    # ------------------------------------------------------------------ open
    def open(self, path: str, password: str | None, info: BackupInfo) -> dict[str, Any]:
        """Unlock a backup and start building its index. Raises ``AlreadyOpen``."""
        with self._lock:
            if self._session is not None:
                raise AlreadyOpen("A backup session is already open")
            session = self._open_func(path, password)
            self._generation += 1
            generation = self._generation
            self._session = session
            self._info = info
            self._index = None
            self._index_state = "building"
            self._progress = {"stage": "starting", "done": 0, "total": 0}
        worker = threading.Thread(
            target=self._build,
            args=(generation, session),
            name="backuplens-index",
            daemon=True,
        )
        worker.start()
        return self.snapshot()

    def _build(self, generation: int, session: Session) -> None:
        def progress(stage: str, done: int, total: int) -> None:
            with self._lock:
                if generation != self._generation:
                    return
                self._progress = {"stage": stage, "done": done, "total": total}

        try:
            index = self._index_builder(session, progress)
        except Exception as exc:  # noqa: BLE001 - report failures through state, never raise
            with self._lock:
                if generation != self._generation:
                    return
                self._index = None
                self._index_state = "failed"
                self._progress = {
                    "stage": "failed",
                    "done": 0,
                    "total": 0,
                    "message": f"{type(exc).__name__}: {exc}",
                }
            return
        with self._lock:
            if generation != self._generation:
                return
            self._index = index
            self._index_state = "ready"
            self._progress = None

    # ----------------------------------------------------------------- close
    def close(self) -> dict[str, Any]:
        with self._lock:
            session = self._session
            self._generation += 1
            self._session = None
            self._info = None
            self._index = None
            self._index_state = "idle"
            self._progress = None
        if session is not None:
            session.close()
        return self.snapshot()

    # ----------------------------------------------------------------- state
    @property
    def session(self) -> Session | None:
        return self._session

    @property
    def info(self) -> BackupInfo | None:
        return self._info

    @property
    def index(self) -> LibraryIndex | None:
        return self._index

    @property
    def index_state(self) -> str:
        return self._index_state

    def set_index_state(self, state: str, progress: dict[str, Any] | None = None) -> None:
        with self._lock:
            self._index_state = state
            self._progress = progress

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "open": self._session is not None,
                "backup": self._info.to_dict() if self._info is not None else None,
                "indexState": self._index_state,
                "progress": self._progress,
            }
