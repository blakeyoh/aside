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
  echo "create-dmg not found — run ./setup.sh or install with: brew install create-dmg"
  exit 1
fi

VERSION=$(python3 -c \
  "import sys; sys.path.insert(0,'src'); from aside import __version__; print(__version__)")
DMG_PATH="dist/Aside-${VERSION}.dmg"

# Remove stale artifact so create-dmg does not fail on re-runs
rm -f "${DMG_PATH}"

# Only apply ad-hoc signature when the app has not already been signed with a
# real Developer ID (Authority= is absent for ad-hoc and unsigned apps).
# This preserves any upstream Developer ID + notarization done in CI.
if codesign -dv dist/Aside.app 2>&1 | grep -q "^Authority="; then
  echo "==> Preserving existing Developer ID signature"
else
  echo "==> Ad-hoc codesigning dist/Aside.app (no real identity present)"
  codesign --deep --force --sign - --entitlements entitlements-helper.plist dist/Aside.app
fi

# create-dmg copies the *contents* of its source folder into the DMG root,
# so Aside.app must live inside a staging directory — not be the source itself.
STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
cp -r "dist/Aside.app" "$STAGING/"

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
  "${STAGING}"

echo "==> Done: ${DMG_PATH}"
