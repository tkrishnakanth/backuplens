# SETUP

Everything you need to go from "a folder of docs" to "app running and pushed to GitHub", on Windows 10/11.
Commands are for **Command Prompt or PowerShell** unless noted.

> opencode, GitHub CLI and DeepSeek change their commands and menus over time. Where this file
> describes them, treat it as a guide and confirm against their current docs (opencode.ai/docs,
> cli.github.com, api-docs.deepseek.com).

---

## 1. What you need

| Tool | Why | Check |
|---|---|---|
| Windows 10/11 | target platform | |
| **Python 3.11+** (python.org, tick *Add to PATH*) | run the app and tests | `python --version` |
| **Git for Windows** | version control | `git --version` |
| **GitHub account** (+ optional GitHub CLI `gh`) | host the repo | `gh --version` |
| **opencode** | the AI coding agent harness | `opencode --version` |
| **DeepSeek API key** (or your subscription's provider details) | the model behind opencode | |
| A modern browser (Chrome/Edge/Firefox) | use the app | |
| **Your iPhone backup** (encrypted) + its password | test data | see §6 |
| *Optional:* `ffmpeg` on PATH | video thumbnails fallback | `ffmpeg -version` |
| *Optional:* Node.js | only if you install opencode through npm | `node --version` |

The app itself does **not** need Node.js.

## 2. Install the tools

1. **Python:** download from python.org → installer → tick *Add python.exe to PATH* → Install.
2. **Git:** download from git-scm.com, accept defaults, then set your identity:
   ```
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
3. **GitHub CLI (optional but handy):** `winget install GitHub.cli`, then `gh auth login`.
4. **opencode** (pick one that works for you; see opencode.ai/docs for the current list):
   - with Node.js installed: `npm install -g opencode-ai`
   - or Scoop: `scoop install opencode`
   - or Chocolatey: `choco install opencode`
   - or inside **WSL** (Windows Subsystem for Linux) using its Linux install script
   Verify with `opencode --version`.

## 3. Create the project folder

```
mkdir C:\dev\backuplens
cd C:\dev\backuplens
git init -b main
```

Copy the documentation set into it so you have:

```
backuplens\
  README.md  AGENTS.md  LICENSE  CHANGELOG.md  requirements*.txt
  project-docs\ARCHITECTURE.md  FEATURES.md  UI_SPEC.md  SETUP.md  PROMPT_LOG.md
  project-docs\local\        <- private/raw material (git-ignored; see §9)
  docs\                      <- public user guides and project screenshots
```

Create the empty folders the agents will fill (git ignores empty folders, so add `.gitkeep` files if you
want them committed): `backend`, `frontend`, `tests`, `scripts`.

Create and activate a virtual environment:

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```
(`requirements.txt` is the pinned runtime set; `requirements-dev.txt` adds pytest and ruff. The app does
not need Node.js. Python 3.11+ is supported; 3.13.1 was used for the verified build.)

## 4. Configure opencode with DeepSeek

1. Get an API key from the DeepSeek platform (platform.deepseek.com → API keys). If your "subscription"
   is a chat plan rather than API credit, check whether it includes API access; opencode needs an API
   key or a supported provider login.
2. In the project folder run `opencode`, then either:
   - run `opencode auth login`, choose **DeepSeek** from the provider list and paste the key, **or**
   - set an environment variable for the session:
     ```
     setx DEEPSEEK_API_KEY "your-key-here"
     ```
     (open a new terminal afterwards).
3. Inside opencode use its model picker (commonly `/models`) to select a DeepSeek chat or reasoning model.
   Use the reasoning model for **architect / photos / core** work and the standard chat model for routine
   coding if you want to save cost.
4. opencode reads `AGENTS.md` from the project root automatically; you do **not** need to run `/init`
   (it would overwrite or duplicate your rules). If it offers to create one, decline.
5. Optional: create real agent files as described in `AGENTS.md` §6.

## 5. First run of the AI workflow

> **Status:** Phases 0–9 have been executed in this repository (see `PROMPT_LOG.md` and the status board
> in `AGENTS.md`). The workflow below is retained for future phases and optional P2/P3 modules.

1. Open a terminal in the project folder, activate the venv, run `opencode`.
2. Paste the **Context block** (`PROMPT_LOG.md` §1), then **P-001 (Orientation)**. Answer its questions.
3. Commit the docs as the first commit:
   ```
   git add .
   git commit -m "docs: initial architecture, agents, prompt log, setup"
   ```
4. Continue with **P-002 (Phase 0 spike)**. This is the most important step: it proves your backup can be
   unlocked and records the real database layout.
5. Work through P-003 → P-012 in order. After each prompt:
   - run the tests the agent reports (`pytest -q`) and look at the result yourself,
   - fill in the Outcome in `PROMPT_LOG.md`,
   - `git add -A && git commit -m "<conventional message>"`,
   - at the end of a phase: merge the branch, tag it (`git tag phase-N-done`).
6. Start a **fresh opencode session per phase**, beginning with the Context block.

Tips for getting good results from DeepSeek:
- One task per prompt; paste the prompt verbatim.
- If the output drifts from the docs, reply: "Re-read AGENTS.md section 1 and ARCHITECTURE.md section X,
  then redo only <thing>."
- Ask it to show evidence (command output) rather than claiming success.
- Keep the Architect agent in plan/read-only mode to review work before you merge.

## 6. Locate your backup and set test variables

Default Windows locations (look for a folder named like `DEMO-UDID-00000001`):

- Apple Devices app / iTunes from Microsoft Store: `%USERPROFILE%\Apple\MobileSync\Backup\`
- Classic iTunes installer: `%APPDATA%\Apple Computer\MobileSync\Backup\`

Rules:
- **Work on a copy** during development if you want extra safety (the app is read-only, but copying a
  backup makes experiments risk-free). A backup can be many GB; check free disk space.
- Create a file named `.env` in the project root (it is git-ignored, see §7):
  ```
  BACKUP_PATH=C:\Users\YOU\Apple\MobileSync\Backup\DEMO-UDID-00000001
  BACKUP_PASSWORD=your-backup-password
  ```
- Never paste these values into prompts, `PROMPT_LOG.md`, issues or commits.
- If iTunes/Apple Devices is open and syncing, close it before testing.

## 7. `.gitignore` (create this file first, before any commit that could include data)

```
# Python
.venv/
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
build/
dist/
*.spec.bak

# Secrets and local config
.env
.env.*
config.local.json

# Runtime data - NEVER commit
logs/
cache/
thumbs/
exports/
*.log
*.sqlite
*.sqlite-wal
*.sqlite-shm
Manifest.db
Photos.sqlite*

# Personal media and backups
backup/
backups/
*.heic
*.HEIC
*.jpg
*.JPG
*.jpeg
*.png
*.mov
*.MOV
*.mp4
!frontend/**/*.png
!frontend/**/*.jpg
!docs/screenshots/*.png

# Reference screenshot with personal data (keep local, or sanitise then move to docs/screenshots/)
project-docs/local/

# OS / editor
.DS_Store
Thumbs.db
.idea/
.vscode/
node_modules/
```

## 8. Push to GitHub

Option A — GitHub CLI:
```
gh repo create backuplens --private --source . --remote origin --push
```
(Make it public later, after you have checked the history for personal data.)

Option B — manual:
1. On github.com create an empty repository named `backuplens` (no README/license/gitignore).
2. Then:
   ```
   git remote add origin https://github.com/<your-user>/backuplens.git
   git branch -M main
   git push -u origin main
   ```
3. Branch workflow: `git checkout -b phase-3-library-index` → commits → push → open a Pull Request →
   review with the architect agent → merge → `git tag phase-3-done && git push --tags`.

Before making the repo public, run through this checklist:
- [ ] `git log --all -p | findstr /i "password"` shows nothing sensitive
- [ ] no photos, thumbnails, sqlite files, logs, `.env` in history (`git ls-files`)
- [ ] reference screenshot sanitised or ignored (see §9)
- [ ] LICENSE present; dependency licences checked
- [ ] README has no personal paths/UDIDs

## 9. Privacy note about the reference screenshot

Your screenshot shows a device **Unique ID**, personal photos, and a photo of a document containing a
name, phone number and email. Do **not** commit it to a public repository. Either:
- keep it in `project-docs/local/` (git-ignored by §7) and give the UI agent its path locally, **or**
- crop to the sidebar/header and blur the photos, save into `docs/screenshots/`, and commit that version.

Agents running through opencode send file contents to the model provider you configured, so only place
the image in the project if you are comfortable with that.

## 10. Run the application (after Phase 2+)

```
cd C:\dev\backuplens
.venv\Scripts\activate
python backend\app.py
```
The console prints a URL like `http://127.0.0.1:<port>/?t=<token>` and opens your browser.
1. Pick your backup card (encrypted ones show a lock).
2. Enter the password; wait for "Reading photo library…".
3. Browse by category/album/moment, select photos, use **Current Folder** or the selection tool to
   export to a folder on disk.
Stop with `Ctrl+C` in the console. Temp decrypted data is deleted on exit and the media cache is cleared
unless `CACHE_PERSIST` is enabled. To try the UI without a backup, append `?mock=1` to the printed URL
(or open `http://127.0.0.1:<port>/?mock=1`); the demo has several thousand synthetic assets and self-contained SVG
thumbnails, with no network access.

## 11. Tests and quality checks

```
pytest -q                          # unit + contract tests (integration tests deselected)
pytest -q -m integration           # needs BACKUP_PATH and BACKUP_PASSWORD in .env / environment
ruff check .
python -m mypy backend --ignore-missing-imports   # optional, best effort
python -m pip_audit -r requirements.txt          # optional security audit
```
Integration tests read your real backup (read-only) and are skipped when the variables are missing.
Current verified result: **106 unit/contract + 15 integration tests pass**. See `project-docs/QA_REPORT.md`.

## 12. Optional: build a standalone folder (Phase 9)

```
pip install pyinstaller
python scripts\build_exe.py
dist\BackupLens\BackupLens.exe
```

The script bundles `frontend/`, pillow-heif and the backend. Settings/cache remain in
`%LOCALAPPDATA%\BackupLens`; logs are written next to the exe. The frozen entry point resolves the
bundled frontend via `sys._MEIPASS`. The build is optional and is **not** part of the release gates
unless you run the checklist in `project-docs/RELEASE_CHECKLIST.md`. Do not commit `build/`, `dist/` or `*.spec`.

## 13. Troubleshooting

| Symptom | Likely cause | What to do |
|---|---|---|
| "Wrong password" but you are sure | typo, keyboard layout, or the password differs from your Apple ID password | The backup password is the one you set in iTunes/Finder; retry carefully; try the Phase 0 script to isolate |
| Unlock takes a long time | PBKDF2 iterations are intentionally slow | Wait; progress is shown |
| `UnsupportedVersion` / crash on unlock | library does not yet support your iOS version | Update `iphone_backup_decrypt`; check its issues; escalate in PROMPT_LOG as a CR |
| No backups listed | non-default location | Use "Add backup folder…" and pick the `0000…` folder itself |
| Photos count smaller than expected | photos only in iCloud, or filtered category rules | See `project-docs/schema-notes.md` |
| HEIC thumbnails are blank | `pillow-heif` not installed/loaded | `pip install pillow-heif`; check the agent registered the opener |
| Video will not play in browser | HEVC/MOV not supported by your browser | Use Edge or Safari-class codecs, or export and play locally |
| Port in use | another process | App picks a free port automatically; check firewall prompts (allow localhost only) |
| Export fails with "access denied" | destination protected or inside backup | Choose a normal folder such as `D:\Exports\Photos` |
| Settings do not persist | config file not writable | Check `%LOCALAPPDATA%\BackupLens\config.json` and folder permissions |
| Cache grows too large | limit increased or old cache retained | Settings → lower the cache limit; use Clear cache |
| Demo mode shows no raw files | `?mock=1` has no Manifest | Open a real backup for the Files view |
| Built exe shows "frontend missing" | PyInstaller did not bundle frontend/ | Re-run `python scripts\build_exe.py`; check `--add-data` output |
| opencode cannot see the API key | env var set in another terminal | Open a new terminal after `setx`, or use `opencode auth login` |
| Agent edits files outside its ownership | persona drift | Remind it of AGENTS.md §3 and revert with `git checkout -- <path>` |

## 14. Updating the docs

Whenever behaviour changes: update `README.md`, `ARCHITECTURE.md` (via an ADR row), `project-docs/FEATURES.md`
status, and append to `PROMPT_LOG.md`. The QA agent verifies this at each phase exit.
