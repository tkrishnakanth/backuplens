# PROMPT_LOG

Purpose: a durable record of every prompt given to an AI agent, what it produced, and what you
decided. It also carries the **ready-to-paste phase prompts** so you can drive the build in order.

## How to use this file

1. Pick the next unchecked prompt (P-xxx) below. Copy the text in its code block into opencode.
2. Right after the run, fill in its **Outcome** block (date, model, result, notes, link to commit/PR).
3. If you write an ad-hoc prompt, append a new entry using the template in §3. **Never delete or
   rewrite old entries**; add corrections as new entries.
4. **Never paste the backup password or any personal data into a prompt or into this file.** The app
   reads the password from the UI or from a local `.env` that is git-ignored.
5. When an agent reports `NEXT:` or raises a question, log it as a Change Request (§4).

## 1. Context block (paste at the start of EVERY new opencode session)

```
You are working on the BackupLens repo. Before doing anything, read in this order:
README.md, ARCHITECTURE.md, project-docs/FEATURES.md, project-docs/UI_SPEC.md, AGENTS.md, the last 5 entries of
PROMPT_LOG.md, and project-docs/schema-notes.md if it exists. Follow AGENTS.md section 1 strictly.
Work only on the task I give you, stop at its Definition of Done, and finish with the Standard report
format from AGENTS.md. If anything is ambiguous, ask me before coding. Never print or store the
backup password.
```

## 2. Prompt catalogue (run in order)

Legend: ⬜ not run · 🟨 partially · ✅ done

### P-000 — Original human request (recorded for history)  ✅
- **Date:** 2026-10-28 · **By:** project owner · **To:** Claude (planning)
- **Request (summary):** Build a lightweight local web app (Go or Python backend, very light
  frontend) to browse and download photos from an encrypted iPhone backup on Windows, with UI replicating
  iBackup Viewer's photo browser (reference screenshot), replicating its features as far as possible, no
  export limits. Deliver architecture.md, prompt log, agent creation/assignment file, README, setup.md so
  an opencode + DeepSeek workflow can build it and push it to GitHub.
- **Outcome:** this documentation set (README, ARCHITECTURE, AGENTS, PROMPT_LOG, SETUP, docs/FEATURES,
  docs/UI_SPEC).

---

### P-001 — Orientation (no code)  ✅
**Agent:** architect (plan/read-only mode)
```
Act as the architect agent. Read all project docs as described in the context block. Then produce:
1) A 15-line summary of what we are building and the stack decisions.
2) A list of any contradictions, gaps or risky assumptions you found in the docs (be specific, cite
   file and section).
3) A checklist of what you need from me (e.g. backup path, iOS version, Python version).
Do not write or change any code or files. Wait for my answers.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · all docs read. Findings: docs were
mis-laid-out at repo root (`FEATURES.md`, `UI_SPEC.md`, reference image) — moved to `docs/` and
`project-docs/local/` (reference image git-ignored). Docs reference `docs/...` paths throughout, so this
was a layout fix, not a spec change. Environment: Python 3.13.1, backup found at the default
location, encrypted, a recent iOS 17.x release. One blocking item: `.env` with `BACKUP_PATH`/`BACKUP_PASSWORD`
was missing; the owner created it before Phase 0. No code written.

### P-002 — Phase 0: spike on the real backup  ✅
**Agent:** photos (with core)
**Prereq:** `pip install iphone_backup_decrypt`; `BACKUP_PATH` set; password in local `.env` as `BACKUP_PASSWORD`.
```
Act as the photos agent, supported by core. Task: Phase 0 from AGENTS.md section 4.
Create project-docs/spike_unlock.py that, using env vars BACKUP_PATH and BACKUP_PASSWORD (load from a local
.env with a tiny parser; never print the password):
1) Opens the encrypted backup with iphone_backup_decrypt, runs test_decryption(), saves the decrypted
   Manifest.db to a temp folder.
2) Prints: device name, product type, iOS version, last backup date, total file count, count per domain
   (top 15).
