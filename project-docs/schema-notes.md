# schema-notes — Photos.sqlite findings (sanitised)

Status: Phase 0 evidence, sanitised for public release in Phase 10A. This file records **structure,
column semantics and rules only**. The unredacted notes, sample rows and the owner's reference numbers
live in the git-ignored `project-docs/local/` folder and are never published.

The spike (`project-docs/spike_unlock.py`) unlocked a real encrypted iOS backup read-only, decrypted
`Manifest.db` and `Photos.sqlite` to a temporary folder, and queried them with SQLite. No values from the
owner's library are reproduced below.

## 1. Test backup and tooling

| Item | Value |
|---|---|
| Backup location | a local, read-only iOS backup folder (path omitted) |
| Device | iPhone-class device, recent iOS 17.x release (exact values kept locally) |
| Encryption | `IsEncrypted = True`, `Manifest.plist` version 10.x |
| Unlock + Manifest decrypt | a few seconds; PBKDF2 dominates |
| Library | `iphone_backup_decrypt` 0.11.2 |
| Python | 3.13.1 (app requires 3.11+) |

**Licence check:** `iphone_backup_decrypt` 0.11.2 is **MIT** (Copyright 2019–2026 James Sharkey);
its dependency `pycryptodome` is BSD-2-Clause. Both are compatible with the MIT licence chosen for
BackupLens.

`Manifest.db` was decrypted to a temporary folder, integrity was checked, and the temp artefacts were
deleted after the spike.

## 2. Manifest.db facts (structure)

- `Files` has the expected columns: `fileID`, `domain`, `relativePath`, `flags`, `file`.
- `flags = 1` means a regular file; `2` a directory; `4` a symlink.
- A backup contains many app domains and thousands of files; the exact counts vary by device.
- `CameraRollDomain` contains `Media/DCIM/...` originals and `Media/PhotoData/...` metadata.
- `Media/PhotoData/Photos.sqlite` is present. In the tested backup there was no `-wal`/`-shm` sibling.
  The Manifest-reported size can differ from the decrypted size for live SQLite files; integrity checks
  passed, so this is treated as an iOS/Manifest quirk rather than corruption.
- Modern per-asset thumbnails live under `Media/PhotoData/Thumbnails/V2/...`; older `.ithmb` files may
  also exist and are not used.

## 3. Photos.sqlite shape (tested variant)

- `Photos.sqlite` is a Core Data SQLite database with many tables.
- Asset table: **`ZASSET`** on the tested iOS version. Older backups may use **`ZGENERICASSET`**.
- `ZADDITIONALASSETATTRIBUTES` has one row per asset and joins on its `ZASSET` column.
- `ZGENERICALBUM` stores albums; **`ZKIND = 2` marks user albums**. Other `ZKIND` values are
  system/smart albums and must not be shown in the Albums list.
- Album↔asset join table name changes with the Core Data model (for example a `Z_<n>ASSETS` name).
  Locate it via `sqlite_master`/column introspection; never hard-code one name.
- `ZMOMENT` stores moments and is linked from `ZASSET.ZMOMENT`.
- `ZINTERNALRESOURCE` stores per-asset resources (photo/video/adjustment data).
- The tested schema had no `ZISDETECTEDSCREENSHOT` column. Treat every optional column as optional.

### 3.1 Columns used

`ZASSET`: `Z_PK`, `ZDIRECTORY`, `ZFILENAME`, `ZKIND`, `ZKINDSUBTYPE`, `ZDATECREATED`, `ZADDEDDATE`,
`ZFAVORITE`, `ZHIDDEN`, `ZTRASHEDSTATE`, `ZTRASHEDDATE`, `ZPLAYBACKSTYLE`, `ZSAVEDASSETTYPE`,
`ZDEPTHTYPE`, `ZWIDTH`, `ZHEIGHT`, `ZDURATION`, `ZLATITUDE`, `ZLONGITUDE`, `ZHASADJUSTMENTS`,
`ZMOMENT`, `ZVISIBILITYSTATE`, `ZORIENTATION`.

`ZADDITIONALASSETATTRIBUTES`: `ZASSET`, `ZORIGINALFILENAME`, `ZORIGINALFILESIZE`, `ZORIGINALWIDTH`,
`ZORIGINALHEIGHT`, `ZTIMEZONEOFFSET`, `ZEXIFTIMESTAMPSTRING`, `ZREVERSELOCATIONDATA`,
`ZADJUSTEDFINGERPRINT`.

