#!/usr/bin/env bash
# Build the Linux artifacts on ubuntu-22.04.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
VERSION="$(python -c 'from backend.version import VERSION; print(VERSION)')"
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging/backuplens.spec
APP="dist/BackupLens"
BIN="$APP/BackupLens"
if [ ! -x "$BIN" ]; then
  echo "Linux executable not produced" >&2
  exit 1
fi
cp THIRD_PARTY_NOTICES.txt LICENSE "$APP/"
mkdir -p dist/linux
tar -C "$APP" -czf "dist/linux/BackupLens-${VERSION}-linux-x86_64.tar.gz" .

# .deb staging
DEB="dist/deb"
rm -rf "$DEB"
mkdir -p "$DEB/DEBIAN" "$DEB/opt/backuplens" "$DEB/usr/bin" "$DEB/usr/share/applications" "$DEB/usr/share/icons/hicolor/256x256/apps"
cp -R "$APP/." "$DEB/opt/backuplens/"
ln -s /opt/backuplens/BackupLens "$DEB/usr/bin/backuplens"
cp packaging/icon/icon-256.png "$DEB/usr/share/icons/hicolor/256x256/apps/backuplens.png"
cat > "$DEB/usr/share/applications/backuplens.desktop" <<DESKTOP
[Desktop Entry]
Name=BackupLens
Comment=Browse and export photos from local iOS backups
Exec=/opt/backuplens/BackupLens
Icon=backuplens
Terminal=false
Type=Application
Categories=Utility;Graphics;
DESKTOP
cat > "$DEB/DEBIAN/control" <<CONTROL
Package: backuplens
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: BackupLens contributors <noreply@users.noreply.github.com>
Depends: libc6, libgcc-s1, libstdc++6
Homepage: https://github.com/tkrishnakanth/backuplens
Description: Local-only browser and exporter for encrypted iOS backups
 BackupLens browses and exports photos/videos from a local iOS backup without
 uploading anything.
CONTROL
cat > "$DEB/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -f /usr/share/icons/hicolor || true
exit 0
POSTINST
chmod 755 "$DEB/DEBIAN/postinst"
dpkg-deb --build "$DEB" "dist/BackupLens-${VERSION}-linux-amd64.deb"

# AppImage (pinned appimagetool and checksum verification)
TOOL="appimagetool-x86_64.AppImage"
URL="https://github.com/AppImage/appimagetool/releases/download/1.9.1/${TOOL}"
EXPECTED="${APPIMAGETOOL_SHA256:-ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0}"
curl -fsSL "$URL" -o "/tmp/${TOOL}"
echo "${EXPECTED}  /tmp/${TOOL}" | sha256sum -c -
chmod +x "/tmp/${TOOL}"
APPDIR="build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/lib/backuplens" "$APPDIR/usr/share/icons/hicolor/256x256/apps" "$APPDIR/usr/share/applications"
cp -R "$APP/." "$APPDIR/usr/lib/backuplens/"
cp packaging/icon/icon-256.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/backuplens.png"
cp "$DEB/usr/share/applications/backuplens.desktop" "$APPDIR/usr/share/applications/backuplens.desktop"
cp "$APPDIR/usr/share/applications/backuplens.desktop" "$APPDIR/backuplens.desktop"
ln -sfn usr/lib/backuplens/BackupLens "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
ARCH=x86_64 "/tmp/${TOOL}" --appimage-extract-and-run "$APPDIR" "dist/BackupLens-${VERSION}-linux-x86_64.AppImage"
"dist/BackupLens-${VERSION}-linux-x86_64.AppImage" --appimage-extract-and-run --smoke-test
