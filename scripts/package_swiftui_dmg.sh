#!/usr/bin/env bash
set -euo pipefail

# Package a Developer ID-signed native app into a signed SwiftUI DMG.

IDENTITY="${1:-}"

if [[ -z "$IDENTITY" || "$IDENTITY" == "-" ]]; then
  echo "Usage: scripts/package_swiftui_dmg.sh \"Developer ID Application: Name (TEAMID)\"" >&2
  echo "A real Developer ID identity is required; ad-hoc release DMGs are not allowed." >&2
  exit 1
fi

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

echo "==> Verifying Developer ID-signed app"
scripts/verify_swiftui_bundle.sh --distribution dist-swiftui/Aside.app

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

echo "==> Developer ID-signing ${DMG_PATH}"
codesign --force --timestamp --sign "$IDENTITY" "$DMG_PATH"
codesign --verify --verbose=2 "$DMG_PATH"

echo "==> Done: ${DMG_PATH}"
