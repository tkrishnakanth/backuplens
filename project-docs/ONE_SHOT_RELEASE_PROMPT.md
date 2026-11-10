# ONE-SHOT RELEASE PROMPT (Phase 10: publish + installers)

Use this after Phases 0-9 are finished. In one run the agent will:

**Stage A:** move the non-code files into a new folder, audit everything (files *and* git history) for
personal or critical data, create your GitHub repository, push it, make **only this repository** public,
and double-check that it really is public while your other repositories stay private.

**Stage B:** build installable packages for Windows, macOS and Linux, set up GitHub Actions, add the
open-source community files and produce a draft pre-release.

The specification is `project-docs/RELEASE.md` (Stage A is §0). Put both files in your `docs/` folder first.

> Reality check: one prompt can write everything, and the agent can fully test the Windows installer on your
> PC. macOS and Linux installers can only be built and tested on GitHub's machines, so expect 1-3 "fix the CI"
> rounds (the prompt has a capped repair loop; §3 has follow-up prompts).

---

## 1. Before you paste (checklist for you)

1. Phases 0-9 are finished and committed locally; tests pass.
2. `project-docs/RELEASE.md` and this file are in `docs/`.
3. **GitHub CLI installed and logged in:** run `gh auth status`. It must show you are logged in with the
   `repo` scope. If `gh` is missing: `winget install GitHub.cli`, then `gh auth login`. (Your saved git
   credentials alone can push, but they cannot create a repo or change visibility; `gh` can.)
4. Decide the repository name (default in the prompt: `backuplens`) and edit the `REPO_NAME` line if you want
   another. The agent stops if that name already exists on your account.
5. Install **Inno Setup 6** (jrsoftware.org) so the Windows installer can be tested locally.
6. Close anything that holds files open in the project folder (editors with unsaved work, iTunes using the backup).
7. Optional but wise: copy the whole project folder somewhere else as a manual backup before starting. The agent
   also makes its own `git bundle` backup before any history rewrite.
8. Start a **fresh opencode session** with your strongest DeepSeek model.

## 2. THE PROMPT (paste everything inside the block)

