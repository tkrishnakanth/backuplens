"""Generate THIRD_PARTY_NOTICES.txt for BackupLens binaries.

The output lists every bundled Python/native component, its version, licence and the
exact upstream source URL, then appends the licence texts from the installed packages
and Python distribution. Run from the repo root.
"""

from __future__ import annotations

import importlib.metadata as metadata
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PYTHON_ROOT = Path(sys.base_prefix)
from backend.version import VERSION  # noqa: E402

PROJECT_URL = "https://github.com/tkrishnakanth/backuplens"
SOURCE_TAG = f"{PROJECT_URL}/tree/v{VERSION}-rc1"

# display name, distribution name, SPDX licence, upstream source URL
PACKAGES = [
    ("Flask", "flask", "BSD-3-Clause", "https://github.com/pallets/flask"),
    ("Werkzeug", "werkzeug", "BSD-3-Clause", "https://github.com/pallets/werkzeug"),
    ("Jinja2", "jinja2", "BSD-3-Clause", "https://github.com/pallets/jinja"),
    ("MarkupSafe", "markupsafe", "BSD-3-Clause", "https://github.com/pallets/markupsafe"),
    ("itsdangerous", "itsdangerous", "BSD-3-Clause", "https://github.com/pallets/itsdangerous"),
    ("click", "click", "BSD-3-Clause", "https://github.com/pallets/click"),
    ("blinker", "blinker", "MIT", "https://github.com/pallets-eco/blinker"),
    ("Waitress", "waitress", "ZPL-2.1", "https://github.com/Pylons/waitress"),
    (
        "iphone_backup_decrypt",
        "iphone_backup_decrypt",
        "MIT",
        "https://github.com/jsharkey13/iphone_backup_decrypt",
    ),
    ("pycryptodome", "pycryptodome", "BSD-2-Clause", "https://github.com/Legrandin/pycryptodome"),
    ("Pillow", "pillow", "MIT-CMU", "https://github.com/python-pillow/Pillow"),
    (
        "pillow-heif",
        "pillow-heif",
        "BSD-3-Clause (binary wheels: GPL-2.0-or-later via x265)",
        "https://github.com/bigcat88/pillow_heif",
    ),
    (
        "PyInstaller bootloader",
        "pyinstaller",
        "GPL-2.0-or-later with bootloader exception",
        "https://github.com/pyinstaller/pyinstaller",
    ),
]

# name, version, SPDX licence, upstream source URL, file names in the build
NATIVE = [
    (
        "libheif",
        "1.23.6",
        "LGPL-3.0-or-later",
        "https://github.com/strukturag/libheif/tree/v1.23.6",
        "libheif-*.dll / libheif.*.so / libheif.*.dylib",
    ),
    (
        "libde265",
        "1.1.3",
        "LGPL-3.0-or-later",
        "https://github.com/strukturag/libde265/tree/v1.1.3",
        "libde265-*.dll / libde265.*.so / libde265.*.dylib",
    ),
    (
        "x265",
        "4.3",
        "GPL-2.0-or-later",
        "https://github.com/Multicorewareinc/x265/tree/4.3",
        "libx265-*.dll / libx265.*.so / libx265.*.dylib",
    ),
]

LIBRARY_TEXTS = [
    ("GNU General Public License version 2 (x265)", "GPL-2.0.txt"),
    ("GNU Lesser General Public License version 3 (libheif, libde265)", "LGPL-3.0.txt"),
]


def version(dist: str) -> str:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "unavailable"


def read_text(path: Path) -> str | None:
    try:
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except OSError:
        return None
    return None


def package_license_text(dist: str) -> str:
    """Concatenate every licence file shipped in a distribution's metadata."""
    try:
        root = Path(metadata.distribution(dist)._path)
    except metadata.PackageNotFoundError:
        return "(not installed in this environment; see the upstream source URL)"
    files = sorted(
        (p for p in root.rglob("*") if p.is_file() and ("licen" in p.name.lower() or "copying" in p.name.lower())),
        key=lambda p: (len(p.parts), str(p)),
    )
    chunks: list[str] = []
    for path in files:
        text = read_text(path)
        if text:
            chunks.append(f"--- {path.relative_to(root).as_posix()} ---\n{text.strip()}")
    return "\n\n".join(chunks) or "(no licence file in the installed metadata; see the upstream source URL)"


