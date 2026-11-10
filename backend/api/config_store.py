"""User configuration persisted in ``%LOCALAPPDATA%\\BackupLens\\config.json``."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any

from .paths import default_data_dir


def default_config_path() -> Path:
    return default_data_dir() / "config.json"


class ConfigStore:
    """Small JSON document store with atomic writes and a process-local lock."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path else default_config_path()
        self._lock = threading.RLock()
        self._data: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        with self._lock:
            if self._data is not None:
                return self._data
            data: dict[str, Any] = {}
            try:
                raw = self.path.read_text(encoding="utf-8")
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    data = parsed
            except (OSError, ValueError):
                data = {}
            self._data = data
            return data

    def save(self, data: dict[str, Any]) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = Path(str(self.path) + ".tmp")
            temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temporary, self.path)
            self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = dict(self.load())
            data[key] = value
            self.save(data)

    def extra_backup_paths(self) -> list[str]:
        value = self.load().get("extra_backup_paths", [])
        if not isinstance(value, list):
            return []
        return [str(item) for item in value if isinstance(item, str)]

    def add_extra_backup_path(self, path: str) -> bool:
        with self._lock:
            paths = self.extra_backup_paths()
            resolved = str(Path(path).resolve())
            if any(str(Path(existing).resolve()) == resolved for existing in paths):
                return False
            paths.append(resolved)
            data = dict(self.load())
            data["extra_backup_paths"] = paths
            self.save(data)
            return True
