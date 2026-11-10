# Contributing to BackupLens

Thanks for helping. BackupLens is a local-only, read-only browser/exporter for iOS backups. Please keep
privacy and the read-only guarantee intact.

## Licence of contributions

BackupLens is licensed under **GPL-3.0-or-later**. By submitting a contribution (code, docs, artwork or
tests) you agree that it may be distributed under GPL-3.0-or-later. Do not contribute code or assets that
you cannot license this way.

## Development setup

```powershell
git clone https://github.com/tkrishnakanth/backuplens
cd backuplens
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

The app itself: `.venv\Scripts\python.exe backend\app.py` (or append `?mock=1` to use the synthetic demo).
Developer and build documentation lives in [`project-docs/`](../project-docs/).

## Before opening a pull request

```powershell
ruff check .
pytest -q
python scripts/privacy_guard.py
```

Integration tests additionally need a local backup and are gated by `BACKUP_PATH`/`BACKUP_PASSWORD`:

```powershell
pytest -q -m integration
```

- Use Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- Keep the backup folder read-only; never add a function that writes to it.
- Never commit a password, `.env`, photos, thumbnails, SQLite files, logs, exports or a real backup.
- Use synthetic fixtures for tests and keep personal library names/counts out of the public repository.
- If you change behaviour or the API, update the relevant document under `project-docs/` (and add an ADR
  for architectural changes).
- New runtime dependencies need an ADR with size and licence noted.

## Reporting bugs and security issues

- Bugs: use the bug report template. Do not attach backups, photos, passwords or personal logs.
- Security/privacy: follow [SECURITY.md](SECURITY.md), not a public issue.

## Code of conduct

Participation is covered by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
