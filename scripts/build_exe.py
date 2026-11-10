"""Build the optional PyInstaller one-folder distribution.

Usage (from the repo root, venv active):

    pip install pyinstaller
    python scripts/build_exe.py

Result: ``dist/BackupLens/BackupLens.exe`` on Windows (``BackupLens.app`` on macOS).
"""

from __future__ import annotations

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
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(ROOT / "dist"),
        "--workpath",
        str(ROOT / "build"),
        str(ROOT / "packaging" / "backuplens.spec"),
    ]
    print("Running:", " ".join(command))
    subprocess.run(command, check=True, cwd=ROOT)
    target = ROOT / "dist" / ("BackupLens.app" if sys.platform == "darwin" else "BackupLens")
    if target.exists() and target.is_dir():
        for extra in ("README.md", "LICENSE", "CHANGELOG.md", "THIRD_PARTY_NOTICES.txt"):
            source = ROOT / extra
            if source.is_file():
                shutil.copy2(source, target / extra)
    print(f"\nBuilt: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