```
You are the lead engineer for BackupLens. Phases 0-9 are done. Your task is PHASE 10, in two stages,
specified in project-docs/RELEASE.md (Stage A = section 0, Stage B = sections 1-12). Use the qa persona as release
engineer, api persona for backend changes, architect persona for review (AGENTS.md section 2). Work
autonomously. Stop only in the cases listed under "WHEN TO STOP".

REPO_NAME = backuplens        (owner = the logged-in GitHub user from `gh api user --jq .login`)

STEP 0 - READ
Read fully: project-docs/RELEASE.md, project-docs/ONE_SHOT_RELEASE_PROMPT.md, README.md, ARCHITECTURE.md, AGENTS.md,
SETUP.md, project-docs/FEATURES.md and PROMPT_LOG.md, then list the repository (git ls-files and the untracked
files). Follow AGENTS.md section 1 throughout. Never print, store or commit secrets, the backup password,
device identifiers or any content from my backup. Do not read .env values; only check that the variables exist.

STEP 1 - PRE-FLIGHT
Check: git works; the working tree state (commit or stash nothing silently, tell me what is uncommitted);
tests and ruff pass; Python 3.11+; Inno Setup 6; `gh auth status` OK with repo scope. Take the SAFETY
SNAPSHOT of my GitHub repositories: `gh repo list --limit 1000 --json nameWithOwner,visibility`, saved to a
file OUTSIDE the project folder (for example one level above it). If gh is missing or not authenticated,
stop and give me the exact command to run.

========== STAGE A: REORGANISE, AUDIT, PUBLISH (project-docs/RELEASE.md section 0) ==========

STEP 2 - REORGANISE
Create branch phase-10a-publish. Create the folder project-docs/ and move into it, using `git mv`, every
non-code file that is not required in the root (ARCHITECTURE.md, SETUP.md, PROMPT_LOG.md, project-docs/FEATURES.md,
project-docs/UI_SPEC.md, project-docs/RELEASE.md, project-docs/ONE_SHOT_RELEASE_PROMPT.md, schema notes, spike outputs, scratch
notes, status-board material). Keep in the root: README.md, LICENSE, CHANGELOG.md, SECURITY.md,
CONTRIBUTING.md, CODE_OF_CONDUCT.md, .gitignore, requirements.txt, .github/, and AGENTS.md (opencode only
auto-loads it from the root; mention this in your report). Keep docs/ for the public user-facing docs written
later. Move the reference screenshot and any raw/personal spike output into project-docs/local/ (git-ignored,
never tracked). Then fix EVERY cross-reference: links and paths in all Markdown files, the reading order in
AGENTS.md section 1, the prompts in PROMPT_LOG.md, .gitignore entries, and any code/test/script that refers to
a moved file. Run a link/path check and the full test suite; zero dangling references allowed. Add a short
"Project documentation" section to README.md.

STEP 3 - PRIVACY AUDIT (working tree AND full git history)
Follow project-docs/RELEASE.md section 0.2 literally. Scan EVERY tracked text file, not a sample, plus the list of all
files ever added in history. Use gitleaks or detect-secrets if you can install a pinned version, AND the custom
patterns in section 0.2, AND read the files most likely to contain personal data (PROMPT_LOG.md, SETUP.md,
schema notes, tests, fixtures, scripts, mock data, any json/yml/opencode config). I know at least that SETUP.md
contains my real device ID as an example (copied from my screenshot), that spike/schema notes may contain real
sample rows, file names, dates and place names from my library, and that the reference screenshot contains
personal photos and a photographed document with a name, phone number and email: treat all of that as
critical. You may be unable to view images: exclude every image or binary that is not an app asset created
by this project (icon source, frontend assets, the synthetic tests/assets HEIC), without inspecting it.
Actions: remove/replace/move per the Tier rules; sanitise schema-notes.md (structure only, no sample rows or real
names; raw copy only in project-docs/local/); move reference counts to an ignored local file read through an
optional environment variable (tests skip if absent); replace UDIDs, paths and names with placeholders; harden
.gitignore; add the CI guard script that fails on forbidden file types or secret/UDID-like strings.
History: list distinct author/committer emails; list all files ever added; scan all revisions. First create the
safety copy OUTSIDE the project: `git bundle create ../<REPO_NAME>-original.bundle --all`. If anything personal
or secret is in history, or any personal email is used, rewrite: try git filter-repo (pinned), re-audit; if that
fails or still finds data, create a fresh single-commit history of the cleaned tree. Use my GitHub no-reply
address (<id>+<login>@users.noreply.github.com from `gh api user`) for all commit identities and set it as the
repo-local git user.name/user.email. After any rewrite expire reflogs and gc. Only main (and tags into main) will
be pushed.
Write project-docs/PUBLISH_AUDIT.md: tools and versions, scope counts, findings by CATEGORY and FILE PATH
only (never the value), action per finding, history decision. If you cannot remove something with certainty,
STOP and report.

STEP 4 - MINIMUM PUBLIC-READY FILES
Add LICENSE (MIT unless I said otherwise) and make README.md state what the project is, that it is not
affiliated with Apple, a responsible-use notice (only for backups of devices you own or are authorised to
access), and that installers arrive with the first release. Commit, merge to main (a local merge is fine).

STEP 5 - CREATE THE GITHUB REPO, PUSH, VERIFY, MAKE PUBLIC
Follow project-docs/RELEASE.md section 0.4 exactly:
1. Check OWNER/REPO does not exist (gh repo view must fail). If it exists, STOP and ask me.
2. Create it PRIVATE first and push main:
   gh repo create OWNER/REPO --private --source . --remote origin --push
   Set description and topics on THIS repo only.
3. Verify the REMOTE: shallow-clone the new repo into a temporary folder, rerun the full audit on that clone,
   compare `gh api repos/OWNER/REPO/git/trees/main?recursive=1` with `git ls-files`. Confirm: no project-docs/local,
   no screenshot, no .env, no sqlite/images/logs, only the no-reply email in commits.
4. Only if that is clean, make THIS repo public, naming it explicitly:
   gh repo edit OWNER/REPO --visibility public --accept-visibility-change-consequences
   Never use loops, wildcards, account-level or organisation settings; never touch another repository.
5. DOUBLE-CHECK public status three independent ways and paste the output into PUBLISH_AUDIT.md:
   (a) gh repo view OWNER/REPO --json visibility,isPrivate,url  -> PUBLIC / false
   (b) an UNAUTHENTICATED request (no token, no login): HTTP 200 for https://github.com/OWNER/REPO and
       "private": false from https://api.github.com/repos/OWNER/REPO
   (c) take the second snapshot of my repositories and diff it with the first: the ONLY difference allowed is
       the new repository (all my other repositories must have the same visibility as before, i.e. private
       ones still private). If there is any other difference, STOP immediately and report.
6. Enable on THIS repo only: Issues, private vulnerability reporting, secret scanning + push protection,
   Dependabot alerts (and Discussions if available). From here on, work only through branches and pull requests.
Record the Stage A results, update the AGENTS.md status board (phases 10A and 10B rows), commit.

========== STAGE B: INSTALLERS AND RELEASE (project-docs/RELEASE.md sections 1-12) ==========

STEP 6 - APP CHANGES FOR PACKAGING (api persona; section 2)
Branch phase-10b-release. Implement with tests: a single version source; flags --version, --no-browser, --port,
--data-dir, --smoke-test, --quit-after-idle; resource lookup that works inside a PyInstaller bundle; per-OS
data/cache dirs; single-instance behaviour; unauthenticated GET /api/health (version + "ok" only);
POST /api/app/quit (token + Origin protected) with a "Quit BackupLens" item in the hamburger menu; graceful
shutdown that deletes temp decrypted data; --smoke-test per section 5 including decoding a tiny SYNTHETIC HEIC
sample in tests/assets/ (not from my library) and making a thumbnail. Keep all tests green. Add ADR rows.

STEP 7 - PACKAGING (qa persona; sections 2-3)
Create our own original icon source (packaging/icon/icon.svg; no Apple or competitor artwork) and a generator
script for .ico/.icns/PNGs. Create packaging/backuplens.spec (PyInstaller one-folder, pinned) and the per-OS
packaging: Inno Setup script (per-user, no admin), macOS .app + DMG + zip, Linux AppImage + .deb + tar.gz.
Build the Windows app, portable zip and installer LOCALLY. Silent-install into a temp dir, run --smoke-test,
silent-uninstall, show me the output. If BACKUP_PATH and BACKUP_PASSWORD exist in the environment, also run the
installed app with --no-browser, open my real backup through the API and report only the asset COUNT
(never print the password, paths with my username, or any file names).

STEP 8 - CI/CD (section 4)
Write .github/workflows/ci.yml (matrix on 3 OS families, includes the privacy guard script) and release.yml
(verify, 4 build jobs, per-artifact smoke tests on the built artifacts, draft GitHub Release with
SHA256SUMS.txt and notes from CHANGELOG.md, optional gated PyPI job via Trusted Publishing). Apply the security
rules: least-privilege permissions, pinned actions, no pull_request_target, pinned and checksum-verified tool
downloads, no secrets required for the unsigned path; optional gated signing/notarization per section 6. Check
the CURRENT GitHub runner labels in GitHub's documentation (Intel macOS, Linux arm64) and adapt. Add
.github/dependabot.yml.

STEP 9 - LICENSING AND COMMUNITY FILES (sections 7-9)
Generate THIRD_PARTY_NOTICES.txt for Python packages AND native libraries inside the frozen app; run the
copyleft check (if any GPL/AGPL component is bundled, STOP and report with options). Write CHANGELOG.md,
SECURITY.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, issue and PR templates (the bug template must warn not to
attach backups, photos or passwords), docs/INSTALL.md, docs/SIGNING.md, docs/RELEASING.md, and the README
Download section with checksum commands. Re-run the privacy guard on the built folders and on git ls-files.

STEP 10 - PUSH AND CI REPAIR LOOP
Push phase-10b-release, open a pull request with gh, run release.yml via workflow_dispatch (dry run) and watch
it (gh run watch, gh run view --log-failed). Fix root causes, push, repeat; at most 6 iterations per failing
job, then stop and report. When everything is green: merge the PR to main, tag v0.1.0-rc1, push the tag, and
verify the DRAFT pre-release contains every artifact in section 1 plus SHA256SUMS.txt; download them with
gh release download and verify the checksums. NEVER publish the release, NEVER create the final v0.1.0 tag,
NEVER change visibility of any repository again.

STEP 11 - REVIEW AND REPORT
As the architect, check every item of project-docs/RELEASE.md section 10 (Stage A and B) with evidence; update the
AGENTS.md status board and PROMPT_LOG.md (append an Outcome entry: commands used and results, no secrets or
personal values). Final report: (1) Stage A result: new folder layout, what the audit found by category (no
values), history decision, the exact public-visibility evidence, and the before/after snapshot diff;
(2) artifacts with sizes and checksums; (3) what was verified on this machine versus only in CI; (4) the
warnings users will see per OS; (5) what I must do manually (publish the draft, optional signing secrets, PyPI
trusted publisher, testing on real Mac/Linux, relocating AGENTS.md if I want); (6) known issues.

WHEN TO STOP AND ASK ME
- gh missing/unauthenticated, repo name already exists, or the snapshot diff shows any unexpected change;
- anything personal/secret remains that you cannot remove with certainty, or history rewriting fails;
- a GPL/AGPL component is bundled in the executables;
- a new third-party dependency or tool is needed that project-docs/RELEASE.md does not name;
- the same CI job fails after 6 repair iterations;
- anything would need secrets, a paid account, publishing a release, or changing any other repository;
- any step would write inside a backup folder.
When stopping: what you tried, what you need, and the exact next command for me.

CONTEXT MANAGEMENT
Commit after each step (Conventional Commits, no-reply identity). Keep the AGENTS.md status board and
PROMPT_LOG.md current. If I say "resume", read them plus PUBLISH_AUDIT.md and git log, then continue at the
first unfinished step; never redo finished steps and never re-run a visibility change that already succeeded.
```

