# Third-party notices (build-process note)

Status: superseded by the root **[THIRD_PARTY_NOTICES.txt](../THIRD_PARTY_NOTICES.txt)** for releases.

Phase 10 found that `pillow-heif` 1.8.1 binary wheels bundle **x265 4.3** under
**GPL-2.0-or-later** (the x265 headers grant “either version 2 … or any later version”),
plus libheif 1.23.6 and libde265 1.1.3 under LGPL-3.0. The project was relicensed to
**GPL-3.0-or-later** (ADR-010). The one-folder PyInstaller build keeps the LGPL native libraries as
separate replaceable DLLs/shared libraries.

The generated root notice contains every bundled component, its version, SPDX licence, upstream source
URL, the exact BackupLens source tag URL, and the full licence texts for GPLv3, GPLv2, LGPLv3 and the
permissive component licences. `scripts/generate_notices.py` regenerates it from the installed wheels
and Python distribution.
