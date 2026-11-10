# Release blocker — GPLv2 component in the binary wheels

Date: 2026-11-10. Status: **STOPPED before CI/release** (Stage B §7.3).

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

## Next action

The human must choose A, B, C or D. No CI/release work should continue until then. The locally
modified Stage B application/packaging work is preserved on the local branch
`phase-10b-release`; it has not been pushed.
