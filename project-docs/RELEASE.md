# RELEASE — cross-platform installers, open-source release pipeline

Owner: **qa** agent acting as **release engineer** (Phase 10). Architect reviews. This file is the
specification; `ONE_SHOT_RELEASE_PROMPT.md` (same folder) is the prompt that executes it. Note: Stage A
(§0) moves both files into `project-docs/`; after that, read them from there.

Goal: anyone can download an **installable file for Windows, macOS or Linux**, run BackupLens
without installing Python, and trust where it came from. The project is open source from the first
public release.

Phase 10 has two parts: **Stage A (§0)**: reorganise the repo, audit for personal data, push to GitHub and make
this one repo public; then **Stage B (§1-§12)**: packaging, CI, installers, community files, release candidate.

---

## 0. Stage A — publish the repository safely (runs BEFORE any packaging work)

Nothing in Phase 10 starts until Stage A is finished and verified. Order: **reorganise → privacy audit
(files and git history) → public-ready minimum files → create the GitHub repo → push → verify → make this
one repo public → verify again**.

### 0.1 Reorganise: move non-code files out of the root

Goal: the repository root and `docs/` look like a normal open-source project; everything that only
documents *how the project was built with AI agents* goes into one folder.

Target layout:

```
<repo>/
├─ README.md  LICENSE  CHANGELOG.md  SECURITY.md  CONTRIBUTING.md  CODE_OF_CONDUCT.md   (stay in root: GitHub shows them)
├─ AGENTS.md                      (stays in root: opencode reads it from the root; see note below)
├─ requirements.txt  .gitignore  pyproject.toml (if any)
├─ backend/  frontend/  tests/  scripts/  packaging/  .github/            (code, tooling, CI)
├─ docs/                          (public, user-facing: INSTALL.md, SIGNING.md, RELEASING.md)
└─ project-docs/                  (NEW: build-process material)
   ├─ ARCHITECTURE.md  FEATURES.md  UI_SPEC.md  SETUP.md  RELEASE.md  PROMPT_LOG.md
   ├─ ONE_SHOT_RELEASE_PROMPT.md  PUBLISH_AUDIT.md  schema-notes.md (sanitised)
   └─ local/                      (git-ignored: raw schema notes, reference screenshot, private counts, backups of notes)
```

Rules:
1. Move with `git mv` so history follows. Move **every** non-code file that is not in the "stay in root" list:
   the design/spec/setup/prompt/release docs, the reference screenshot (it goes to `project-docs/local/`,
   never to a tracked path), spike outputs, scratch notes, exports of any kind.
