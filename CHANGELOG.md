# Changelog

All notable changes are recorded here. Format follows Keep a Changelog; versions use SemVer.

## [0.1.0] — 2026-10-28

First release. Local-only, read-only browser and exporter for photos in encrypted iOS backups.

### Added

- Backup discovery in the default Windows locations, custom folder registration, device metadata,
  password unlock with typed wrong-password errors, and session close with temp-data purge.
- Photo browser matching the reference layout: header/toolbar, sidebar with 13 categories, user albums
  and moments/places, status bar, date-grouped virtualised grid, lazy thumbnails, multi-select,
  type filter, calendar jump, filename + date-range search, and a keyboard-friendly lightbox.
- Media pipeline that prefers the backup's own thumbnails, generates previews with Pillow/pillow-heif,
  falls back to ffmpeg or a placeholder, and streams originals (and Live Photo videos) with HTTP Range.
- Unlimited export to a folder: ids or scope, flat/by-date/by-album/original-path layouts,
  skip/rename/overwrite, optional HEIC→JPEG, Live Photo video, edited `.AAE` sidecars, capture-date
  mtimes, cooperative cancel, per-file errors, and `export-report.txt`.
- Store-only ZIP download for small selections (≤500 items / 2 GB).
- Raw file explorer: domains, lazy folder tree, case-insensitive SQLite `LIKE` search with `%`, `_`,
  `\` escape, sortable columns, download, and export matching/selected with relative paths preserved.
- Settings persisted to `%LOCALAPPDATA%\BackupLens\config.json`: theme (light/dark/system),
  date-grouping zone, thumbnail size, cache location and limit.
- Localhost security: one-time token cookie, Host/Origin/Sec-Fetch-Site checks, CSP, no-store JSON,
  gzip, redacting logs, and consistently typed JSON errors.

### Privacy

- The backup folder is never written to. The password is never logged or persisted; decrypted temp
  data and the media cache are removed on exit unless `CACHE_PERSIST` is enabled.
- No outbound network calls at runtime; no CDN assets.

### Licence and packaging

- Relicensed from MIT to **GPL-3.0-or-later** (ADR-010) because the official `pillow-heif` wheels
  bundle x265 (GPL-2.0-or-later). This keeps source and binary distribution consistent.
- Added reproducible PyInstaller one-folder packaging, Windows Inno Setup installer, macOS DMG/zip and
  Linux AppImage/.deb/tar.gz build scripts.
- Added `THIRD_PARTY_NOTICES.txt` with every bundled Python/native component, exact versions, source
  URLs and full licence texts, plus the source tag URL in installers and release notes.
- Added per-OS data/cache paths, single-instance launch, `--version`, `--data-dir`, `--smoke-test`,
  `--quit-after-idle`, `/api/health`, `/api/app/quit` and a Quit menu item.

### Known gaps

- In-app rich preview of arbitrary raw files (F-RAW-05, P2) is not implemented; files can be downloaded.
- Device-info panel (F-BKP-06), symlink target UI (F-RAW-06), and the Messages/Contacts/Calls/Notes/
  Calendar/Safari/Voice/Apps modules are optional/P2/P3.
- The optional PyInstaller one-folder build is provided and smoke-tested, but has not been tested on a
  completely clean Windows profile without Python installed.

### Verification

- 106 unit/contract tests + 15 integration tests against a real encrypted iPhone backup.
- Reference sidebar parity verified against the owner's local-only acceptance file.
- 20 exported files byte-identical to the decrypted originals; HTTP Range verified; 100 thumbnails
  3.28 s cold / 0.10 s warm.
