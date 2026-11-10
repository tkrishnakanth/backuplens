#!/usr/bin/env bash
# Build and package the macOS app on a GitHub macOS runner.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
VERSION="$(python -c 'from backend.version import VERSION; print(VERSION)')"
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging/backuplens.spec
APP="dist/BackupLens.app"
if [ ! -d "$APP" ]; then
  echo "BackupLens.app not produced" >&2
  exit 1
fi
# Ad-hoc signing is the minimum on Apple Silicon; real signing is optional and gated by secrets.
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
cp THIRD_PARTY_NOTICES.txt LICENSE "$APP/Contents/Resources/" 2>/dev/null || true
mkdir -p dist/macos
ditto -c -k --keepParent "$APP" "dist/macos/BackupLens-${VERSION}-macos-$(uname -m).zip"
mkdir -p dist/dmg
cp -R "$APP" dist/dmg/
ln -sfn /Applications dist/dmg/Applications
hdiutil create -volname "BackupLens ${VERSION}" -srcfolder dist/dmg -ov -format UDZO \
  "dist/BackupLens-${VERSION}-macos-$(uname -m).dmg"
"$APP/Contents/MacOS/BackupLens" --smoke-test