2. **Exceptions that must stay put:** `README.md`, `LICENSE`, `CHANGELOG.md`, `SECURITY.md`,
   `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `.gitignore`, `requirements.txt`, config files tools need in the
   root, `.github/`, and `AGENTS.md` (opencode only auto-loads it from the project root; the agent must say
   so in its report so the owner can decide to relocate it later).
3. After moving, **fix every cross-reference**: links and paths inside all Markdown files, the reading
   order in `AGENTS.md` §1, the prompts in `PROMPT_LOG.md`, `.gitignore` entries (e.g. `project-docs/local/` →
   `project-docs/local/`), and any code, test or script that refers to a moved file. Run a link checker
   (a simple script is enough) and the full test suite. Leave **no dangling reference**.
4. `README.md` gets a short "Project documentation" section linking into `project-docs/`.
5. Public user-facing docs written later in Phase 10 (`INSTALL.md`, `SIGNING.md`, `RELEASING.md`) go in
   `docs/`, not in `project-docs/`.

### 0.2 Privacy audit: find and exclude critical or personal data

The repo will be public forever (history included), so audit **both the working tree and the full git
history**. Use `git ls-files` plus a scan of **every** tracked text file (do not sample), and
`git log --all` for history. Combine tools and manual review: `gitleaks` or `detect-secrets` if
installable (check the licence/source, pin the version), plus the custom patterns below, plus reading the
files that are most likely to hold personal data (`PROMPT_LOG.md`, `SETUP.md`, `schema-notes.md`, tests,
fixtures, scripts, mock data, `.env*`, any `*.json`/`*.yml`/`opencode*` config).

**What counts as critical or personal (remove, replace with a placeholder, or move to an ignored file):**

| Category | Examples and detection hints |
|---|---|
| Secrets | the backup password in any form; `.env` files; API keys/tokens (`sk-…`, `ghp_…`, `gho_…`, `github_pat_…`, `AKIA…`, `xox[bap]-…`); private keys (`-----BEGIN … PRIVATE KEY-----`); `password`/`passwd`/`secret`/`token`/`api_key` assignments with a value; provider config files that hold keys |
| Device identifiers | iOS device IDs / UDIDs (pattern `[0-9A-Fa-f]{8}-[0-9A-Fa-f]{16}` or 40-hex), serial numbers, IMEI/MEID, ICCID, MAC addresses, device name, Apple ID / iCloud account names, phone numbers |
| Backup-derived content | `Manifest.db`, `Manifest.plist`, `Info.plist`, `Status.plist`, any `*.sqlite`/`*.db`, `-wal`/`-shm`, extracted or hashed payload files, thumbnails, photos/videos (`.heic .jpg .jpeg .png .mov .mp4 .dng`), exports, ZIPs of such |
| Library details that identify a person | real photo filenames and capture dates, GPS coordinates, real **place names and album names** from the owner's library (anything copied from the reference screenshot or from spike output), message/contact/note text, sample rows from `Photos.sqlite` |
| Personal paths and accounts | `C:\Users\<real name>\…`, `/Users/<name>/…`, `/home/<name>/…`, real hostnames, personal email addresses, real names in comments/`LICENSE`/`SECURITY.md` unless the owner wants them |
| Images and binaries | any tracked image or binary that is not an app asset created by this project (the icon source, frontend assets, the synthetic `tests/assets` HEIC). **The agent may not be able to view images; therefore the rule is "exclude by default" — never inspect-and-keep.** The reference screenshot is excluded without exception: it contains personal photos, a device ID and a photographed document with a name, phone number and email |
| Logs and caches | `*.log`, `logs/`, `cache/`, `thumbs/`, `exports/`, crash dumps, PyInstaller `build/` and `dist/` output |

**Actions by tier**
- **Tier 1 (secrets, device IDs, personal identifiers, backup content, images, logs):** remove from the
  tracked tree, add to `.gitignore`, and replace in prose with obvious placeholders (`<YOUR-BACKUP-ID>`,
  `C:\Users\YOU\…`, `00008XXX-XXXXXXXXXXXXXXXX`). The known example is the real device ID used as an example
  in `SETUP.md`; there may be more.
- **Tier 2 (library statistics, real album/place names, sample rows):** generalise or move to
  `project-docs/local/` (ignored). `schema-notes.md` keeps table/column names, value *types* and rule
  descriptions, but **no sample rows and no real names/dates/coordinates**; the raw version is kept only under
  `project-docs/local/`. Reference counts used for acceptance checks are moved to an ignored local file and
  read by the integration tests through an optional environment variable (tests skip cleanly when absent).
- **Tier 3 (borderline):** if unsure, treat as Tier 2. Prefer removal over keeping.

**Git history audit**
1. List every file that was ever added (`git log --all --diff-filter=A --name-only`) and every distinct
   author/committer name and email (`git log --all --format='%an <%ae> | %cn <%ce>' | sort -u`).
2. Scan all revisions with the same patterns (e.g. `git grep -I -n -E <pattern> $(git rev-list --all)`) and run
   the secret scanner in history mode.
3. **Commit author emails are public once pushed.** If any author/committer email is a personal address, rewrite
   to the owner's GitHub no-reply address `<id>+<login>@users.noreply.github.com` (get `id` and `login` from
   `gh api user`) and set the repo-local `git config user.name/user.email` to it for all future commits.
4. If **anything** from the table above exists anywhere in history, rewrite history **before the first push**:
   - first make a full safety copy **outside the project folder**: `git bundle create ../<repo>-original.bundle --all`
     (never pushed, never inside the repo);
   - then try `git filter-repo` (pinned version) to drop paths and replace text; re-run the whole audit;
   - if that fails or still finds data, create a fresh history: orphan branch with **one** squashed commit of the
     cleaned tree, and say so in the report;
   - afterwards expire reflogs and garbage-collect so old objects are really gone locally.
5. Only `main` (and tags that point into `main`) are pushed. Delete or leave unpushed any scratch branches.

**Hardening `.gitignore`:** extend it so the excluded categories can never be re-added by accident
(`project-docs/local/`, `.env*`, `*.sqlite*`, `Manifest.*`, `*.heic`, `*.mov`, `*.log`, `logs/`, `cache/`,
`thumbs/`, `exports/`, `*.bundle`, `dist/`, `build/`, with explicit allow-rules only for the project's own
assets such as `packaging/icon/*` and `tests/assets/*.heic`). Add a lightweight **pre-commit/CI guard**
(simple script run in `ci.yml`) that fails if a forbidden file type or a UDID-like/secret-like string appears.

**Audit report:** write `project-docs/PUBLISH_AUDIT.md` with: scan tools and versions, date, number of files
and commits scanned, findings **by category and file path (never the secret/personal value itself)**, action
taken for each, history decision (kept / filtered / squashed), and the final "clean" confirmation commands and
their results.

### 0.3 Public-ready minimum before the first push
`LICENSE` (MIT unless the owner said otherwise), a README that states what the project is, that it is
unaffiliated with Apple, a responsible-use notice, and "installers coming with the first release". Nothing
else is required for the push; the full community files are produced later in Phase 10.

### 0.4 Create the GitHub repository, push, verify, then make **only this repo** public

Safeguards for the owner's other repositories:
- **Before** touching GitHub, snapshot all existing repositories and their visibility:
  `gh repo list --limit 1000 --json nameWithOwner,visibility` (and for organisations the owner belongs to, only
  if the owner confirms; default is the personal account only). Save the snapshot **outside the repo**.
- Every command that changes visibility must name the **full `OWNER/REPO` of this project explicitly**. No loops,
  no wildcards, no account-level or organisation-level settings, no changes to other repositories, no deletion.
- **After** the work, take a second snapshot and diff: the only difference allowed is the new repository.

Procedure (repo name default `backuplens`; owner = `gh api user --jq .login`):
1. `gh auth status` must succeed and show the `repo` scope. If `gh` is missing or unauthenticated, **stop** and tell
   the owner the exact fix (`winget install GitHub.cli`, then `gh auth login`).
2. Check the name is free (`gh repo view OWNER/REPO` must fail with "not found"). If it exists, **stop and ask**.
3. Create it **private first**, pushing `main`:
   `gh repo create OWNER/REPO --private --source . --remote origin --push` (description and topics set via
   `gh repo edit OWNER/REPO …`, topics such as `ios-backup`, `iphone-backup`, `backup-viewer`, `photos`).
4. **Verify the remote, not just the local tree:** shallow-clone the new repo into a temporary directory and
   run the full audit again on that clone (forbidden file types, secret/identifier patterns, author emails,
   no `project-docs/local/`, no screenshot, no `.env`). Also list the tree with
   `gh api repos/OWNER/REPO/git/trees/main?recursive=1` and compare with `git ls-files`.
5. Only if step 4 is clean: make it public:
   `gh repo edit OWNER/REPO --visibility public --accept-visibility-change-consequences`.
6. **Double-check visibility three independent ways** and record the output in `PUBLISH_AUDIT.md`:
   - `gh repo view OWNER/REPO --json visibility,isPrivate,url` → `PUBLIC` / `false`;
   - an **unauthenticated** request: `curl -s -o NUL -w "%{http_code}" https://github.com/OWNER/REPO` → `200`,
     and the unauthenticated API `https://api.github.com/repos/OWNER/REPO` returns `"private": false`
     (use `-H "Authorization:"` / no token so the owner's login is not used);
   - the second snapshot diff from the safeguard above (all other repos unchanged).
7. Enable repository features (only on this repo): Issues, Discussions (optional), vulnerability reporting
   (private security advisories), secret scanning + push protection (free for public repos), Dependabot alerts.
   Set branch protection on `main` only if it does not block the agent's own PR flow; otherwise leave it and
   list it as a manual to-do.
8. From here on, work through branches and pull requests.

### 0.5 Stop conditions for Stage A
Stop and report (do not push, do not make public) if: `gh` is missing/unauthenticated; the repository name
exists; the audit finds anything it cannot remove with certainty; history rewriting fails; the snapshot diff
shows any unexpected change; the remote re-scan is not clean. Report exactly what was found (categories and
paths, **never the values**) and the next command for the owner.

---

## 1. Deliverables (artifact matrix)

Version `X.Y.Z` comes from one place (`backend/version.py` or `pyproject.toml`; pick one, the other
reads it). Artifact names are fixed so docs and the README table never drift.

| OS | Primary installable | Also published | Built on (verify current runner labels in GitHub docs) |
|---|---|---|---|
| **Windows 10/11 x64** | `BackupLens-X.Y.Z-windows-x64-setup.exe` (Inno Setup, per-user, no admin needed, Start Menu shortcut, uninstaller) | `BackupLens-X.Y.Z-windows-x64-portable.zip` | `windows-latest` |
| **macOS Apple Silicon (arm64)** | `BackupLens-X.Y.Z-macos-arm64.dmg` (drag-to-Applications) | `…-macos-arm64.zip` | `macos-latest` (arm64) |
| **macOS Intel (x86_64)** | `BackupLens-X.Y.Z-macos-x86_64.dmg` | `…-macos-x86_64.zip` | an Intel macOS runner (e.g. `macos-13` or a newer `*-intel` label; the agent must check what exists today) |
| **Linux x86_64** | `BackupLens-X.Y.Z-linux-x86_64.AppImage` | `BackupLens-X.Y.Z-linux-amd64.deb`, `BackupLens-X.Y.Z-linux-x86_64.tar.gz` | `ubuntu-22.04` (older glibc = wider compatibility) |
| Linux arm64 (optional, stretch) | same three formats | | `ubuntu-24.04-arm` or equivalent if available |
| All | `SHA256SUMS.txt` | `THIRD_PARTY_NOTICES.txt`, `CHANGELOG` excerpt as release notes | |
| PyPI (optional, gated) | `backuplens` wheel + sdist, `pipx install backuplens` | | `ubuntu-22.04` |

Rules:
- Universal macOS binaries are **not** required. Separate arm64 and x86_64 builds avoid
  native-wheel headaches with `pillow-heif`.
- Every installable must pass its **smoke test** (§5) in CI before it is attached to a release.
- The GitHub Release is created as a **draft**. A human publishes it.

## 2. Packaging approach

- **Freezer:** PyInstaller, **one-folder** mode (fewer antivirus false positives and faster start
  than one-file). Pin the PyInstaller version. Hidden imports and data files (frontend, `pillow-heif`
  native libs, Flask templates if any, `iphone_backup_decrypt` crypto dependencies) go in a committed
  `packaging/backuplens.spec` so the build is reproducible.
- **Entry point behaviour of the frozen app** (add to `backend/app.py` if missing):
  - Flags: `--version`, `--no-browser`, `--port N`, `--data-dir PATH`, `--smoke-test` (see §5),
    `--quit-after-idle MINUTES` (default off).
  - Locate bundled resources via PyInstaller's resource directory (not the CWD).
  - Data/config/cache directories per OS: Windows `%LOCALAPPDATA%\BackupLens`; macOS
    `~/Library/Application Support/BackupLens`; Linux `${XDG_DATA_HOME:-~/.local/share}/backuplens`
    (cache in `${XDG_CACHE_HOME:-~/.cache}/backuplens`).
  - **Single instance:** write a small lock/state file (port + token) in the data dir; a second launch
    just opens the browser at the running instance.
  - **Quit control** (needed because macOS/Windows GUI builds have no console): hamburger menu item
    "Quit BackupLens" → `POST /api/app/quit` (token + Origin protected) → graceful shutdown (close
    sessions, delete temp decrypted data). Plus quit-on-idle option.
  - Console behaviour: Windows build is a **windowed** app (no console window) but writes
    `app.log` in the data dir; add a Start Menu entry "BackupLens (show console log)" only if cheap.
    Linux/AppImage keeps stdout. macOS `.app` is windowed.
  - The folder-picker (tkinter) must degrade gracefully if tkinter is absent in the frozen build
    (text field fallback already specified in `ARCHITECTURE.md` §7.3).
- **App identity:** bundle id `org.backuplens.app` (changeable), copyright line, version string from the
  single source. Original icon artwork only (no Apple/iBackup Viewer artwork): create `packaging/icon/icon.svg`
  and generate `.ico` (Windows), `.icns` (macOS, via `iconutil` on the macOS runner), PNG set (Linux)
  in a script, not by hand.

## 3. Per-OS installer specifications

### 3.1 Windows
1. PyInstaller one-folder build → `dist/BackupLens/`.
2. **Inno Setup** script `packaging/windows/backuplens.iss`: per-user install to
   `%LOCALAPPDATA%\Programs\BackupLens` (no admin), Start Menu shortcut, optional desktop shortcut task,
   uninstaller that removes program files but **asks** before deleting user data, version metadata,
   `AppId` GUID constant, Windows 10+ minimum, 64-bit only. Install Inno Setup via the runner's package
   manager if not preinstalled.
3. Portable zip of `dist/BackupLens/` + a short `README-PORTABLE.txt`.
4. Signing hook: if secrets exist (§6) sign the exe and the installer; otherwise skip and say so in the log.

### 3.2 macOS
1. PyInstaller **windowed** build producing `BackupLens.app` (bundle id, version, `LSMinimumSystemVersion`,
   high-resolution capable, icon).
2. Ad-hoc codesign the bundle at minimum (arm64 binaries must be signed to run). Use real Developer ID
   signing + notarization + stapling only if secrets exist (§6).
3. DMG with an `/Applications` symlink and a simple background-free layout via `hdiutil` (or `create-dmg`
   if it works unattended on the runner).
4. Zip of the `.app` using `ditto -c -k --keepParent` (preserves attributes).
5. Document the unsigned-app flow in `docs/INSTALL.md`: open the app → blocked → System Settings →
   Privacy & Security → "Open Anyway" (and `xattr -dr com.apple.quarantine /Applications/BackupLens.app`
   as the terminal alternative).

### 3.3 Linux
1. Build on `ubuntu-22.04`. Install needed system libs (`libheif`/runtime libs only if PyInstaller does not
   bundle them; tkinter optional).
2. **AppImage** via `appimagetool` (download with checksum verification, pinned version): AppDir with
   `AppRun`, `.desktop` file (Categories=Utility;Graphics;), icon, PyInstaller folder under `usr/lib/backuplens`.
   Document that some distros need `libfuse2` or `--appimage-extract-and-run`.
3. **.deb** via `dpkg-deb --build` from a staging tree: files in `/opt/backuplens/`, launcher symlink
   `/usr/bin/backuplens`, `/usr/share/applications/backuplens.desktop`, icons under `/usr/share/icons/hicolor/*`,
   `control` file (Package, Version, Architecture, Maintainer, Depends minimal, Description, Homepage), `postinst`
   to refresh desktop/icon caches (non-fatal).
4. **tar.gz** of the PyInstaller folder with a `install.sh`-free layout (just extract and run `./backuplens`).
5. No signing; publish SHA256SUMS. Optional later: `.rpm`, Flatpak, AUR (not in v0.1.0).

## 4. CI/CD (GitHub Actions)

Files: `.github/workflows/ci.yml`, `.github/workflows/release.yml`.

**ci.yml** (push + PR): matrix on the three OS families running `ruff`, unit and contract tests (no
integration tests), Python 3.11 and 3.12. Cache pip. Must complete in < 10 min.

**release.yml** triggers:
- `push` of tags matching `v*.*.*` (and `v*.*.*-rc*` as pre-releases),
- `workflow_dispatch` (manual dry-run that builds everything and uploads artifacts without releasing).

Jobs:
1. `verify` — tag version equals the single-source version; CHANGELOG has an entry; tests pass.
2. `build-windows`, `build-macos-arm64`, `build-macos-x86_64`, `build-linux-x86_64` — build, package,
   smoke-test (§5), upload as workflow artifacts. Each job independent so one failure is easy to read.
3. `release` (needs all build jobs): downloads artifacts, generates `SHA256SUMS.txt`, assembles release notes
   from the CHANGELOG section, creates a **draft** GitHub Release (pre-release flag for `-rc` tags) and uploads
   all files.
4. `pypi` (optional): runs only if repository variable `PUBLISH_PYPI == 'true'`; uses PyPI **Trusted
   Publishing** (OIDC), no stored token.

Security requirements for the workflows:
- Top-level `permissions: contents: read`; only the `release` job gets `contents: write`; `pypi` job gets
  `id-token: write`.
- Pin third-party actions to a full commit SHA (add a comment with the version) or at least a major version
  from trusted publishers; never run untrusted PR code with secrets (`pull_request`, not `pull_request_target`).
- Never echo secrets; signing steps are gated with `if: ${{ env.HAS_SECRET == 'true' }}`-style checks that do
  not leak secret presence beyond a boolean.
- Download third-party tools (appimagetool, Inno Setup) with pinned versions and checksum verification.
- Enable Dependabot for `github-actions` and `pip`.

Notes:
- GitHub-hosted runners are free for **public** repositories. Stage A (§0) has already made this repository
  public after the privacy audit, so the full matrix can run without metering concerns. If Stage A was
  skipped or the repo is private, stop: do not run the macOS jobs on a private repo without the owner's consent.
- Runner image labels and available Xcode/Python versions change; the agent must check current GitHub
  documentation and adapt rather than trust this file.

## 5. Smoke tests (mandatory, per artifact)

The frozen app supports `--smoke-test`: start the server on a random port with a temp data dir, request
`/` and a health endpoint (`/api/health`, no auth, returns version), verify the bundled frontend files are
served, import-check `iphone_backup_decrypt`, `PIL`, `pillow_heif`, decode a **tiny embedded HEIC sample**
(a few KB, synthetic, committed under `tests/assets/`), create a thumbnail from it, then exit 0. Any
failure exits non-zero with a clear message.

CI must run, on the actual built artifact (not the source tree):
- Windows: silent install of the setup `.exe` (`/VERYSILENT /SUPPRESSMSGBOXES /DIR=...`), run installed
  exe with `--smoke-test`, then silent uninstall and confirm the directory is gone. Also smoke-test the portable zip.
- macOS: mount the DMG, copy the `.app` out, run `Contents/MacOS/BackupLens --smoke-test`, detach. Check
  `codesign --verify --deep` (ad-hoc accepted).
- Linux: run the AppImage with `--appimage-extract-and-run --smoke-test`; `dpkg-deb --info/--contents` on the
  `.deb` then install it in the runner (`sudo dpkg -i`) and run `/usr/bin/backuplens --smoke-test`; extract the
  tar.gz and run it.
Record results in the workflow summary.

## 6. Signing and notarization (optional, off by default)

Unsigned builds must work end to end. Signing is added through **repository secrets**; when absent the
steps are skipped with a clear log line.

| Platform | Mechanism | Secrets / setup (human does this) |
|---|---|---|
| macOS | Developer ID Application certificate → `codesign --options runtime --timestamp` → `notarytool submit --wait` → `stapler staple` (DMG and app) | `APPLE_CERT_P12_BASE64`, `APPLE_CERT_PASSWORD`, `APPLE_TEAM_ID`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD` (or API-key variants). Requires a paid Apple Developer membership |
| Windows | **SignPath Foundation** (free for qualifying open-source projects, requires an OSI licence, automated builds, approval) or another cloud-signing service | `SIGNPATH_API_TOKEN` plus repo **variables** for organisation id, project slug, signing policy slug |
| Linux | none; publish checksums | — |

`docs/SIGNING.md` (to be written by the agent) documents how to obtain each, how to add the secrets, which
workflow steps they unlock, and the code-signing policy text SignPath asks projects to publish.

## 7. Licensing and compliance (blocking checks)

1. Choose the project licence (default **MIT**; ask the human only if a dependency forces a decision) and add
   `LICENSE`.
2. Generate `THIRD_PARTY_NOTICES.txt` for the frozen app: every bundled Python package **and** native library
   (including whatever `pillow-heif` ships inside its wheels, such as libheif and its codec libraries) with
   name, version, licence text/SPDX id and source URL. Include it in every installer and in the repo.
3. **Copyleft check:** list any LGPL/GPL/AGPL components that end up inside the executables. If anything
   GPL-family is bundled, **stop and report to the human** with options (change project licence, replace the
   component, ship without HEIC encode support, or make it an optional download). Do not guess.
4. Confirm `iphone_backup_decrypt`'s licence in `project-docs/schema-notes.md` (from Phase 0) and honour it.
5. Trademark hygiene: no use of "iBackup Viewer", "iMazing", Apple logos or the Photos flower in names, icons,
   screenshots or marketing copy. Add a disclaimer that BackupLens is not affiliated with Apple.
6. Add a clear **responsible-use notice** to README/INSTALL: for backups of devices you own or are authorised
   to access.

## 8. Repository and community files to generate

(Locations: `LICENSE`, `CHANGELOG.md`, `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
`THIRD_PARTY_NOTICES.txt` in the repo root; `INSTALL.md`, `SIGNING.md`, `RELEASING.md` in `docs/`;
build-process documents stay in `project-docs/`, see §0.1. `LICENSE` already exists from Stage A.)

`LICENSE` · `THIRD_PARTY_NOTICES.txt` · `CHANGELOG.md` (Keep a Changelog format, entry `0.1.0`) ·
`SECURITY.md` (private reporting via GitHub security advisories; scope: local-only app, password handling,
file handling) · `CONTRIBUTING.md` (dev setup from SETUP.md, tests, commit style, how to run the agents is
optional) · `CODE_OF_CONDUCT.md` (Contributor Covenant) · `.github/ISSUE_TEMPLATE/bug_report.yml`,
`feature_request.yml`, `config.yml` (point support questions to Discussions) ·
`.github/pull_request_template.md` · `.github/dependabot.yml` · `docs/INSTALL.md` (end-user, per OS) ·
`docs/SIGNING.md` · `docs/RELEASING.md` (maintainer checklist: bump version, update CHANGELOG, tag, watch CI,
verify artifacts on real machines, publish draft, announce) · README "Download" section with a table linking to the
latest release assets, checksum verification commands, and a "Troubleshooting installs" subsection.

Issue template for bug reports must **warn not to attach backups, photos or passwords** and ask for the
diagnostics bundle (app version, OS, iOS version of the backup, log excerpt with paths redacted). Add a
"Copy diagnostics" output in the app that is safe by design (no password, no file names).

## 9. docs/INSTALL.md content requirements (end users)

For each OS: where to download, how to verify the checksum (PowerShell `Get-FileHash`, macOS `shasum -a 256`,
Linux `sha256sum`), how to install, how to start, how to uninstall, where data lives, and exactly what the
security warning looks like and how to proceed:
- Windows SmartScreen "Windows protected your PC" → More info → Run anyway (explain why it appears for
  unsigned/new software, and what the signature will show once signing is enabled).
- macOS Gatekeeper "cannot be opened because Apple cannot verify…" → System Settings → Privacy & Security →
  Open Anyway; terminal alternative with `xattr`.
- Linux: `chmod +x` for AppImage, `libfuse2` note, `sudo apt install ./file.deb`, desktop-file location.
Also: Firewall prompts (the app only listens on localhost), antivirus false-positive note with the SHA-256
and a pointer to report false positives, and "what the app can't do" (iCloud-only photos).

## 10. Definition of Done for the release phase

**Stage A**
- [ ] Non-code files moved to `project-docs/` per §0.1; no dangling links; tests still pass.
- [ ] `project-docs/PUBLISH_AUDIT.md` exists, lists findings by category/path (no values), history decision, and
      the clean results of the working-tree scan, the history scan and the **fresh-clone re-scan**.
- [ ] No author/committer email other than the GitHub no-reply address (or one the owner explicitly approved).
- [ ] Reference screenshot, `.env`, backup-derived files, logs and caches are **not tracked** and **not in history**.
- [ ] Repository `OWNER/REPO` is **public**, confirmed by `gh repo view`, by an unauthenticated HTTP request and by
      the unauthenticated API (`"private": false`); evidence recorded.
- [ ] The before/after snapshots of the owner's repositories differ **only** by the new repository; all others
      keep their previous visibility.

**Stage B**
- [ ] A tag `v0.1.0-rc1` produces a **draft pre-release** containing every artifact in §1, `SHA256SUMS.txt`, and
      notices, with all smoke tests green in CI.
- [ ] The Windows installer was also **installed and run locally** by the agent on the human's Windows machine,
      opening a real backup (if the human allowed) or at least `--smoke-test`.
- [ ] macOS and Linux artifacts were verified by CI smoke tests; the report lists exactly what was **not**
      verified on real hardware.
- [ ] README, INSTALL, SIGNING, RELEASING, SECURITY, CONTRIBUTING, LICENSE, notices all present and consistent
      with the real artifact names.
- [ ] No personal data in the repo or artifacts (scan the built folders for `.sqlite`, images, `.env`).
- [ ] `AGENTS.md` status board shows Phase 10 and the Architect's APPROVE.

## 11. AGENTS.md addendum (the agent adds this)

Add to the phase table in `AGENTS.md` §4:

| 10A | **Repo reorganisation, privacy audit, public GitHub repo** | qa (release engineer) | architect | `project-docs/`, `PUBLISH_AUDIT.md`, public repo | §10 Stage A |
| 10B | **Cross-platform release** | qa (release engineer) | architect, api | `packaging/`, workflows, installers, docs in §8, rc tag | §10 Stage B |

Add rows for Phases 10A and 10B to the status board. The **qa** agent owns `packaging/`, `.github/`, `project-project-docs/RELEASE.md`,
`project-docs/PUBLISH_AUDIT.md`, `docs/INSTALL.md`, `docs/SIGNING.md`, `docs/RELEASING.md`, `LICENSE`, `CHANGELOG.md`, `SECURITY.md`,
`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `THIRD_PARTY_NOTICES.txt`. The **api** agent may be asked to add the
launcher flags, `/api/health`, `/api/app/quit` and single-instance logic in `backend/` (§2).

## 12. Risks

| Risk | Mitigation |
|---|---|
| PyInstaller misses native libs (`pillow-heif`) on one OS | `--smoke-test` decodes a real HEIC sample in every build |
| Antivirus false positives on Windows | one-folder build, installer, signing when available, checksums, INSTALL note |
| macOS blocks the app | documented flow; notarization path ready behind secrets |
| macOS Intel runner label disappears | agent checks current labels; fall back to documenting Rosetta or source install |
| AppImage fails on some distros | `.deb` and tar.gz alternatives; libfuse2 note |
| GPL component bundled unexpectedly | §7.3 stop-and-report rule |
| CI works but real machines don't | release DoD lists what was only CI-verified; ask early testers on each OS |
| Secrets leakage in workflows | least privilege, gated steps, no `pull_request_target`, no echoing |
| Personal data published (device ID, place names, email in commits, screenshot) | §0.2 audit of tree **and** history, fresh-clone re-scan, private-first push, CI guard script |
| Rewriting history destroys the only copy | `git bundle` backup outside the repo before any rewrite |
| Visibility command hits the wrong repo | explicit `OWNER/REPO` only, before/after snapshots of all repos, unauthenticated checks |
| Moving files breaks links or tests | link checker + full test run after §0.1; `AGENTS.md` stays in the root |
| Image content cannot be reviewed by a text-only model | images excluded by default; only project-made assets allow-listed |