`ZGENERICALBUM`: `Z_PK`, `ZTITLE`, `ZKIND`, `ZCACHEDCOUNT` (cached; recompute from the join).
`ZMOMENT`: `Z_PK`, `ZTITLE`, `ZSUBTITLE`, `ZCACHEDCOUNT`, `ZTIMEZONEOFFSET`, `ZSTARTDATE`, `ZENDDATE`,
`ZAPPROXIMATELATITUDE`, `ZAPPROXIMATELONGITUDE`.

## 4. Timestamps and time zones

- Core Data epoch is 2001-01-01 UTC: `unix = ZDATECREATED + 978307200`.
- `ZADDITIONALASSETATTRIBUTES.ZTIMEZONEOFFSET` is **seconds east of UTC** (may be `NULL`).
- Grouping rule: local day = `taken_at + coalesce(tz_offset, machine_utc_offset)`; fall back to the
  machine's zone when the column is `NULL`, as `project-docs/ARCHITECTURE.md` §6.5 proposes.
- `ZMOMENT.ZTIMEZONEOFFSET` can provide a fallback when the asset offset is missing.

## 5. Category rules (verified on the tested schema)

Exact counts are deliberately omitted here; acceptance counts for the owner's original screenshot live
in the ignored `project-docs/local/reference-counts.json`. These are the rules:

| Category | SQL rule on `ZASSET` |
|---|---|
| All | *no filter* — includes trashed rows for the sidebar count |
| Camera Roll | `ZSAVEDASSETTYPE = 3 AND ZTRASHEDSTATE = 0` (or `ZDIRECTORY LIKE 'DCIM%'` on older schemas) |
| Photos | `ZKIND = 0 AND ZTRASHEDSTATE = 0` |
| Videos | `ZKIND = 1 AND ZTRASHEDSTATE = 0` |
| Favorites | `ZFAVORITE = 1` |
| Live Photos | `ZKINDSUBTYPE = 2 AND ZTRASHEDSTATE = 0` |
| Portrait | `ZDEPTHTYPE IN (1, 2) AND ZTRASHEDSTATE = 0`; older schemas may use `ZKINDSUBTYPE = 3` |
| Panoramas | `ZKINDSUBTYPE = 1 AND ZTRASHEDSTATE = 0` |
| Time-lapse | `ZKINDSUBTYPE = 102 AND ZTRASHEDSTATE = 0` |
| Slo-mo | `ZKINDSUBTYPE = 101 AND ZTRASHEDSTATE = 0` |
| Screenshots | `ZKINDSUBTYPE = 10 AND ZTRASHEDSTATE = 0`; or `ZISDETECTEDSCREENSHOT = 1` when present |
| Hidden | `ZHIDDEN = 1` |
| Trashed | `ZTRASHEDSTATE = 1` |

**Camera Roll vs All.** `All` is every asset row, including trashed. `Camera Roll` is untrashed media
saved by the camera (`ZSAVEDASSETTYPE = 3`). iCloud/shared-library imports live under
`PhotoData/CPLAssets/...` and are not Camera Roll assets.

**All: count vs grid.** The sidebar count for All includes trashed assets, but the grid hides them. The
Trashed view is the only place deleted assets appear. This matches the reference screenshot's date
groups. Implemented in `LibraryIndex.query(scope="all")`.

**Observed flags (not categories):** `ZKIND` 0=photo/1=video; `ZKINDSUBTYPE` carries the
panorama/live/screenshot/slo-mo/time-lapse values above; `ZDEPTHTYPE` marks portrait-depth captures;
`ZSAVEDASSETTYPE = 3` is camera roll and `6` is an iCloud/CPL import; `ZPLAYBACKSTYLE` is **not** a
reliable Live Photo flag; `ZVISIBILITYSTATE = 2` does **not** mean hidden in the tested schema.

## 6. Albums

User albums are `ZGENERICALBUM.ZKIND = 2`. Counts must be recomputed by joining the album↔asset table to
`ZASSET` and excluding trashed assets; `ZCACHEDCOUNT` is a useful cross-check but is not trusted.
All other `ZKIND` values are system albums (Recents, Favorites, media types, imports, restore markers,
etc.) and are not listed. Empty user albums render without a count pill.

## 7. Thumbnails

The backup contains pre-rendered per-asset thumbnails:

```
Media/PhotoData/Thumbnails/V2/<ZDIRECTORY>/<ZFILENAME>/5005.JPG
```

- In the tested library every indexed asset had a matching V2 thumbnail; filenames should still be
  checked, because stale entries can exist.
- Look up the exact path above rather than scanning by basename.
- Consequence: the grid can serve a decrypted JPEG without decoding the HEIC original. Fall back to
  Pillow + pillow-heif when a thumb is absent or undecodable.

## 8. File mapping, Live Photos, edited versions

### 8.1 Original file mapping