## 3. Follow-up prompts

**Resume after context loss:**
```
Resume Phase 10. Read AGENTS.md status board, project-docs/PROMPT_LOG.md (last 5 entries),
project-docs/PUBLISH_AUDIT.md, project-project-docs/RELEASE.md section 10 and git log. Determine the first unfinished
step of the Phase 10 prompt (Stage A or B) and continue from there. Do not redo finished steps and do not
change repository visibility again.
```

**Independent re-check that nothing personal is public (run any time, also after future commits):**
```
Run a fresh public-exposure audit of OWNER/REPO. Shallow-clone it into a temp folder, scan every file and the
full history for secrets, device identifiers (UDID-like strings), personal emails, local user paths, place/album
names from my library, backup-derived files, images that are not project assets, and logs. Confirm only the
no-reply email appears in commits. Re-verify that the repo is public (gh, unauthenticated HTTP, unauthenticated
API) and compare `gh repo list` with the saved snapshot to prove no other repository changed visibility.
Report findings by category and path only, never values.
```

**If something personal was found in the public repo afterwards (emergency):**
```
Treat as an incident. Do not just delete the file in a new commit. 1) Tell me exactly which category and path
(no values). 2) Make a git bundle backup outside the repo. 3) Rewrite history with git filter-repo (or a fresh
squashed history) to remove it, force-push main with --force-with-lease after I confirm, delete affected tags
and releases, and re-run the full audit on a fresh clone. 4) List what I must do manually: rotate any exposed
secret, ask GitHub Support to purge cached views and orphaned commits if needed, and delete forks if any.
```