def python_license_text() -> str:
    for name in ("LICENSE.txt", "LICENSE"):
        text = read_text(PYTHON_ROOT / name)
        if text:
            return text
    return "(Python licence not found in this environment; see https://www.python.org/)"


def tcl_license_text() -> str:
    for candidate in (
        PYTHON_ROOT / "tcl" / "tk8.6" / "license.terms",
        PYTHON_ROOT / "lib" / "tcl8.6" / "license.terms",
    ):
        text = read_text(candidate)
        if text:
            return text
    match = next(PYTHON_ROOT.glob("**/license.terms"), None)
    text = read_text(match) if match else None
    return text or "(Tcl/Tk licence not found in this environment; see https://www.tcl.tk/)"


def main() -> int:
    out: list[str] = [
        "BackupLens — THIRD PARTY NOTICES",
        "",
        "BackupLens is licensed under GPL-3.0-or-later (see LICENSE).",
        "",
        "Corresponding source for this release:",
        f"  {SOURCE_TAG}",
        "",
        "If that link is unavailable, write to the maintainers through the repository issues",
        "page and the corresponding source for the exact release will be provided.",
        "",
        "The installers and portable builds contain the components below. Source links point",
        "at the exact upstream versions bundled by the binary wheels.",
        "",
        "Python packages",
        "---------------",
    ]
    for name, dist, licence, url in PACKAGES:
        out.append(f"- {name} {version(dist)}: {licence} — {url}")

    out += [
        "",
        "Bundled native libraries",
        "------------------------",
    ]
    for name, ver, licence, url, files in NATIVE:
        out.append(f"- {name} {ver}: {licence} — {url}")
        out.append(f"  Files: {files}")

    out += [
        "",
        "Runtime and toolchain",
        "---------------------",
        f"- Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}: PSF-2.0 — https://www.python.org/",
        "- Tcl/Tk 8.6: BSD-style (Tcl/Tk licence) — https://www.tcl.tk/",
        "- MinGW-w64 runtime DLLs (Windows build): libgcc/libstdc++ under GPL-3.0-with-GCC-exception,",
        "  libwinpthread under MIT/BSD — https://sourceforge.net/p/mingw-w64/mingw-w64/ci/master/tree/COPYING",
        "",
        "Distribution notes",
        "------------------",
        "The PyInstaller build is one-folder, so libheif, libde265 and x265 are shipped as separate",
        "DLLs/shared libraries rather than being statically linked into the application. The LGPL",
        "libraries may be replaced with compatible builds; see the upstream source links above.",
        "BackupLens as a whole is distributed under GPL-3.0-or-later, which is compatible with the",
        "GPL-2.0-or-later x265 code and with the LGPL-3.0 libheif/libde265 libraries.",
        "",
    ]

    sections: list[tuple[str, str, str, str]] = [("BackupLens", VERSION, "GPL-3.0-or-later", PROJECT_URL)]
    sections += [(name, version(dist), licence, url) for name, dist, licence, url in PACKAGES]
    sections += [
        (
            "Python",
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "PSF-2.0",
            "https://www.python.org/",
        ),
        ("Tcl/Tk", "8.6", "BSD-style", "https://www.tcl.tk/"),
    ]

    for name, ver, licence, url in sections:
        out += ["", "=" * 78, f"{name} {ver} — {licence}", f"Source: {url}", "=" * 78]
        if name == "BackupLens":
            out.append(read_text(ROOT / "LICENSE") or "(see LICENSE)")
        elif name == "Python":
            out.append(python_license_text())
        elif name == "Tcl/Tk":
            out.append(tcl_license_text())
        else:
            dist = next(d for n, d, _l, _u in PACKAGES if n == name)
            out.append(package_license_text(dist))

    for title, filename in LIBRARY_TEXTS:
        out += ["", "=" * 78, title, "=" * 78]
        out.append(read_text(ROOT / "packaging" / "licenses" / filename) or f"(see packaging/licenses/{filename})")

    target = ROOT / "THIRD_PARTY_NOTICES.txt"
    target.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"Wrote {target} ({target.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
