# Installing BackupLens

BackupLens is a local-only app. Its installers contain no analytics, accounts or cloud calls. Use it only
on backups of devices you own or are authorised to access. It is not affiliated with Apple.

The release artifacts are unsigned unless the maintainers have enabled signing. Verify downloads with
`SHA256SUMS.txt` from the same release before running them.

## Download names

| OS | Primary file | Also published |
|---|---|---|
| Windows 10/11 x64 | `BackupLens-<version>-windows-x64-setup.exe` | `BackupLens-<version>-windows-x64-portable.zip` |
| macOS Apple Silicon | `BackupLens-<version>-macos-arm64.dmg` | `BackupLens-<version>-macos-arm64.zip` |
| macOS Intel | `BackupLens-<version>-macos-x86_64.dmg` | `BackupLens-<version>-macos-x86_64.zip` |
| Linux x86_64 | `BackupLens-<version>-linux-x86_64.AppImage` | `.deb`, `.tar.gz` |

Get them from https://github.com/tkrishnakanth/backuplens/releases. A draft release is not downloadable
until the maintainer publishes it.

## Verify the checksum

Windows PowerShell:

```powershell
Get-FileHash .\BackupLens-<version>-windows-x64-setup.exe -Algorithm SHA256
```

macOS:

```bash
shasum -a 256 BackupLens-<version>-macos-arm64.dmg
```

Linux:

```bash
sha256sum BackupLens-<version>-linux-x86_64.AppImage
```

Compare with the matching line in `SHA256SUMS.txt`.

## Windows

1. Run the setup `.exe`. It installs **per user** to `%LOCALAPPDATA%\Programs\BackupLens`; no administrator
   rights are needed. A Start Menu shortcut is created; the desktop shortcut is optional.
2. The build is currently unsigned. Windows SmartScreen may say **“Windows protected your PC”**. Choose
   **More info → Run anyway** only if you verified the checksum and downloaded from the official release.
   Once signing is enabled, the dialog will show the project's signing identity instead.
3. Start **BackupLens**. It opens a token URL in your browser. The window itself is hidden; logs are in
   `%LOCALAPPDATA%\BackupLens\logs\app.log`.
4. Uninstall from Settings → Apps. The uninstaller asks before deleting settings/cache. Your backup folder
   is never touched.
5. Portable ZIP: extract it and run `BackupLens.exe`; delete the folder to remove the program.

## macOS

1. Open the `.dmg`, drag **BackupLens** to `/Applications`, then eject the disk image.
2. The build is currently unsigned/not notarized. On first launch macOS may block it: open **System
   Settings → Privacy & Security**, find the BackupLens message and choose **Open Anyway** (or right-click
   the app → Open). Terminal alternative:
   `xattr -dr com.apple.quarantine /Applications/BackupLens.app`
3. The app is windowed; use the hamburger menu → **Quit BackupLens** to stop it. Data and logs are in
   `~/Library/Application Support/BackupLens`.
4. Uninstall by moving the app to Trash, then optionally delete the data folder.
5. The `.zip` contains the same app for users who prefer not to use a DMG.

## Linux (x86_64)

**AppImage**

```bash
chmod +x BackupLens-<version>-linux-x86_64.AppImage
./BackupLens-<version>-linux-x86_64.AppImage
```

If your distribution lacks FUSE 2, install `libfuse2` or run with `--appimage-extract-and-run`. The app
listens only on `127.0.0.1`; allow the localhost firewall prompt if one appears. Data is in
`${XDG_DATA_HOME:-~/.local/share}/backuplens`; cache in `${XDG_CACHE_HOME:-~/.cache}/backuplens`.

**Debian/Ubuntu .deb**

```bash
sudo apt install ./BackupLens-<version>-linux-amd64.deb
backuplens
```

The package installs under `/opt/backuplens` with a `/usr/bin/backuplens` launcher and a desktop entry.
Uninstall with `sudo apt remove backuplens`; user data is left in place.

**tar.gz**

```bash
tar -xzf BackupLens-<version>-linux-x86_64.tar.gz
./BackupLens --no-browser
```

## Antivirus and firewall

Unsigned, newly released binaries can trigger antivirus heuristics. Check the SHA-256 and report a false
positive to the vendor if needed. BackupLens only listens on `127.0.0.1`; do not expose it to a network.

## What it cannot do

- Download iCloud-only photos that are not in the local backup.
- Play HEVC/MOV in a browser without the codec; use **Download original** instead.
- Modify, restore or delete anything in the backup.

## Licence and source

BackupLens is **GPL-3.0-or-later**. The exact corresponding source for a release is linked in
`THIRD_PARTY_NOTICES.txt` and in the release notes, together with the source of the bundled native
libraries (libheif, libde265, x265) at the versions used. The one-folder layout keeps LGPL libraries as
separate replaceable DLLs/shared libraries.