3) Lists the CameraRollDomain files under Media/PhotoData/ (names and sizes), and whether any
   Thumbnails directories exist, with 3 example paths.
4) Extracts Media/PhotoData/Photos.sqlite (and -wal/-shm if present) to the temp folder and prints:
   all table names, and PRAGMA table_info for the asset table (ZASSET or ZGENERICASSET),
   ZADDITIONALASSETATTRIBUTES, the album table and the album-asset join table (find it via
   sqlite_master), and ZMOMENT if present.
5) Prints 5 sample asset rows (columns: directory, filename, kind, kindsubtype, date, favorite, hidden,
   trashedstate, playbackstyle, savedassettype, depthtype, screenshot flag, width, height, duration).
6) Prints distinct values and counts for kindsubtype, playbackstyle, savedassettype, depthtype,
   trashedstate, hidden, favorite.
7) Computes candidate counts for: All, Camera Roll, Photos, Videos, Favorites, Live Photos, Portrait,
   Panoramas, Time-lapse, Slo-mo, Screenshots, Hidden, Trashed, and for each album.
Then write project-docs/schema-notes.md recording everything found, the SQL rule you propose for each
category, how Camera Roll differs from All, and how Moments/places could be derived. Compare your counts
with the owner's local reference file (kept outside the public repo) and explain differences.
Also check and state the licence of iphone_backup_decrypt. Do not guess any column meaning: show the
query evidence. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE** (architect self-review).
The spike unlocked the real encrypted backup and decrypted `Photos.sqlite`; `PRAGMA integrity_check`
returned `ok`. Findings are recorded in the sanitised `project-docs/schema-notes.md`; the raw notes and
reference numbers stay in `project-docs/local/` and are never published. **Every reference count
matched** with these rules: All = every asset row (including trashed); Camera Roll =
`ZSAVEDASSETTYPE=3 AND trashed=0`; Photos = `ZKIND=0`; Videos = `ZKIND=1`; Favorites = `ZFAVORITE=1`;
Live = `ZKINDSUBTYPE=2`; Portrait = `ZDEPTHTYPE=1`; Panoramas = `ZKINDSUBTYPE=1`; Slo-mo =
`ZKINDSUBTYPE=101`; Screenshots = `ZKINDSUBTYPE=10`; Trashed = `ZTRASHEDSTATE=1`; Time-lapse and Hidden
were zero and rendered without a pill. Surprises:
(1) **every indexed asset had a pre-rendered V2 thumbnail** at
`Media/PhotoData/Thumbnails/V2/<dir>/<filename>/5005.JPG` — the grid can skip HEIC decoding;
(2) `ZISDETECTEDSCREENSHOT` did not exist on the tested schema; `ZKINDSUBTYPE=10` was exact;
(3) every indexed original resolved via `Media/<ZDIRECTORY>/<ZFILENAME>`;
(4) Live Photos paired by same-name `.MOV`;
(5) edited assets had **only `.AAE` adjustment sidecars**, no rendered edit — logged as
CR-001. Library licence: **MIT**.

