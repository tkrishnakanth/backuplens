"""Build an optional PyInstaller one-folder distribution.

Usage (from the repo root, venv active):

    pip install pyinstaller
    python scripts/build_exe.py

Result: ``dist/BackupLens/BackupLens.exe`` with the frontend bundled. The app still
stores configuration/cache under ``%LOCALAPPDATA%\\BackupLens`` and logs next to the exe.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller is not installed. Run: pip install pyinstaller")
        return 2

    frontend = ROOT / "frontend"
    if not (frontend / "index.html").is_file():
        print("frontend/index.html is missing")
        return 2

    dist = ROOT / "dist"
    build = ROOT / "build"
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "BackupLens",
        "--distpath",
        str(dist),
        "--workpath",
        str(build),
        "--specpath",
        str(build),
        "--add-data",
        f"{frontend}{os.pathsep}frontend",
        "--collect-all",
        "pillow_heif",
        "--hidden-import",
        "waitress",
        str(ROOT / "backend" / "app.py"),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, check=True, cwd=ROOT)

    target = dist / "BackupLens"
    for extra in ("README.md", "LICENSE", "CHANGELOG.md"):
        source = ROOT / extra
        if source.is_file():
            shutil.copy2(source, target / extra)
    print(f"\nBuilt: {target / 'BackupLens.exe'}")
    print("Run it, then open the token URL printed in the console.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
