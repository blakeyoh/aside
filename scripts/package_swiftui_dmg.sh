#!/usr/bin/env bash
set -euo pipefail

# Package dist-swiftui/Aside.app into a distributable SwiftUI DMG.

if [[ ! -d "dist-swiftui/Aside.app" ]]; then
  echo "dist-swiftui/Aside.app not found — run scripts/build_swiftui_app.sh release first."
  exit 1
fi

if ! command -v create-dmg >/dev/null 2>&1; then
  echo "create-dmg not found — run ./setup.sh or install with: brew install create-dmg"
  exit 1
fi

VERSION=$(python3 -c \
  "import sys; sys.path.insert(0,'src'); from aside import __version__; print(__version__)")
DMG_PATH="dist-swiftui/Aside-SwiftUI-${VERSION}.dmg"

rm -f "$DMG_PATH"

if codesign -dv dist-swiftui/Aside.app 2>&1 | grep -q "^Authority="; then
  echo "==> Preserving existing Developer ID signature"
else
  echo "==> Ad-hoc codesigning dist-swiftui/Aside.app"
  codesign --deep --force --sign - --entitlements entitlements.plist dist-swiftui/Aside.app
fi

echo "==> Verifying codesign"
codesign --verify --deep --strict --verbose=2 dist-swiftui/Aside.app

STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT
cp -R "dist-swiftui/Aside.app" "$STAGING/"

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
