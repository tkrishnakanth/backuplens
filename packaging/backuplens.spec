# -*- mode: python ; coding: utf-8 -*-
"""Pinned PyInstaller recipe for BackupLens (one-folder build)."""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
if (ROOT / "backend").is_dir() is False:
    ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
from backend.version import VERSION  # noqa: E402

datas = [
    (str(ROOT / "frontend"), "frontend"),
    (str(ROOT / "tests" / "assets"), "tests/assets"),
]
binaries = []
hiddenimports = ["waitress"]

for package in ("pillow_heif", "iphone_backup_decrypt"):
    package_datas, package_binaries, package_hidden = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hidden

a = Analysis(
    [str(ROOT / "backend" / "app.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff", "mypy"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="BackupLens",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=(sys.platform != "win32"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "packaging" / "icon" / ("icon.icns" if sys.platform == "darwin" else "icon.ico")),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="BackupLens")

if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="BackupLens.app",
        icon=str(ROOT / "packaging" / "icon" / "icon.icns"),
        bundle_identifier="org.backuplens.app",
        info_plist={
            "CFBundleName": "BackupLens",
            "CFBundleDisplayName": "BackupLens",
            "CFBundleShortVersionString": VERSION,
            "CFBundleVersion": VERSION,
            "LSMinimumSystemVersion": "11.0",
            "NSHighResolutionCapable": True,
        },
    )
