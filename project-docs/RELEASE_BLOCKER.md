# Release blocker — GPLv2 component in the binary wheels (RESOLVED)

Date: 2026-11-10. Status: **RESOLVED — relicensed to GPL-3.0-or-later (Option C).**
Historical note: this file records the blocker that interrupted Stage B before CI/release.

## Finding

`pillow-heif` 1.8.1's **binary wheels** ship a license bundle that declares:

- `libheif` — LGPLv3 (okay, with notices/source)
- `libde265` — LGPLv3 (okay)
- **`x265` — GPLv2**
- MinGW runtime — GPLv3-with-GCC-exception / MIT / BSD

The wheel metadata's `License` field says BSD-3-Clause (the Python source), but the
`LICENSES_bundled.txt` file in the installed wheel states: *“License for pillow-heif binary wheels:
GPLv2, due to base library licenses.”*

Because PyInstaller includes the `pillow_heif` native libraries in the executable, the Windows
portable folder, the Inno Setup installer, and would include them in the macOS/Linux artifacts, the
combined binary distribution would be subject to GPLv2. This is incompatible with presenting the
release binaries as MIT-only.

## What was done

- Windows PyInstaller one-folder build succeeded, and the built app passed `--smoke-test`.
- The Inno Setup per-user installer was built, silently installed, the installed app passed
  `--smoke-test`, and silent uninstall removed the program directory.
- **All locally built `dist/` and `build/` output was then deleted** and was never committed or
  uploaded. No release, tag, or CI run was created.
- Source code and packaging scripts remain local; no GPL binary was pushed to GitHub.

## Options for the owner

### A. Source-only MIT release (no installers)
Keep the MIT source release; users install Python and `pip install -r requirements.txt` themselves.
The app is fully functional, but there is no one-click installer and HEIC support depends on the GPL
wheel the user installs. Lowest effort; no binary distribution by the project.

### B. Decode-only HEIC build (recommended for permissive binaries)
Build `libheif`/`libde265` **without x265** (or use system libraries) and build `pillow-heif` from
source against that. BackupLens only *decodes* HEIC for previews and HEIC→JPEG export; it does not
need HEVC encoding. This requires a reproducible native build on each OS, a new build dependency, and
an ADR. Binaries can then stay MIT/LGPL-compliant with notices and relinkable LGPL libraries.

### C. GPLv2 binary distribution
Distribute the binaries under GPLv2 (or a GPL-compatible dual licence), include the complete
corresponding source and notices, and update the README/licence wording. This requires an explicit
owner decision and legal review; the source tree can remain MIT only if the combined binary
distribution is clearly separated and compliant.

### D. Replace the HEIC dependency
Use a different HEIC decoder without x265 (e.g. a system libheif binding), or drop HEIC preview
support and export originals only. This is a product-scope change and needs an ADR.

## Resolution — 2026-11-10 (Option C)

- Verified x265 4.3's source headers grant “GNU General Public License … either version 2 of the License,
  or (at your option) any later version”; its `COPYING` is GPLv2. libheif 1.23.6 and libde265 1.1.3 are
  LGPLv3; MinGW runtime components are GPLv3-with-GCC-exception/MIT/BSD. All are GPL-3.0-compatible.
- BackupLens is now **GPL-3.0-or-later** in `LICENSE`, `README.md`, `pyproject.toml`, `CONTRIBUTING.md`,
  the Inno Setup license page and the generated `THIRD_PARTY_NOTICES.txt`.
- The one-folder build remains, so LGPL libheif/libde265 are separate replaceable DLLs/shared libraries.
- `THIRD_PARTY_NOTICES.txt` contains the component/version/licence table, exact source-tag URL
  (`https://github.com/tkrishnakanth/backuplens/tree/v0.1.0-rc1`) and links for libheif 1.23.6,
  libde265 1.1.3 and x265 4.3, with full licence texts.
- The Windows installer and smoke test were rebuilt with these files. Continue at Stage B step 10.