### P-003 — Phase 1: backup core  ✅
**Agent:** core
```
Act as the core agent. Task: Phase 1 from AGENTS.md section 4, using project-docs/schema-notes.md.
Implement backend/backup/ per ARCHITECTURE.md sections 3, 4, 5 and 10:
- plist readers for Info.plist and Manifest.plist (plistlib) returning a typed BackupInfo.
- open_backup(path, password|None) -> Session: validates, unlocks, decrypts Manifest.db once to a
  private temp dir (user-only permissions), exposes read-only per-thread SQLite access to the decrypted
  manifest, and a single dedicated worker thread for every call into iphone_backup_decrypt.
- Session.read_file(file_id) / extract_file(file_id, dest) that never buffers huge files fully in memory
  when avoidable, and never writes inside the backup folder.
- Errors: WrongPassword, NotABackup, ManifestMissing, UnsupportedVersion, PayloadMissing (typed).
- Session.close(): remove temp files, drop references to the password.
Write pytest tests (unit with mocks, plus @integration tests gated by BACKUP_PATH/BACKUP_PASSWORD that
unlock the real backup and byte-compare 5 extracted files with the library's own extract_file).
Add a test proving the password never appears in captured log output. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented
`backend/backup/` with typed errors, plist readers, discovery, and `Session`:
* single `ThreadPoolExecutor(max_workers=1)` owns every `iphone_backup_decrypt` call (verified by test);
* `Manifest.db` decrypted once to a user-only temp folder; `manifest_query` uses per-call read-only
  SQLite connections (`mode=ro`, `query_only=ON`) so request threads never block on decryption;
* `read_file` / `extract_file` stream through `aes_decrypt_chunked` and write atomically via `.part`;
  destinations inside the backup folder are refused; non-encrypted backups supported;
* `close()` removes decrypted temp data, clears the library's temp copy, shuts the worker;
* password is accepted as bytes for unlock, a bytearray copy is zeroed, and no password reference is
  retained by `Session` (Python strings are immutable — documented limitation).
Evidence: `21` unit tests and `5` integration tests green; integration test unlocks the real backup and
byte-compares the first five CameraRoll files with `EncryptedBackup.extract_file_as_bytes`, asserts
wrong-password messages/logs never contain the password, and verifies backup mtimes/sizes are unchanged.
`ruff check .` clean.

### P-004 — Phase 2: API skeleton, security, launcher  ✅
**Agent:** api
```
Act as the api agent. Task: Phase 2 from AGENTS.md section 4.
Create backend/app.py (Flask app factory, Waitress, free port on 127.0.0.1, prints the URL and opens the
default browser), requirements.txt (pinned), .gitignore (see SETUP.md section 7), and backend/api/ with:
- security: per-launch random token (cookie HttpOnly, SameSite=Strict), Host and Origin checks, CSP and
  security headers, consistent JSON error model, gzip, redacting logger.
- routes from ARCHITECTURE.md section 7.1 (/api/backups, /api/backups/add, /api/session/open,
  /api/session, /api/session/close) using backend/backup/ via its public interface only.
- discovery of backups in the default Windows locations plus user-added paths stored in
  %LOCALAPPDATA%\BackupLens\config.json.
- a job manager skeleton (in-memory) for later export jobs.
- serve frontend/ as static files, with a placeholder index.html.
Write contract tests with Flask's test client and a fake Session: bad token, bad Host, bad Origin,
wrong password -> 401 wrong_password, already_open -> 409. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented
`backend/app.py` (app factory + Waitress launcher on 127.0.0.1, free port, printed token URL, browser
open), `backend/api/` (security, errors, config store, session manager, job manager, routes) and the
placeholder frontend. Security: per-launch token in an HttpOnly/SameSite=Strict cookie or
`X-BackupLens-Token` header, Host allow-list (127.0.0.1/localhost), Origin + `Sec-Fetch-Site` checks
on unsafe methods, CSP, no-store JSON, gzip, access log without query strings, redacting logger.
Backups stored in `%LOCALAPPDATA%\BackupLens\config.json`; session open gives 401 `wrong_password`
and 409 `already_open` as specified. Evidence: 51 unit/contract tests + 7 integration tests green;
live launcher smoke on port 5097 served `/`, listed the real backup (recent iOS, encrypted, size reported)
and rejected token-less API calls. `ruff check .` clean. Browser auto-open is the only manual check.

