#!/usr/bin/env bash
set -euo pipefail

# Package dist/Aside.app into a distributable DMG.
#
# Usage:
#   scripts/package_dmg.sh
#
# Prerequisites:
#   - dist/Aside.app must exist  (run: scripts/build_app.sh release)
#   - create-dmg on PATH         (install: brew install create-dmg)

if [[ ! -f "setup_py2app.py" ]]; then
  echo "Run this script from the repository root."
  exit 1
fi

if [[ ! -d "dist/Aside.app" ]]; then
  echo "dist/Aside.app not found — run scripts/build_app.sh release first."
  exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "create-dmg not found — install with: brew install create-dmg"
  exit 1
fi

VERSION=$(python3 -c \
  "import sys; sys.path.insert(0,'src'); from aside import __version__; print(__version__)")
DMG_PATH="dist/Aside-${VERSION}.dmg"

# Remove stale artifact so create-dmg does not fail on re-runs
rm -f "${DMG_PATH}"

echo "==> Ad-hoc codesigning dist/Aside.app"
# Uses ad-hoc identity (-): allows right-click → Open to bypass Gatekeeper.
# For Developer ID signing, replace - with your certificate identity string.
codesign --deep --force --sign - --entitlements entitlements.plist dist/Aside.app

echo "==> Creating ${DMG_PATH}"
create-dmg \
  --volname "Aside" \
  --window-pos 200 120 \
  --window-size 660 400 \
  --icon-size 100 \
  --icon "Aside.app" 180 185 \
  --hide-extension "Aside.app" \
  --app-drop-link 480 185 \
  "${DMG_PATH}" \
  "dist/Aside.app"

echo "==> Done: ${DMG_PATH}"
