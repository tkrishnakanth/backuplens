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

## 6. Tag and publish (human)

```powershell
git tag -a v0.1.0 -m "BackupLens v0.1.0: local photo browser and unlimited exporter for encrypted iOS backups"
git push origin main
git push origin v0.1.0
```

Suggested tag message:

> **v0.1.0 — first release.** Browse and export photos/videos from encrypted iOS backups on Windows,
> entirely locally. Sidebar parity with the local reference library, virtualised several-thousand-photo grid,
> Range-streamed videos/Live Photos, unlimited folder export and a raw Manifest explorer. 106 unit +
> 15 integration tests against a real iPhone backup. Read-only by design; no telemetry, no cloud.

- [ ] Create the GitHub release from the tag, attach the optional `dist\BackupLens` ZIP (no personal data).
- [ ] Keep the repository private until the history/privacy sweep is confirmed.
