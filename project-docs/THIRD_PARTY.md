# Third-party notices

BackupLens is MIT-licensed. Runtime dependencies are pinned in `requirements.txt`; development tools
are in `requirements-dev.txt`. All runtime licences are compatible with MIT distribution.

| Component | Version | Licence | Use |
|---|---|---|---|
| iphone_backup_decrypt | 0.11.2 | MIT | Keybag, PBKDF2, key unwrap, AES-CBC file decryption |
| pycryptodome | 4.2.0 | BSD-2-Clause | AES implementation used by the decrypt library |
| Flask | 3.1.3 | BSD-3-Clause | Local HTTP API and static files |
| Waitress | 3.0.2 | ZPL-2.1 | Production WSGI server on Windows |
| Pillow | 13.0.0 | MIT-CMU | Image decode, thumbnails, JPEG conversion |
| pillow-heif | 1.8.1 | BSD-3-Clause | HEIC/HEIF decoding and encoding |
| pytest | 9.2.0 | MIT | Tests (development only) |
| ruff | 0.17.3 | MIT | Lint/format (development only) |

`iphone_backup_decrypt` is distributed under the MIT licence (Copyright 2019–2026 James Sharkey), and
`pycryptodome` under BSD-2-Clause. No GPL/AGPL code is linked.

Optional tools: `ffmpeg` (LGPL/GPL depending on build) is invoked as a separate executable only when it
is already on PATH for video poster fallback; it is not bundled.

`project-docs/local/ibackup-viewer-photos.png` is a local reference screenshot of a commercial app. It is
**not** part of the source distribution and is git-ignored; no commercial logos or artwork are reused.
The UI uses original inline SVG icons.
