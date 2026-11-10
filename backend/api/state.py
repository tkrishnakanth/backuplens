"""Process-wide application state stored in ``app.extensions['backuplens']``."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from backend.backup import BackupInfo
from backend.media.cache import MediaCache

from .config_store import ConfigStore
from .jobs import JobManager
from .session_manager import SessionManager

Discovery = Callable[..., list[BackupInfo]]


@dataclass
class AppState:
    token: str
    port: int | None
    config_store: ConfigStore
    session_manager: SessionManager
    jobs: JobManager
    discovery: Discovery
    frontend_dir: Path
    media_cache: MediaCache
    data_dir: Path
    persist_cache: bool = False
    shutdown_event: threading.Event = field(default_factory=threading.Event)
    started_at: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)
