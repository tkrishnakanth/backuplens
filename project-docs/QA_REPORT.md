# QA report — Phase 8 hardening

Date: 2026-10-28 · QA & Release Engineer · Windows 11, Python 3.13.1, real encrypted backup
(a real encrypted iOS backup)

This report records what was actually executed. It does not claim checks that were not run.

## 1. Quality gates

| Gate | Command | Result |
|---|---|---|
| Unit + contract tests | `.venv\Scripts\python.exe -m pytest -q` | **106 passed** |
| Integration tests (real backup) | `.venv\Scripts\python.exe -m pytest -q -m integration` | **15 passed** |
| Lint | `.venv\Scripts\ruff.exe check .` | **All checks passed** |
| Types (best effort) | `.venv\Scripts\python.exe -m mypy backend --ignore-missing-imports` | **No issues** (one note: `routes/jobs.py` has intentionally untyped inner helpers) |
| Dependency audit | `.venv\Scripts\python.exe -m pip_audit -r requirements.txt` | **No known vulnerabilities found** |
| JS syntax | `node --check` on every `frontend/js/**/*.js` copy | **0 failures** |

## 2. Security checks

| Check | Evidence | Result |
|---|---|---|
| Missing/wrong token → 401 | `test_api_without_token_is_rejected`, `test_api_with_wrong_token_is_rejected` | Pass |
| Bad `Host` → 403 | `test_bad_host_is_rejected` | Pass |
| Bad `Origin` on POST → 403 | `test_bad_origin_on_post_is_rejected` | Pass |
| `Sec-Fetch-Site: cross-site` → 403 | `test_sec_fetch_cross_site_is_rejected` | Pass |
| CSP + hardening headers | `test_security_headers_and_csp` | Pass |
| Password never in logs/stdout | Wrong and correct password captured in unit + integration tests | Pass |
| Password not retained by `Session` | `test_session_drops_password_reference` | Pass |
| Backup folder unchanged by reads/exports | Integration mtime/size comparison | Pass |
| Export destination inside backup refused | Unit + integration `bad_destination` | Pass |
| Path traversal in raw export | `safe_join` unit tests (`..`, absolute) | Pass |
| Path traversal in `/api/files` | `../../etc` → 400; invalid file id → 400 | Pass |
| ZIP guard | ≤500 items / 2 GB, store-only; unit + integration | Pass |
| No outbound requests from UI | Chrome Network: only `127.0.0.1`; mock uses `data:` SVGs | Pass (manual/CDP) |
| Read-only app (no replace/delete) | No write routes for the backup; raw export only writes to destination | Pass |

## 3. Performance and memory

| Measurement | Result |
|---|---|
| Index build (real, several thousand assets) | **under 1 s** after manifest unlock |
| 100 thumbnails, cold cache (Flask test client) | **3.28 s** (another run 5.14 s with a cold OS cache) |
| 100 thumbnails, warm cache | **0.10 s** (0.08 s in the second run) |
| Grid DOM at 1920×1080, several thousand assets | **25–28 tiles**, 9 date groups, **657–677 DOM nodes** |
| Scroll to bottom (376,094 px) | heap **5–6 MB**, tile/node counts unchanged |
| 2,000-file export plan/runner (synthetic, 1 KB files) | completed; Python peak allocation **< 100 MB** (asserted) |
| 20-file real export | byte-identical to `Session.read_file`; capture-date mtimes exact |

Memory was measured in Chrome via CDP `Performance.getMetrics`; export memory via `tracemalloc`.
The 2,000-file test uses synthetic payloads, so it verifies engine bookkeeping rather than disk throughput.

## 4. P0/P1 acceptance matrix

Every row below was executed; details and exact test names live in `project-docs/FEATURES.md` §I.

