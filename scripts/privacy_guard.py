"""Fail the build if tracked files look like private data or secrets.

Run locally with::

    python scripts/privacy_guard.py

The guard intentionally prints paths and categories only, never the matching value.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

FORBIDDEN_SUFFIXES = {
    ".env",
    ".sqlite",
    ".sqlite-wal",
    ".sqlite-shm",
    ".db",
    ".log",
    ".mov",
    ".mp4",
    ".heic",
    ".heif",
    ".jpg",
    ".jpeg",
    ".png",
    ".zip",
    ".bundle",
    ".pem",
    ".key",
}
ALLOWED_PREFIXES = (
    "docs/screenshots/",
    "frontend/",
    "packaging/icon/",
    "tests/assets/",
)
# Verbatim upstream licence texts contain their authors' contact addresses; those are
# not the maintainer's personal data, so only the e-mail/local-path heuristics skip them.
VERBATIM_LICENSE_FILES = ("THIRD_PARTY_NOTICES.txt", "packaging/licenses/")
UDID = re.compile(r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}\b")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
LOCAL_PATH = re.compile(r"(?:C:\\Users\\|/Users/|/home/)(?!YOU|You|Public|<|example)[^\\/\s]+")
TOKENISH = re.compile(
    r"(?:sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|"
    r"AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)


def tracked_files() -> list[str]:
    return subprocess.check_output(["git", "ls-files"], text=True).splitlines()


def main() -> int:
    problems: list[tuple[str, str]] = []
    for name in tracked_files():
        lower = name.lower()
        suffix = Path(lower).suffix
        if suffix in FORBIDDEN_SUFFIXES and not name.startswith(ALLOWED_PREFIXES):
            problems.append((name, "forbidden file type"))
            continue
        if Path(name).name.startswith(".env"):
            problems.append((name, "environment file tracked"))
            continue
        if name.startswith("project-docs/local/") or name == ".env":
            problems.append((name, "private path tracked"))
            continue
        if name == "scripts/privacy_guard.py":
            # The guard contains the detection patterns themselves.
            continue
        if suffix in {".png", ".jpg", ".jpeg", ".ico", ".icns", ".heic", ".mov", ".mp4", ".zip"}:
            continue
        try:
            text = Path(name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if UDID.search(text):
            problems.append((name, "device-ID-like string"))
        verbatim_license = name == "THIRD_PARTY_NOTICES.txt" or name.startswith("packaging/licenses/")
        if not verbatim_license:
            for match in EMAIL.finditer(text):
                value = match.group(0).lower()
                if value.endswith("@users.noreply.github.com") or value.endswith("@example.com"):
                    continue
                problems.append((name, "personal email"))
                break
            if LOCAL_PATH.search(text):
                problems.append((name, "local user path"))
        if TOKENISH.search(text):
            problems.append((name, "secret/token-like string"))
    if problems:
        print("Privacy guard failed:")
        for path, category in problems:
            print(f"  - {path}: {category}")
        return 1
    print(f"Privacy guard passed for {len(tracked_files())} tracked files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
