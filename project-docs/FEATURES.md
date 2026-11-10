# FEATURES — matrix and acceptance criteria

Sources:
- **IBV** = features of iBackup Viewer (per its public descriptions): browse contacts, call history,
  messages, calendar, voicemails, voice memos, notes, photos, Safari history/bookmarks, installed
  apps and raw files; export photos to JPEG; filter photos by type (live, portrait, panorama,
  time-lapse, screenshots, slo-mo); call history to TXT/CSV; contacts to vCard; calendar to ICS;
  Safari data to HTML; messages (SMS/iMessage/WhatsApp/WeChat) to text/HTML/PDF; works with encrypted
  backups but its free tier limits exports.
- **ITBE** = MaxiHuHe04/iTunes-Backup-Explorer: hierarchical file browser; File Search tab with
  case-insensitive SQLite `LIKE` on domain and relative path (`%`, `_`, `\` escape), sortable
  columns, "Export matching", open/extract of single files, symlink target display; encrypted and
  non-encrypted backups from iOS 10.2.
- **USER** = stated requirement: local web app, encrypted backup with known password, Windows,
  download photos, no export limits, light backend, light frontend, UI like the reference screenshot.

Priority: **P0** must ship in v1 · **P1** next · **P2** later · **P3** nice to have.
Phase numbers refer to `AGENTS.md` §4.

## A. Backups and session

| ID | Feature | Src | Pri | Phase | Acceptance criteria |
|---|---|---|---|---|---|
| F-BKP-01 | Discover backups in default Windows paths (`%USERPROFILE%\Apple\MobileSync\Backup`, `%APPDATA%\Apple Computer\MobileSync\Backup`) | IBV | P0 | 2 | Lists every folder containing `Info.plist` + `Manifest.plist`; shows device name, model, iOS version, last backup date, size, encrypted flag |
| F-BKP-02 | Add custom backup folder | IBV | P0 | 2 | Validates the folder; persists in user config; handles missing/removed folder |
| F-BKP-03 | Unlock encrypted backup with password | USER | P0 | 1 | Correct password opens; wrong password → clear error, retry possible; password never logged/persisted |
| F-BKP-04 | Open unencrypted backup | ITBE | P1 | 2 | No password prompt; same UI |
| F-BKP-05 | Progress feedback while unlocking / indexing | — | P0 | 3 | Overlay with stage text and percentage where known |
| F-BKP-06 | Device info panel | IBV | P2 | 7 | Shows name, model, iOS, serial/IMEI if present, backup date, encrypted, UDID |
| F-BKP-07 | Close backup and purge temp data | — | P0 | 2 | Password zeroed, temp decrypted manifest removed |

## B. Photos and videos browser (the core)

| ID | Feature | Src | Pri | Phase | Acceptance criteria |
|---|---|---|---|---|---|
| F-PHO-01 | Sidebar categories: All, Camera Roll, Photos, Videos, Favorites, Live Photos, Portrait, Panoramas, Time-lapse, Slo-mo, Screenshots, Hidden, Trashed | IBV | P0 | 3 | Counts shown; zero counts hide the pill; counts within tolerance of the reference numbers in `ARCHITECTURE.md` §6.4 or deviations documented |
| F-PHO-02 | Albums list with counts | IBV | P0 | 3 | All user albums listed with correct counts |
| F-PHO-03 | Moments / places list | IBV | P1 | 3 | Alphabetical list; selecting filters the grid; omitted with a notice if not derivable |
| F-PHO-04 | Date-grouped thumbnail grid, newest first | IBV | P0 | 4 | Layout per `project-docs/UI_SPEC.md` §5, groups flow inline and wrap |
| F-PHO-05 | Virtualised scrolling and lazy thumbnails | USER | P0 | 4 | 5k assets scroll smoothly; ≤ 300 DOM tiles |
| F-PHO-06 | Thumbnails from backup's own thumbnails when available, else generated + cached | — | P0 | 5 | Second visit loads from cache; no full-size decode for cached tiles |
| F-PHO-07 | Preview lightbox with keyboard nav | IBV | P0 | 4 | Arrows/Esc work; HEIC displayed as JPEG; zoom; info panel |
| F-PHO-08 | Video playback with seeking | IBV | P0 | 5 | `<video>` plays MOV/MP4 from `/original` with Range requests; if browser cannot decode HEVC/MOV, show "Download to play" hint |
| F-PHO-09 | Live Photo playback (paired MOV) | IBV | P1 | 5 | "Live" control plays paired clip |
| F-PHO-10 | Media type filter (All / Photos / Videos) | IBV | P0 | 4 | Client-side filter updates grid and counts instantly |
| F-PHO-11 | Date jump via calendar popover | IBV | P1 | 4 | Days with items highlighted; picking scrolls to group |
| F-PHO-12 | Original filenames shown/used | IBV | P0 | 3 | Filename shown in info panel and used in export |
| F-PHO-13 | Edited photo support (original + rendered edit) | IBV | P1 | 3 | Both exposed; export option *Include edited versions* |
| F-PHO-14 | Search by filename / date range | — | P2 | 7 | Debounced query; combinable with scope |
| F-PHO-15 | Map/location view | — | P3 | — | Optional; out of scope for v1 |
| F-PHO-16 | Duplicate hints | — | P3 | — | Optional |

## C. Selection and export (the part commercial apps restrict)

| ID | Feature | Src | Pri | Phase | Acceptance criteria |
|---|---|---|---|---|---|
| F-EXP-01 | Multi-select: click, Shift range, Ctrl toggle, Select all in view | IBV | P0 | 4 | Counter updates; selection survives filter changes where items remain visible |
| F-EXP-02 | Export **selected** to a folder | USER | P0 | 6 | Files appear with original names; progress; cancel; errors listed; byte-identical to the decrypted original |
| F-EXP-03 | Export **current folder/scope** ("Current Folder" button) | IBV | P0 | 6 | Count matches sidebar; respects type filter |
| F-EXP-04 | Export **everything** | USER | P0 | 6 | Works for 5k+ assets without browser involvement or memory blow-up |
| F-EXP-05 | Convert HEIC → JPEG option | IBV | P0 | 6 | Quality ≥ 90, EXIF orientation applied, EXIF retained where possible |
| F-EXP-06 | Include paired Live Photo video | IBV | P1 | 6 | Same basename, `.MOV` |
| F-EXP-07 | Folder layout: flat / by date / by album / original path | — | P1 | 6 | Directory structure verified by test |
| F-EXP-08 | Conflict policy: skip / rename / overwrite | — | P0 | 6 | Verified by test |
| F-EXP-09 | Preserve capture date as file modified time | — | P1 | 6 | mtime equals capture date |
| F-EXP-10 | ZIP download for small selections | USER | P1 | 6 | ≤ 500 items / 2 GB; streamed, store-only |
| F-EXP-11 | Atomic writes and resumable-friendly behaviour (skip existing) | — | P0 | 6 | Interrupted export leaves no partial files without `.part` suffix |
| F-EXP-12 | Export report | — | P2 | 6 | `export-report.txt` with counts and failures |
| F-EXP-13 | **No artificial limits** (count, size, formats) | USER | P0 | 6 | Nothing in code gates features behind licenses or caps other than documented ZIP size guard |

## D. Raw file explorer (iTunes-Backup-Explorer parity)

| ID | Feature | Src | Pri | Phase | Acceptance criteria |
|---|---|---|---|---|---|
| F-RAW-01 | Hierarchical browser by domain → path | ITBE | P1 | 7 | Expand folders lazily; sizes and dates shown |
| F-RAW-02 | File Search with SQL `LIKE` on domain and path | ITBE | P1 | 7 | `%`, `_`, `\` escape, case-insensitive; presets (Camera Roll videos `%.mov`, DCIM `Media/DCIM/%`, `%.sqlite`, WhatsApp `%whatsapp%`) |
| F-RAW-03 | Sort by column, find largest files | ITBE | P1 | 7 | Click header toggles asc/desc |
| F-RAW-04 | Export matching / selected raw files | ITBE | P1 | 7 | Preserves relative paths under chosen destination |
| F-RAW-05 | Open/preview a single file (text, image, sqlite table view, plist) | ITBE | P2 | 7 | Safe viewer; large files truncated with notice |
| F-RAW-06 | Show symlink target | ITBE | P3 | — | Optional |
| F-RAW-07 | Replace/delete files in backup | ITBE | — | — | **Explicitly out of scope** (read-only app) |

## E. Messages and other data (IBV parity, later phases)

| ID | Feature | Src | Pri | Phase | Notes |
|---|---|---|---|---|---|
| F-MSG-01 | SMS/iMessage conversation viewer | IBV | P2 | 8+ | `Library/SMS/sms.db` in `HomeDomain`; bubbles UI, attachments inline |
| F-MSG-02 | Export conversation: TXT, HTML, PDF | IBV | P2 | 8+ | PDF via a light library or browser print stylesheet |
| F-WAP-01 | WhatsApp viewer and export | IBV | P2 | 8+ | `ChatStorage.sqlite` in the WhatsApp group domain; media from the same domain |
| F-CON-01 | Contacts viewer, export vCard | IBV | P2 | 8+ | `AddressBook.sqlitedb` |
| F-CAL-01 | Call history viewer, export TXT/CSV | IBV | P2 | 8+ | `CallHistory.storedata` |
| F-CAL-02 | Calendar viewer, export ICS | IBV | P3 | 8+ | `Calendar.sqlitedb` |
| F-NOT-01 | Notes viewer, export | IBV | P2 | 8+ | `NoteStore.sqlite`; rich text/protobuf handling is non-trivial |
| F-SAF-01 | Safari history and bookmarks, export HTML | IBV | P3 | 8+ | `History.db`, `Bookmarks.db` |
| F-VOI-01 | Voice memos / voicemail playback + export | IBV | P3 | 8+ | `Recordings` |
| F-APP-01 | Installed apps list + app data browse | IBV | P3 | 8+ | From `Manifest.plist` / `Info.plist` / `AppDomain-*` |

## F. Platform, quality and project

| ID | Feature | Pri | Phase | Acceptance criteria |
|---|---|---|---|---|
| F-SEC-01 | Localhost-only binding with token, Host/Origin checks, CSP | P0 | 2 | Security tests pass (see `ARCHITECTURE.md` §12) |
| F-SEC-02 | Password never persisted/logged | P0 | 1 | Log-capture test |
| F-SEC-03 | Read-only access to the backup folder | P0 | 1 | No write calls under the backup path (static check + test) |
| F-PLT-01 | Windows 10/11 support with Python 3.11+ | P0 | 1 | Documented in `SETUP.md`; CI optional |
| F-PLT-02 | One-command start (`python backend/app.py`) that opens the browser | P0 | 2 | Prints URL, opens default browser, picks a free port |
| F-PLT-03 | Settings: cache location/limit, theme, date grouping zone, thumbnail size | P1 | 7 | Persisted in `%LOCALAPPDATA%\BackupLens\config.json` |
| F-PLT-04 | Clear cache action | P0 | 5 | Frees the thumbnail/preview cache |
| F-PLT-05 | PyInstaller build | P2 | 9 | Optional single-folder distribution |
| F-DOC-01 | README, ARCHITECTURE, SETUP, UI_SPEC, FEATURES, AGENTS, PROMPT_LOG kept current | P0 | all | Release Agent checks at each phase exit |
| F-TST-01 | Unit + contract tests; integration tests gated by env vars | P0 | all | `pytest` passes; integration skipped without env |
| F-ACC-01 | Keyboard accessibility and ARIA labels | P1 | 4 | Manual checklist in `project-docs/UI_SPEC.md` §12 |

## G. Out of scope for v1
iCloud backup download · restoring to device · editing/deleting inside backups · cloud/multi-user
hosting · mobile-first layout · face/scene recognition · AI search.

## H. Definition of Done (applies to every feature)

1. Code merged to the phase branch with tests (or documented manual test when UI-only).
2. Acceptance criteria above verified and ticked in this file's status column (add `✅ date`).
3. Docs updated if behaviour or API changed.
4. No lint errors (ruff for Python; basic ESLint-free vanilla JS style), no console errors in browser.
5. Entry appended to `PROMPT_LOG.md` for the work.

## I. Verification status (updated at each phase; evidence lives in `PROMPT_LOG.md`)

Status: ✅ verified · 🟨 partially verified (note says what remains) · ⬜ not started

| ID | Status | Date | Evidence / remaining work |
|---|---|---|---|
| F-BKP-01 | ✅ | 2026-10-28 | `backend/backup/discovery.py` + `tests/test_backup_discovery.py`; live smoke test listed the real backup with name/model/iOS/date/size/encrypted |
| F-BKP-02 | ✅ | 2026-10-28 | `POST /api/backups/add` persists to config (`test_add_backup_folder_persists_in_config`); missing folders are skipped (`test_ignores_missing_extra_paths`) |
| F-BKP-03 | ✅ | 2026-10-28 | `tests/test_backup_integration.py::test_real_wrong_password_is_typed_and_never_logged`; retry path is stateless |
| F-BKP-04 | ✅ | 2026-10-28 | Core + HTTP path verified (`test_api_unencrypted.py`, `test_open_unencrypted_and_read_files`) |
| F-BKP-05 | ✅ | 2026-10-28 | Progress overlay stages map to `/api/session` (`starting/extracting/reading/resolving/ready/failed`); mock and real contract tested |
| F-BKP-07 | ✅ | 2026-10-28 | `Session.close()` removes the decrypted manifest and shuts the worker; `test_close_removes_temp_and_blocks_queries` |
| F-PHO-04 | ✅ | 2026-10-28 | Date-grouped virtualised grid; groups flow/wrap; 1920×1080 screenshot |
| F-PHO-05 | ✅ | 2026-10-28 | Virtualisation: ~25 DOM tiles / ~9 groups for a several-thousand-asset mock at 1920×1080 |
| F-PHO-06 | ✅ | 2026-10-28 | Prefers the backup's V2 `5005.JPG`; disk cache hit avoids decode (warm 100 thumbs 0.10 s vs 3.28 s cold) |
| F-PHO-07 | ✅ | 2026-10-28 | Photo preview, arrows/Esc/zoom/info verified; videos use `<video controls>` on Range `/original` |
| F-PHO-08 | ✅ | 2026-10-28 | `/original` returns 206 + `Content-Range` + `Accept-Ranges`; `video/*` content type; UI shows a download hint if the codec fails |
| F-PHO-09 | ✅ | 2026-10-28 | `/api/media/{id}/live` streams the paired MOV with Range (206 verified against the real backup) |
| F-PLT-04 | ✅ | 2026-10-28 | `POST /api/cache/clear` + menu action; integration test clears a populated cache |
| F-PLT-05 | ✅ | 2026-10-28 | `scripts/build_exe.py` built `dist/BackupLens/BackupLens.exe`; launched, served the UI and listed the real backups. Clean-profile (no Python) not tested |
| F-DOC-01 | ✅ | 2026-10-28 | README/SETUP/ARCHITECTURE/FEATURES/UI_SPEC/QA/RELEASE/THIRD_PARTY current; reference screenshot git-ignored |
| F-PHO-10 | ✅ | 2026-10-28 | Client-side All/Photos/Videos filter, no reload (album + Photos filter verified) |
| F-PHO-11 | ✅ | 2026-10-28 | Calendar popover highlights days with items and scrolls to the group (verified) |
| F-PHO-14 | ✅ | 2026-10-28 | Debounced filename search + date-range dialog, combinable with scope (verified `IMG_0001` → 1 item; range narrows further) |
| F-RAW-01 | ✅ | 2026-10-28 | Domain list + lazily loaded folder tree; sizes and mtimes from the manifest |
| F-RAW-02 | ✅ | 2026-10-28 | Case-insensitive LIKE on domain and path with `%`, `_`, `\` escape; all four presets |
| F-RAW-03 | ✅ | 2026-10-28 | Sortable Domain/Path/Size/Modified headers, asc/desc |
| F-RAW-04 | ✅ | 2026-10-28 | Export selected or matching to a folder; `<domain>/<relativePath>` preserved; job + report |
| F-RAW-05 | ⬜ | 2026-10-28 | P2 rich viewer not built; files can be downloaded, not previewed in-app |
| F-RAW-06 | 🟨 | 2026-10-28 | Symlink target is returned by the tree API; not displayed in the table (P3) |
| F-PLT-03 | ✅ | 2026-10-28 | Theme, date-grouping zone, thumbnail size, cache location and limit persisted in config.json |
| F-EXP-01 | ✅ | 2026-10-28 | Click/Ctrl/Shift selection, Select all, clear, counter; export dialog receives exact counts |
| F-EXP-02 | ✅ | 2026-10-28 | `POST /api/export`; 20 real files byte-identical to `Session.read_file`; progress/cancel/errors; report |
| F-EXP-03 | ✅ | 2026-10-28 | Scope export tested with the Panorama category (2 assets); UI Current Folder sends the exact scope |
| F-EXP-04 | ✅ | 2026-10-28 | Server-side job; no browser involvement, no count/size cap (ZIP is the only guarded path) |
| F-EXP-05 | ✅ | 2026-10-28 | HEIC→JPEG quality 92, EXIF orientation applied and orientation tag reset |
| F-EXP-06 | ✅ | 2026-10-28 | Live still + paired `.MOV` exported with the same basename (integration test) |
| F-EXP-07 | ✅ | 2026-10-28 | flat / by-date / by-album / original-path covered by unit tests |
| F-EXP-08 | ✅ | 2026-10-28 | skip / rename / overwrite covered by unit + integration tests |
| F-EXP-09 | ✅ | 2026-10-28 | mtime equals `takenAt` when `setFileDates` is on (integration test) |
| F-EXP-10 | ✅ | 2026-10-28 | Store-only ZIP streamed from disk; ≤500 items / 2 GB guard; contents byte-compared |
| F-EXP-11 | ✅ | 2026-10-28 | All writes go through `.part` then `os.replace`; cancel leaves no `.part` files |
| F-EXP-12 | ✅ | 2026-10-28 | `export-report.txt` with counts, errors and cancelled flag |
| F-EXP-13 | ✅ | 2026-10-28 | No artificial limits in code; only the documented ZIP guard |
| F-ACC-01 | 🟨 | 2026-10-28 | ARIA labels/listbox, focus rings, arrow-key sidebar, Tab focus trap in dialogs; screen-reader pass not run |
| F-PHO-01 | ✅ | 2026-10-28 | `/api/library/sidebar` matches the local reference counts when the optional file is supplied |
| F-PHO-02 | ✅ | 2026-10-28 | User albums via `ZGENERICALBUM.ZKIND=2` + join introspection; counts recomputed from the join |
| F-PHO-03 | ✅ | 2026-10-28 | Titled places from `ZMOMENT.ZTITLE`, normalised and alphabetical; filter tested |
| F-PHO-12 | ✅ | 2026-10-28 | `originalName`/filename in asset detail and compact rows; filenames from the real library |
| F-PHO-13 | ✅ | 2026-10-28 | Original + `.AAE` adjustment sidecar exposed (CR-001); rendered edits do not exist in this backup |
| F-SEC-01 | ✅ | 2026-10-28 | `tests/test_api_security.py`: token, Host, Origin, Sec-Fetch-Site, CSP, gzip |
| F-SEC-02 | ✅ | 2026-10-28 | Log/stdio capture tests with wrong and correct password; session stores no password |
| F-SEC-03 | ✅ | 2026-10-28 | Integration test verifies payload/manifest mtimes and sizes unchanged after reads/exports |
| F-PLT-01 | ✅ | 2026-10-28 | Windows 10/11 + Python 3.13.1 (≥3.11) exercised end-to-end in `SETUP.md` §3/§10 |
| F-PLT-02 | ✅ | 2026-10-28 | Live smoke: `python backend\\app.py --port 5097 --no-browser` printed a token URL, served `/`, rejected token-less API; `find_free_port` unit-tested. Browser auto-open is manual (not automatable here) |
| F-TST-01 | ✅ | 2026-10-28 | 106 unit/contract + 15 integration green; `project-docs/QA_REPORT.md` records gates and scenarios |
