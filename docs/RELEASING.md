# Releasing BackupLens

Maintainer checklist. The version has one source: `backend/version.py`. `pyproject.toml` reads it
dynamically. Artifact names are defined in `docs/INSTALL.md` and the release workflow.

## 1. Prepare

1. Update `backend/version.py`.
2. Add the matching `CHANGELOG.md` section with the date.
3. Run the full gates:
   ```powershell
   ruff check .
   pytest -q
   pytest -q -m integration
   python scripts/privacy_guard.py
   python scripts/generate_notices.py
   python scripts/generate_icons.py
   ```
4. Refresh `THIRD_PARTY_NOTICES.txt` (the generator reads the installed wheel licences) and check the
   source tag URL/version in it.
5. Confirm no personal data, `.env`, backup, photo, SQLite, log or cache is tracked or in the build folder.

## 2. Build and test locally (Windows)

```powershell
python scripts/build_exe.py
python -m PyInstaller --version   # pinned 6.22.3
python -c "from pathlib import Path; print(Path('dist/BackupLens/BackupLens.exe').exists())"
dist\BackupLens\BackupLens.exe --smoke-test
```

Build the installer:

```powershell
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "/DMyAppVersion=<version>" packaging\windows\backuplens.iss
```

Silent install/smoke/uninstall, then create the portable ZIP (the workflow does the same automatically).

## 3. CI and draft release

1. Push a branch and open a PR; wait for `.github/workflows/ci.yml` (3 OS families).
2. Merge the PR. `workflow_dispatch` only sees workflows that exist on the default branch.
3. Optional dry run from `main`: `gh workflow run release.yml --ref main` and fix any job failures in a
   follow-up PR. This builds all platforms but creates no release.
4. Tag an RC: `git tag -a v<version>-rc1 -m "BackupLens v<version>-rc1"` and push the tag.
5. The workflow creates a **draft** GitHub Release with Windows, macOS arm64/Intel, Linux artifacts,
   `SHA256SUMS.txt`, notices and notes. It never publishes automatically.
6. Download the draft assets with `gh release download`, verify checksums, and test on real machines where
   possible.
7. If a draft run fails only in workflow/packaging code, fix it, delete the **unpublished** draft and its
   tag, and recreate the tag on the fixed commit. Never delete or replace assets after publishing.

## 4. Publish (human only)

Review the notes and artifacts, then click **Publish release** in GitHub. Create the final `v<version>` tag
only when the RC is good. Never attach personal data or a backup to a release.

## 5. Optional PyPI

The workflow has a gated `pypi` job. It runs only when repository variable `PUBLISH_PYPI` is `true` and uses
Trusted Publishing (OIDC), not a stored token. Configure a PyPI trusted publisher for this repository and
the `pypi` environment before enabling it. Publishing is a human decision.

## 6. After release

- Announce with the checksum and source links.
- Watch issues for OS-specific install problems.
- For a regression, bump the RC number (`v<version>-rcN`), update `CHANGELOG.md`/`docs/INSTALL.md`, and
  repeat; do not silently replace published assets.