**Fix a failing CI job:**
```
CI job "<job name>" fails. Use `gh run list` and `gh run view <id> --log-failed` to find the root cause (do not
just retry), fix it on the phase-10b-release branch, push, and re-run only that job if possible. Report cause,
fix and evidence. Max 6 iterations, then stop and report.
```

**A user on a real Mac/Linux/Windows machine reports a problem:**
```
Bug report from a real machine: OS=<..>, artifact=<..>, symptom=<..>, log excerpt=<..> (paths redacted).
Reproduce what you can in CI (add a smoke-test case that would have caught it), fix the root cause, bump the rc
number (v0.1.0-rcN), update CHANGELOG.md and docs/INSTALL.md if user-facing behaviour or warning text changed,
and report what remains unverifiable without that hardware.
```

**Turn on signing later:**
```
Enable optional signing. I added these repository secrets/variables: <names only, never values>. Wire macOS
Developer ID signing + notarization + stapling and/or SignPath Windows signing per project-project-docs/RELEASE.md
section 6 and docs/SIGNING.md. Verify with a v0.1.1-rc1 dry run that signed artifacts verify (codesign --verify,
spctl --assess, Get-AuthenticodeSignature as available), update docs/INSTALL.md to remove warnings that no longer
apply, and report.
```

**Publish to PyPI later:**
```
Prepare PyPI publishing. Add/verify pyproject.toml (name backuplens or an available alternative: check
availability; console_scripts entry "backuplens"; frontend as package data; version from the single source),
build sdist+wheel, test `pipx install` from the built wheel in a clean venv and run backuplens --smoke-test.
Keep the pypi workflow job gated by repository variable PUBLISH_PYPI and Trusted Publishing; explain exactly what
I must configure on pypi.org. Do not publish.
```

## 4. After the agent finishes: your manual steps

1. Open `https://github.com/<you>/<repo>` in a **private/incognito window** (not logged in) and confirm you can
   see it. Click through the file list yourself once: no screenshot, no `.env`, no `project-docs/local`.
2. Check **github.com/<you>?tab=repositories** while logged in: your other repositories must still show
   the **Private** label.
3. Look at one or two commits: the author should show your GitHub no-reply identity.
4. Download the draft pre-release files and test on real machines if you can (a Mac, a Linux VM).
5. Read the draft notes, then **Publish release** yourself. Tag the final `v0.1.0` only when the rc is good.
6. Keep `project-docs/local/` and the `../<repo>-original.bundle` backup on your own disk only; delete the bundle
   once you are sure you don't need the original history.
7. Later: apply to SignPath Foundation (Windows), consider the Apple Developer membership (macOS), add winget /
   Homebrew / AUR once there are users.