| Area | IDs | Status | Notes |
|---|---|---|---|
| Backup discovery/session | F-BKP-01, 02, 03, 04, 05, 07 | **Pass** | Wrong password retry is stateless; temp manifest removed on close |
| Library categories | F-PHO-01, 02, 03 | **Pass** | All 13 counts and both albums match the reference exactly |
| Grid/selection/browser | F-PHO-04, 05, 10, 11, 12 | **Pass** | several thousand assets, ≤300 DOM tiles, instant type filter, calendar jump |
| Preview/media | F-PHO-06, 07, 08, 09 | **Pass** | Thumbs, previews, Range originals, Live MOV; HEVC codec hint |
| Original/edited metadata | F-PHO-13 | **Pass** | `.AAE` sidecar exposed (CR-001); no rendered edit exists |
| Filename/date search | F-PHO-14 (P2) | **Pass** | Debounced search + date range combined with scope |
| Export | F-EXP-01…13 | **Pass** | 20-file byte compare, layouts, conflicts, Live/edited, HEIC, ZIP, report, cancel, no limits |
| Raw explorer | F-RAW-01…04 | **Pass** | Domain tree, LIKE search with escape, sort, export matching |
| Security | F-SEC-01, 02, 03 | **Pass** | See §2 |
| Platform | F-PLT-01, 02, 03, 04 | **Pass** | One-command launcher; settings persisted; clear cache |
| Accessibility | F-ACC-01 | **Partial** | ARIA roles/labels, focus rings, keyboard paths implemented; no screen-reader audit |
| Tests/docs | F-DOC-01, F-TST-01 | **Pass** | 106 unit + 15 integration; docs updated each phase |

**Not P0/P1 / intentionally not built:** F-BKP-06 (device info panel, P2), F-RAW-05 (in-app rich
file preview, P2), F-RAW-06 (symlink target display, P3), F-PLT-05 (PyInstaller, P2/Phase 9), and all
P2/P3 data modules (Messages/chat apps/Contacts/Calls/Notes/Calendar/Safari/Voice/Apps).

## 5. Robustness scenarios

| Scenario | Method | Result |
|---|---|---|
| Wrong password, retry | Integration: wrong attempt then correct attempt | Pass |
| Missing payload file | Core typed `PayloadMissing`; media placeholder; export records per-file error | Pass |
| Disk full during export | Simulated `OSError(errno.ENOSPC)` in `extract_file` | Job continues, error recorded, no `.part` left, report says Failed |
| Export cancelled mid-run | Cancel 0.2 s into 300 files | State `cancelled`, no `.part`, report `Cancelled: yes` |
| Destination inside backup | API export and raw export | 400 `bad_destination` |
| Corrupt/unreadable image | Media unit test | Valid placeholder JPEG, no HTTP error |
| Backup open in iTunes / exclusive lock | Not reproducible in this environment (no iTunes process). Core maps unreadable Manifest/payload errors to typed errors; untested in the wild. |
| OS-level disk-full | Not filled a real volume; only simulated as above. |

## 6. Defects and known gaps

No blocking defects were found. The following are recorded and none required a code change:

1. **QA-001 · Low · cache clear can leave a file that is still open.** Windows refuses deletion of a
   cache file while a video stream holds it. Normal `Clear cache` removes everything; a file being
   streamed may survive until the response closes. Repro: start a large video, click Clear cache.
2. **QA-002 · Low · `export-report.txt` is overwritten** by each export into the same destination.
   By design (documented), not a data-loss path for media files.
3. **QA-003 · Medium · F-RAW-05 rich raw preview is absent.** Files can be downloaded but not
   previewed in-app (P2 feature, not a v0.1 regression).
4. **QA-004 · Low · symlink target is not shown** in the Files table (API returns it; P3).
5. **QA-005 · Info · Firefox** was not smoke-tested; Edge shares Chromium with the verified Chrome
   run. UI_SPEC checklist item remains open until a manual pass.
6. **QA-006 · Info · screen-reader audit not run** (F-ACC-01 partial).
7. **QA-007 · Info · LIKE search with size/date sort scans the whole manifest** and can take seconds
   on very broad patterns; path/domain sorts use SQL pagination.
8. **QA-008 · Info · ZIP is assembled store-only on disk** and then streamed to the client; bounded to
   500 items / 2 GB. This avoids buffering in RAM but the request waits for assembly.

## 7. Sign-off

Quality gates pass. P0 and P1 acceptance criteria are verified with the two honest exceptions above
(screen-reader audit and non-Chromium smoke tests). No test-blocking bug was found, so no feature code
was changed in this phase; only type/lint hygiene and hardening tests were added.

**Verdict: APPROVE for Phase 9 (packaging and release).**
