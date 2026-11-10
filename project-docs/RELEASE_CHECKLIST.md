# Release checklist

Use this for `v0.1.0` and later releases.

## 1. Pre-flight

- [ ] `main` is clean and all phase tags are present.
- [ ] `git status` has no untracked personal data.
- [ ] `git ls-files | findstr /i "env sqlite HEIC MOV JPG PNG"` shows only mock screenshots/frontend assets.
- [ ] `project-docs/local/` is still git-ignored (contains the commercial-app reference screenshot).
- [ ] No backup path, UDID, password or photo is in the docs, tests or screenshots.

## 2. Quality gates

```powershell
.venv\Scripts\ruff.exe check .
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m pytest -q -m integration   # needs .env
.venv\Scripts\python.exe -m mypy backend --ignore-missing-imports
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

- [ ] All gates green (or deviations recorded in `project-docs/QA_REPORT.md`).
- [ ] Integration counts still match the reference numbers.

## 3. Fresh-machine / fresh-venv check

```powershell
python -m venv $env:TEMP\bl-release
$env:TEMP\bl-release\Scripts\python.exe -m pip install --upgrade pip
$env:TEMP\bl-release\Scripts\python.exe -m pip install -r requirements.txt
$env:TEMP\bl-release\Scripts\python.exe backend\app.py --port 5188 --no-browser
```

- [ ] Home page loads, backups are listed, password dialog works, thumbnails and export work.
- [ ] `?mock=1` demo works without a backup.

## 4. Optional PyInstaller build

```powershell
.venv\Scripts\python.exe -m pip install pyinstaller
.venv\Scripts\python.exe scripts\build_exe.py
dist\BackupLens\BackupLens.exe
```

- [ ] `dist\BackupLens\BackupLens.exe` starts and serves the UI.
- [ ] HEIC thumbnails work in the built version (pillow-heif bundled).
- [ ] The build folder is not committed.

## 5. Documentation

- [ ] `README.md` quick start matches the real commands.
- [ ] `SETUP.md` has no stale phase notes.
- [ ] `CHANGELOG.md` has the release section and date.
- [ ] `project-docs/FEATURES.md` statuses are truthful.
- [ ] `project-docs/QA_REPORT.md` lists known gaps.
- [ ] `PROMPT_LOG.md` has this phase's outcome.

## 6. Tag and draft release (automated)

`.github/workflows/release.yml` builds Windows, macOS arm64/Intel and Linux artifacts and creates a
**draft pre-release**. It never publishes automatically.

```powershell
git tag -a v0.1.0-rc1 -m "BackupLens v0.1.0-rc1"
git push origin v0.1.0-rc1
```

- [ ] Wait for the Release workflow on the tag; all four build jobs and the draft job must be green.
- [ ] `gh release download v0.1.0-rc1`, verify every hash in `SHA256SUMS.txt`, and smoke-test the Windows
      installer (silent install → `--smoke-test` → silent uninstall).
- [ ] Confirm Windows setup/portable, both macOS DMG/ZIP pairs and all three Linux artifacts are attached,
      and that `LICENSE` + `THIRD_PARTY_NOTICES.txt` are included.
- [ ] A human reviews the draft and clicks **Publish release**. Only then create the final `v0.1.0` tag.
- [ ] Never attach a backup, photo, `.env`, SQLite file or log; never replace published assets silently.

> Suggested draft message: **v0.1.0-rc1 — first release.** Browse and export photos/videos from encrypted
> iOS backups entirely locally: virtualised grid, Range-streamed originals, unlimited folder export, raw
> Manifest explorer. Read-only by design; no telemetry, no cloud. 110 unit/contract +
> 15 integration tests. GPL-3.0-or-later with full third-party notices and source links.