### P-005 — Phase 3: library index  ✅
**Agent:** photos
```
Act as the photos agent. Task: Phase 3 from AGENTS.md section 4, strictly following
project-docs/schema-notes.md (the evidence you gathered in Phase 0).
Implement backend/photos/ producing the normalised schema in ARCHITECTURE.md section 6.3:
variant detection by introspection (never assume columns), assets, categories (All, Camera Roll,
Photos, Videos, Favorites, Live Photos, Portrait, Panoramas, Time-lapse, Slo-mo, Screenshots, Hidden,
Trashed), albums, moments/places, original filenames, paired Live Photo video, edited-version pairing,
thumbnail file lookup, local-day grouping helper.
Wire GET /api/library/sidebar, GET /api/library/assets (compact format from section 7.5, gzip), and
GET /api/library/assets/{id}, plus index build progress in /api/session. Unit-test with hand-built
Photos.sqlite fixtures for both ZASSET and ZGENERICASSET variants. Add an @integration test that prints
the real counts next to the reference numbers. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented
`backend/photos/` (schema introspection, loader, `LibraryIndex`, `build_index`) and `/api/library/*`.
Variant detection handles `ZASSET`/`ZGENERICASSET`, missing optional columns, generic album join
tables, and optional moments. Background index build (ADR-007) takes under a second for a
several-thousand-asset library. The real sidebar matched the owner's local reference counts exactly;
the titled places are grouped from `ZMOMENT.ZTITLE` (NBSP-normalised) and sorted alphabetically.
Originals and V2 thumbnails resolved for every indexed asset; Live Photos paired with `.MOV`; edited
assets expose `.AAE` where present (CR-001). Unit fixtures cover both asset-table variants plus a minimal older
schema. Evidence: 71 unit/contract + 7 integration tests green; `ruff check .` clean. Progress is
exposed via `/api/session` (`indexState`, `progress`); `/api/library/*` returns 409 until ready.

### P-006 — Phase 4a: frontend shell, sidebar, home view (mock API)  ✅
**Agent:** ui
```
Act as the ui agent. Task: Phase 4 part A. Read project-docs/UI_SPEC.md fully and look at the reference image in
project-docs/local/. Build frontend/ with vanilla HTML/CSS/ES modules, no framework, no build step, no
external requests. Implement: design tokens (section 2), header with title + badge + device icon +
Unique ID + hamburger, the toolbar buttons (calendar, Current Folder, All dropdown, selection toggle),
sidebar per section 4 (exact order, icons as inline SVG, count pills, selected state, Albums and Moments
groups, own scrollbar), status bar per section 6, and the Home view of discovered backups with the
password dialog and progress overlay. Use a mock API in frontend/mock/ (plain JSON + a tiny fetch shim
switched by ?mock=1) with several thousand synthetic assets across 40 albums/places so we can develop before the real
backend is ready. Produce a screenshot at 1920x1080 and list every deviation from the reference.
Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Built the vanilla HTML/CSS/ES
module shell with the exact UI_SPEC tokens, header/toolbar, sidebar (all 13 categories, albums, moments,
count pills, blue selected row), status bar and the Home view (backup cards, add-folder dialog, password
dialog, progress overlay). A deterministic `?mock=1` API generates several thousand assets, 20 albums + 20 places
and self-contained SVG `data:` thumbnails, so there are zero external requests. Screenshots:
`docs/screenshots/mock-home.png` and `mock-browser.png`. The mock demo only adds a small "DEMO" badge.

### P-007 — Phase 4b: grid, virtualisation, selection, lightbox  ✅
**Agent:** ui
```
Act as the ui agent. Task: Phase 4 part B. Implement the main grid exactly as project-docs/UI_SPEC.md section 5:
date groups as inline blocks that flow and wrap (never split a group unless wider than a row), bold date
headers like "Tue, Sep 10, 2024", square cover-cropped tiles ~294px at 1920px, 5px gaps, ~65px vertical
gap, virtualised rendering (<=300 DOM tiles with several thousand assets), IntersectionObserver lazy thumbnails with
request cancellation, hover/selection circles, click, Shift-range and Ctrl-toggle selection, Select all,
the All type filter, the calendar date-jump popover, and the lightbox (section 8). Verify scroll
performance with the several thousand-item mock and report DOM node counts and frame behaviour. Finish with the
Standard report and tick the UI checklist in section 12.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE (Phase 4 scope)**. Implemented a
true virtualised grid with its own flow layout: date groups are absolutely positioned from a measured
layout, so small groups share a row, wide groups wrap internally, and only ~25–26 tiles / 9 groups are in
the DOM for several thousand assets at 1920×1080 (target ≤300). Lazy thumbnails use viewport-aware loading +
IntersectionObserver cancellation; 11 of 25 rendered tiles requested images on first paint. Selection
supports click/Ctrl/Shift/count, Select all and clear; the type filter is instant; the calendar popover
highlights 17 days in the mock and scrolls to the chosen group; the lightbox supports arrows/Esc/zoom/info,
preloads neighbours and shows a download hint when a video codec is unsupported. UI_SPEC §12 is ticked with
two honest open items (video/Live playback pending Phase 5; Firefox/Edge smoke tests pending Phase 8).
Screenshots: `mock-browser.png`, `mock-lightbox.png`, `mock-export.png`. `ruff check .` clean; backend suite
still green.

### P-008 — Phase 5: media pipeline  ✅
**Agent:** media
```
Act as the media agent. Task: Phase 5 from AGENTS.md section 4, per ARCHITECTURE.md section 8.
Implement backend/media/ and the routes /api/media/{id}/thumb, /preview, /original (HTTP Range), /live.
Prefer the backup's own thumbnails when project-docs/schema-notes.md says they exist; otherwise generate with
Pillow + pillow-heif (EXIF orientation applied), cache on disk with an LRU size cap, video posters via
backup thumbnails or ffmpeg if available else placeholder. Never buffer large videos in RAM. Add
Clear cache. Measure and report: time for the first 100 thumbnails cold and warm. Handle undecodable
files with a placeholder, not an error. Add tests (including a Range request test). Finish with the
Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented `backend/media/`
(`cache.py`, `pipeline.py`, errors) and the four media routes plus cache stats/clear. Thumbnails prefer
the backup's V2 `5005.JPG`, fall back to Pillow (+ pillow-heif, EXIF transpose) on the original, then
ffmpeg for video posters when available, then a generated JPEG placeholder. Previews are capped at 2048 px;
originals are decrypted once to a per-backup LRU cache and streamed from disk with HTTP Range (verified
`206`, `Content-Range`, `Accept-Ranges`); unencrypted backups stream the payload directly. Large videos are
never buffered in RAM. The cache lives in `%LOCALAPPDATA%\BackupLens\cache`, is capped at 2 GB by default,
and is cleared on exit or via the menu/action (ADR-008; `CACHE_PERSIST` can opt in). **Measured 100
thumbnails: 3.28 s cold, 0.10 s warm.** Undecodable files return a valid placeholder JPEG, not an error.
Tests: 84 unit/contract + 7 integration green, including Range requests, Live `.MOV` streaming, thumbnail
preference, EXIF rotation, cache hit/eviction/clear. A real-browser check at 1920×1080 rendered the true
counts and 12 visible thumbnails; the personal screenshot was deleted and the cache wiped.

### P-009 — Phase 6: export  ✅
**Agent:** export
```
Act as the export agent. Task: Phase 6 from AGENTS.md section 4, per ARCHITECTURE.md section 9 and
project-docs/FEATURES.md F-EXP-01..13.
Implement backend/export/ and routes POST /api/export, GET /api/jobs/{id}, POST /api/jobs/{id}/cancel,
POST /api/export/zip, POST /api/fs/pick-folder (tkinter, optional). Options: scope or ids, destination,
HEIC->JPEG, include Live video, include edited, layout (flat/by-date/by-album/original-path), conflict
policy, set file dates. Atomic writes via .part files, cooperative cancel, per-file error collection, an
export-report.txt, refusal of destinations inside the backup folder. Jobs must not starve interactive
thumbnail requests. Tests: byte-compare 20 real files (integration), conflict policies, cancel
mid-run, bad destination. Then wire the export dialog in the frontend only if the ui agent has finished
Phase 4; otherwise leave a documented TODO. No artificial limits. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented `backend/export/`
(request validation, planner, atomic writer with HEIC→JPEG, runner, ZIP, tkinter folder picker) and the
`/api/export`, `/api/export/zip`, `/api/fs/pick-folder` routes on top of the existing job endpoints and the
Phase 4 export dialog (already wired to this contract). Supports ids or scope, all four layouts, skip/rename/
overwrite, Live/edited companions, capture-date mtimes, `.part` atomic writes, cooperative cancel, per-file
error collection and `export-report.txt`. Destinations inside the backup are refused; every output path is
`realpath`-checked, so traversal/symlink escapes fail. No count/size limits; only the documented ZIP guard
(≤500 items / 2 GB, store-only). Decryption goes through the single worker, so thumbnails interleave between
files. Evidence: **20 real files exported and byte-identical** to `Session.read_file`; conflict policies,
scope export, Live `.MOV`, HEIC→JPEG, ZIP contents, cancel mid-run (no `.part` left) and bad destination all
tested. 97 unit/contract + 14 integration tests green; `ruff check .` clean.

### P-010 — Phase 7: raw file explorer, settings, filename search  ✅
**Agent:** api (lead), ui, core
```
Act as the api agent with help from core and ui. Task: Phase 7. Implement the raw file explorer per
project-docs/FEATURES.md section D: /api/files/domains, /tree, /search (case-insensitive SQLite LIKE with % _ and
backslash escape on domain and relative path, sortable columns, pagination), /files/{id}/download,
/files/export (job). Frontend: a "Files" view reachable from the hamburger menu with a domain/path tree,
a search form with the preset queries from FEATURES F-RAW-02, sortable results table, export matching.
Add Settings (cache limit/location, theme, time zone for grouping, thumbnail size) persisted in
%LOCALAPPDATA%\BackupLens\config.json, and filename/date-range search in the photo view. Do NOT implement
replace/delete of backup files. Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Implemented `backend/files/`
(domains, tree, LIKE search with sorting/pagination, raw download, raw export job) and the `/api/files/*`
routes, plus `/api/settings` with persistence in `config.json`. The frontend gains a Files view (domain
selector, lazy folder tree, presets, sortable results, select/download/export) and a Settings dialog for
theme, date-grouping zone, thumbnail size and cache location/limit (dark theme included). The photo view
now has debounced filename search and a date-range dialog that combine with the sidebar scope and type
filter. Raw export preserves `<domain>/<relativePath>` and writes a report. No replace/delete actions
exist. Evidence: unit tests for tree/search/sort/escape/raw export + settings validation/persistence;
integration test browsing CameraRoll, searching `%.JPG` with size sort, Range download and raw export; live
1920×1080 browser run opened Files, ran a preset (hundreds of matches), sorted by size, opened the settings dialog
and switched to dark, then returned to Photos and filtered by name/date. 103 unit/contract + 15 integration
tests green; `ruff`/JS syntax clean. F-RAW-05 (in-app rich preview, P2) is **not** built and is listed as a
known gap; F-RAW-06 target display is API-only (P3).

### P-011 — Phase 8: hardening and bug bash  ✅
**Agent:** qa
```
Act as the qa agent. Task: Phase 8. Run ruff, mypy (best effort) and pytest (with and without the
integration env). Verify every acceptance criterion in project-docs/FEATURES.md marked P0/P1 literally and record
evidence (command output, screenshot paths) in a table. Test: token/Host/Origin rejection, password never
in logs, export refusing destinations inside the backup, path traversal attempts on /api/files, wrong
password retry, memory use while scrolling 5k assets and exporting 2k files, behaviour when the backup is
open in iTunes, when disk is full (simulate), when a payload file is missing. Run pip-audit. File each
defect as a numbered list with repro steps and severity; fix only test-blocking defects yourself.
Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE**. Wrote `project-docs/QA_REPORT.md`
with the gate results and the P0/P1 matrix. Gates: **106 unit/contract + 15 integration tests pass**, `ruff`
clean, `mypy backend --ignore-missing-imports` clean (one note), `pip-audit -r requirements.txt` reports
**no known vulnerabilities**, and every JS module passes `node --check`. Added hardening tests for disk-full
during export (job continues, error recorded, no `.part`), missing payload → placeholder, 2,000-file export
peak Python memory < 100 MB, and path-traversal/invalid-id rejection on `/api/files`. Measured the mock UI
at 1920×1080: **25–28 DOM tiles / 657–677 nodes / 5–6 MB JS heap** after scrolling to the bottom; thumbnails
100 cold 3.28 s / warm 0.10 s. Security matrix covers token, Host, Origin, `Sec-Fetch-Site`, CSP, password
logging, read-only backup, destination-inside-backup and ZIP guards. Eight non-blocking defects/gaps are
listed (QA-001…008), including F-RAW-05 (P2 preview) and the untested Firefox/iTunes-open scenarios; none
required a feature fix. `ruff`/tests re-run after the type-hygiene cleanups.

### P-012 — Phase 9: packaging and release  ✅
**Agent:** qa (with architect)
```
Act as the qa agent. Task: Phase 9. Follow SETUP.md from a clean Windows user profile (fresh venv) and
correct any inaccuracy in SETUP.md and README.md. Add an optional PyInstaller one-folder build script and
document it. Create LICENSE (MIT unless I say otherwise), a CHANGELOG.md, a GitHub Actions workflow that
runs ruff + unit tests (no integration), issue templates, and a release checklist. Remove any personal
data from docs/reference (blur/crop) or confirm it is git-ignored. Propose the v0.1.0 tag message.
Finish with the Standard report.
```
**Outcome:** 2026-10-28 · DeepSeek V4.1 Flash via opencode · **APPROVE for v0.1.0**. Added MIT
`LICENSE`, `CHANGELOG.md`, `project-docs/THIRD_PARTY.md`, GitHub Actions CI (Windows, Python 3.11 + 3.13, ruff +
unit tests + a frontend external-URL guard), bug/feature issue templates, a PR template, and
`project-docs/RELEASE_CHECKLIST.md`. Rewrote `README.md` for the shipped app (with sanitised mock screenshots) and
corrected `SETUP.md` (pinned requirements, mock mode, cache/settings, tests, PyInstaller, troubleshooting).
`scripts/build_exe.py` produced `dist/BackupLens/BackupLens.exe`; the exe was launched and served the UI +
listed the real backups (clean-profile/no-Python install not tested). A fresh venv installed from
`requirements-dev.txt` imports all packages and passes the 106 unit/contract tests. Privacy sweep: removed
the real UDID from tracked docs/tests/mock, regenerated the mock screenshots with a synthetic UDID, confirmed
`project-docs/local/` is git-ignored and no personal media/SQLite/`.env` is tracked. Proposed tag: `v0.1.0` —
"BackupLens v0.1.0: local photo browser and unlimited exporter for encrypted iOS backups". Not pushed.

### P-014 — Phase 10A: publish the repository safely  ✅
**Agent:** qa (release engineer), architect review
**Outcome (2026-11-10):** Reorganised the public tree into `project-docs/`, `docs/`, code and
`packaging/`; fixed every link/path (link checker 0 dangling); sanitised schema notes and the mock/test
data; moved raw notes, reference counts and the reference screenshot into the git-ignored
`project-docs/local/`. Privacy audit covered every tracked text file with `detect-secrets` 1.5.0 and a
custom guard. History was rewritten with `git-filter-repo` 2.47.0; a residual device identifier led to a
fresh single-commit history of the cleaned tree, then reflog expiration/GC. The safety bundle is outside
the repository. The private repository was created and pushed; a fresh shallow clone matched 136 tracked
files and passed both scanners. It was then made public (explicitly only
`tkrishnakanth/backuplens`); `gh repo view` shows PUBLIC/false, unauthenticated GitHub returns HTTP 200,
the unauthenticated API returns `private=false`, and the before/after repository snapshot diff contains
only the new repository. Issues, Discussions, vulnerability reporting, secret scanning + push
protection and Dependabot were enabled on this repository only. Full evidence:
`project-docs/PUBLISH_AUDIT.md`.

### P-015 — Phase 10B: release engineering (BLOCKED before CI/release)  🟨
**Agent:** qa / api
**Outcome (2026-11-10):** Implemented the Stage B application groundwork and local Windows packaging:
single version source (`backend/version.py` read by `pyproject.toml`), `--version`, `--port`,
`--no-browser`, `--data-dir`, `--smoke-test`, `--quit-after-idle`, per-OS data/cache paths,
single-instance state file, unauthenticated `/api/health`, protected `POST /api/app/quit`, and a
menu item. Added original icon artwork/generator, PyInstaller spec, Inno Setup per-user installer,
macOS/Linux packaging scripts, and tests. Locally the Windows PyInstaller build passed `--smoke-test`;
the Inno installer silently installed, the installed app passed `--smoke-test`, and silent uninstall
removed the program directory.

**STOP CONDITION HIT (GPLv2), before CI/release:** `pillow-heif` 1.8.1 binary wheels bundle
`x265` under GPLv2 (plus LGPLv3 libheif/libde265). The frozen app therefore contains a GPLv2
component and cannot be published as MIT-only binaries. All local `build/` and `dist/` output was
deleted; no CI run, release, rc tag or binary was uploaded. See `project-docs/RELEASE_BLOCKER.md` for
the evidence and options A–D. Stage B remains 🟨 pending the owner's licensing decision.

### P-016 — Phase 10B: GPL relicensing and release preparation  🟨
**Agent:** qa / api / architect
**Outcome (2026-11-10):** Verified from the bundled notices and the x265 4.3 source headers that x265 is
GPL-2.0-or-later (not GPL-2.0-only); libheif 1.23.6 and libde265 1.1.3 are LGPL-3.0 and the MinGW runtime
components are GPLv3-with-GCC-exception/MIT/BSD. All are GPL-3.0-compatible. Relicensed the project to
GPL-3.0-or-later in LICENSE, README, pyproject metadata, CONTRIBUTING and the installer licence page;
added ADR-010. Generated a full `THIRD_PARTY_NOTICES.txt` with component/version/licence/source tables,
the exact source tag URL and full licence texts. Kept one-folder packaging so LGPL libraries remain
separate replaceable DLLs/shared libraries. Added app packaging/launcher groundwork, icon assets,
PyInstaller spec, Windows installer, macOS/Linux scripts, release/CI workflows, community files and
INSTALL/SIGNING/RELEASING docs. Windows build/installer/smoke tests pass locally. Continuing with the
CI repair loop and a draft rc1 release; the release is not published.

### P-013+ — Optional modules (P2/P3)  ⬜
Run one prompt per module after v0.1.0: Messages (F-MSG-01/02), WhatsApp (F-WAP-01), Contacts
(F-CON-01), Call history (F-CAL-01), Notes (F-NOT-01), Calendar, Safari, Voice memos, Apps.
Template:
```
Act as the <agent> agent. Task: implement <feature IDs> from project-docs/FEATURES.md. First inspect the real
database schema for this iOS version and record it in project-docs/schema-notes.md, then implement viewer +
export with the same patterns as the photo module (list -> detail -> export job). Add tests and docs.
Finish with the Standard report.
```

## 3. Entry template for ad-hoc prompts

```
### P-0NN — <short title>
- **Date / time:**
- **Agent / persona:**
- **Model + tool:** (e.g. DeepSeek <model id> via opencode <version>)
- **Branch / commit:**
- **Prompt:**
  <exact prompt text, redacted of secrets>
- **Outcome:** (what was produced, test results, quality 1-5)
- **Problems / follow-ups:**
- **Decision:** (accepted / rework / abandoned) and why
```

## 4. Change requests (CR) and decisions

| ID | Date | From | Summary | Proposal | Architect decision |
|---|---|---|---|---|---|
| CR-001 | 2026-10-28 | photos | `project-docs/FEATURES.md` F-PHO-13 expects an "original + rendered edit" pair. Real backup has **no rendered full-size edit**; edited photos carry only `.AAE` adjustment sidecars (most adjusted assets adjusted assets). | Expose the `.AAE` as "adjustment data"; *Include edited versions* copies it when present; UI does not promise a rendered edit. | **Accepted** 2026-10-28. Wording must stay honest; no fake preview. |

## 5. Lessons learned (update as you go)

- _(e.g. which prompts needed rework, model quirks, token/cost notes, things to tell the agent next time)_
