# PUBLISH_AUDIT — Stage A (public-release privacy audit)

Date: 2026-11-10. Owner: qa/release engineer. Architect review required before publishing.
This report names categories and file paths only; it never repeats a secret, device identifier or
library value.

## 1. Tools and scope

| Item | Value |
|---|---|
| Secret scanner | `detect-secrets` 1.5.0 (PyPI) |
| History rewrite tool | `git-filter-repo` 2.47.0 |
| Custom guard | `scripts/privacy_guard.py` (forbidden files, device-ID-like strings, emails, local user paths, token-like strings) |
| Git | 2.48.1.windows.1 |
| Tracked files scanned | **134** (every tracked text file; binary/image rules below) |
| Commits in final history | 1 squashed commit + Stage A/B follow-ups, all no-reply identity |
| Scope | working tree and every revision reachable before the rewrite |
| Safety copy before rewrite | `C:\Workspace\backuplens-original.bundle` (outside the repository; never pushed) |

## 2. Findings and actions (by category and path)

### 2.1 Secrets

- No backup password, `.env`, API token, private key or provider credential was tracked.
- `detect-secrets` reported five **false positives** (generic `password` keyword in test payloads and
  one prose line about security workflows):
  `tests/api_fixtures.py`, `tests/test_api_session.py`, `tests/test_backup_session.py`,
  `tests/test_launcher.py`, `project-docs/RELEASE.md`. Each is a placeholder/test value, reviewed
  manually; no value was copied into this report.
- Custom guard: **passed**.

### 2.2 Device identifiers

- `project-docs/ARCHITECTURE.md`, `project-docs/SETUP.md`, the mock API, API test fixtures and the
  discovery tests used a real iOS UDID/serial-like value copied during development.
- Action: replaced with obvious demo identifiers (`DEMO-UDID-…`, `TEST-SERIAL`, `TEST-IMEI`);
  the real values are gone from the tree and from history.
- No valid `8-16` UDID pattern remains in tracked files (guard passes).

### 2.3 Backup-derived content

- The reference screenshot existed locally only and was **never tracked**; it has been moved to
  `project-docs/local/`, which is git-ignored.
- No `Manifest.db`/`Manifest.plist`/`Info.plist`, `Photos.sqlite`, `-wal`/`-shm`, exported photos,
  videos, thumbnails, SQLite files, ZIPs or logs are tracked.
- `build/`, `dist/`, logs and caches were removed before the audit and are ignored.

### 2.4 Library details (places, albums, dates, counts, sample rows)

- `project-docs/schema-notes.md` contained sample rows/paths, real place/album names and exact
  reference counts. It was replaced with a **structure-only** version. The raw copy is
  `project-docs/local/schema-notes.raw.md` (ignored).
- Exact reference counts were moved to `project-docs/local/reference-counts.json` (ignored). The
  integration test reads it only when `BACKUPLENS_REFERENCE_COUNTS` is set; otherwise it checks internal
  consistency and skips the exact comparison.
- `project-docs/PROMPT_LOG.md`, `project-docs/QA_REPORT.md`, `project-docs/FEATURES.md`,
  `project-docs/ARCHITECTURE.md`, `README.md`, `CHANGELOG.md`, `project-docs/UI_SPEC.md` and the mock
  library carried counts/device metadata/place or album names; all were generalised.
- Tests and fixtures were changed to synthetic paths/names (`TESTAPPLE`, `TEST_…`, `Place A/B`,
  `Album A/B`, a neutral timezone offset).

### 2.5 Personal paths and accounts

- Commit metadata used a personal email on every old commit. History was rewritten and the repository
  identity is now the GitHub no-reply address
  `194752155+tkrishnakanth@users.noreply.github.com`.
- No real local user path remains; examples use `C:\Users\YOU`, `C:\Users\Public` or placeholders.

### 2.6 Images and binaries

- Tracked images: four synthetic mock screenshots under `docs/screenshots/` plus `frontend/favicon.svg`.
  They are project-created assets and were regenerated after the mock data was anonymised.
- The reference screenshot (which contains personal photos and a document) is not tracked and is not
  in history.

## 3. History decision

1. A safety bundle was created outside the repository before any rewrite.
2. `git filter-repo` 2.47.0 was run with a mailmap and text replacements. It rewrote the 21 commits.
3. Re-audit still found a residual real device identifier in historical blobs (a replacement line was
   not applied), so the safer path was chosen:
   **a fresh single-commit history of the cleaned tree** (`feat: BackupLens v0.1.0 public source tree`).
4. Old branches and all old phase tags were deleted; reflogs expired and `git gc --prune=now` run.
   Only `main` and the new history will be pushed.
5. All commit identities are the no-reply address above.

## 4. Clean confirmations (local)

| Check | Result |
|---|---|
| `python scripts/privacy_guard.py` | **passed** for 134 tracked files |
| `detect-secrets` on every tracked text file | five reviewed false positives (paths in §2.1), no real secret |
| UDID-like pattern scan | none |
| Personal-email scan | only `you@example.com` and no-reply placeholders |
| Tracked forbidden file types | none (images limited to project mock assets) |
| `project-docs/local/` tracked | no |
| `.env` tracked | no |
| `git log --format='%an <%ae>'` | no-reply identity only |
| Full test suite after sanitising | 106 unit/contract + 15 integration passed |
| Ruff | clean |

## 5. Remote verification (Stage A step 5)

- Private repo created and `main` pushed: **yes**
- Fresh shallow clone into a temporary folder: **136 tracked files**, equal to the local `git ls-files`
  list via `gh api repos/.../git/trees/main?recursive=1` (no extra or missing blobs).
- Fresh-clone privacy guard: **passed** for 136 files.
- Fresh-clone `detect-secrets`: the same five reviewed false positives listed in §2.1; no real secret.
- No `project-docs/local`, reference screenshot, `.env`, SQLite, backup, personal media or logs in the
  clone; commit identity is the no-reply address only.

### Public visibility evidence

- `gh repo view tkrishnakanth/backuplens --json visibility,isPrivate,url` →
  `{"isPrivate":false,"url":"https://github.com/tkrishnakanth/backuplens","visibility":"PUBLIC"}`
- Unauthenticated `curl.exe -s -o NUL -w "%{http_code}" https://github.com/tkrishnakanth/backuplens` →
  **200**
- Unauthenticated `https://api.github.com/repos/tkrishnakanth/backuplens` →
  `private=false`, `visibility=public`
- Second `gh repo list --limit 1000 --json nameWithOwner,visibility` snapshot diff against the
  pre-work snapshot: **only `tkrishnakanth/backuplens|PUBLIC` was added**; no other repository changed
  visibility.

Repository features enabled on this repository only: Issues, Discussions, vulnerability alerts,
private vulnerability reporting, secret scanning, push protection and Dependabot security updates.
Branch protection was not set, so the automated PR flow is not blocked.

## 6. Architect review — Stage A

- [x] Non-code files moved; link check 0 dangling links; tests pass.
- [x] Sanitised schema notes; raw notes and reference counts only in ignored local files.
- [x] Device IDs, personal email and library names removed; history is clean.
- [x] Reference screenshot never tracked; no backup-derived files tracked.
- [x] Repository is public and verified three ways; other repositories unchanged.

**Verdict: APPROVE for Stage B.**