Every asset's original is in `CameraRollDomain` at `Media/<ZDIRECTORY>/<ZFILENAME>`. In the tested
library every asset resolved to a 40-hex `fileID` in `Manifest.db`; failures must still be tolerated.
iCloud assets use `Media/PhotoData/CPLAssets/groupNN/<UUID>.JPG`. Original filename and byte size come
from `ZADDITIONALASSETATTRIBUTES` (`ZORIGINALFILENAME`, `ZORIGINALFILESIZE`), with the asset columns as
fallbacks.

### 8.2 Live Photos

A Live Photo still has `ZKINDSUBTYPE = 2` and pairs with a same-directory, same-basename `.MOV`
(e.g. `<NAME>.HEIC` ↔ `<NAME>.MOV`). Pair by filename first; `ZINTERNALRESOURCE` type-3 resources are a
fallback. Some MOV files under DCIM are ordinary videos, not Live clips.

### 8.3 Edited photos

- `ZHASADJUSTMENTS = 1` marks adjusted assets.
- On the tested library, edits have no rendered full-size image; they carry an `.AAE` adjustment
  sidecar beside the original when available.
- Honest behaviour: expose `edited_file_id` only when a sidecar exists, label it "adjustment data",
  and copy it when *Include edited versions* is enabled. Never promise a rendered edit that does not
  exist. Some adjusted assets have no sidecar at all.

## 9. Moments / places

- `ZMOMENT` rows may have `ZTITLE` (place label) or `NULL`. The tested library had many rows but far
  fewer distinct titled places; many assets sit in untitled moments.
- Titles can contain non-breaking spaces (`\xa0`); normalise to regular spaces for display and sorting.
- Derivation: group `ZMOMENT`s by normalised `ZTITLE`; a place row selects assets whose `ZMOMENT` has
  that title. Assets in untitled moments remain visible under All/Camera Roll.
- `ZREVERSELOCATIONDATA` is an `NSKeyedArchiver` plist with address data. Parsing is optional and not
  needed for the sidebar. The no-fix sentinel is `-180.0` latitude/longitude.

## 10. Other observations

- `ZORIENTATION` looks EXIF-like, but Pillow's EXIF transpose on the decrypted file is authoritative;
  do not rotate twice.
- `ZDURATION` (seconds) is enough for video badges; `ZVIDEOCPDURATION*` also exists.
- `ZASSET.ZUUID` exists but `Z_PK` is stable and simpler for opaque IDs (`a<Z_PK>`).
- `ZASSET.ZMOMENT` is the only asset→moment link; `ZMOMENT.ZCACHEDCOUNT` is a cross-check.
- `ZTRASHEDDATE` is populated only for trashed rows.

## 11. Schema-variance strategy

1. Detect `ZASSET` vs `ZGENERICASSET` via `sqlite_master`; fail soft if neither exists.
2. Introspect with `PRAGMA table_info` and build SELECT lists from columns that exist.
3. Locate the album↔asset join table by scanning for album and asset foreign keys; never hard-code it.
4. Category rules: if a column is missing, omit that category and surface a notice; never crash.
5. Screenshot detection: prefer `ZISDETECTEDSCREENSHOT=1` when present, else `ZKINDSUBTYPE=10`.
6. Portrait: prefer `ZDEPTHTYPE` when present; older schemas may use `ZKINDSUBTYPE=3`.
7. Live Photos: `ZKINDSUBTYPE=2`, pair `.MOV` by basename; `ZINTERNALRESOURCE` fallback.
8. All timestamps via `+978307200`; timezone offset from `ZTIMEZONEOFFSET`, else machine zone.

## 12. Open questions / risks

- **Edited versions:** `.AAE` only on the tested library; UI copy must stay honest.
- **Thumbnail freshness:** V2 thumbnails are grid-sized; previews decode the original.
- **Moments:** many assets have no titled place; the UI shows only places.
- **`ZISDETECTEDSCREENSHOT` absent** on the tested iOS; never assume it.
- **Manifest size mismatch** for `Photos.sqlite` was seen; integrity check passed.

## 13. Reproduce

```powershell
.venv\Scripts\python.exe project-docs\spike_unlock.py
```

The script prints structure and counts locally, never prints the password, and writes decrypted
artefacts only to a temporary folder outside the backup. Its raw output must not be committed.

## 14. Implementation confirmation

`backend/photos/` implements these rules with runtime introspection. Unit tests use synthetic fixtures
for both `ZASSET` and `ZGENERICASSET`; integration tests compare against the owner's reference numbers
only when the ignored local file is supplied via `BACKUPLENS_REFERENCE_COUNTS`. The public test suite
asserts internal consistency without library-specific counts.
