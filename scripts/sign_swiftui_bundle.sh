#!/usr/bin/env bash
set -euo pipefail

# Developer ID-sign the native app from the innermost Mach-O outward.
# Usage: scripts/sign_swiftui_bundle.sh "Developer ID Application: Name (TEAMID)" [Aside.app]

IDENTITY="${1:-}"
APP="${2:-dist-swiftui/Aside.app}"
MAIN_ENTITLEMENTS="${MAIN_ENTITLEMENTS:-entitlements-main.plist}"
HELPER_ENTITLEMENTS="${HELPER_ENTITLEMENTS:-entitlements-helper.plist}"
HELPER_APP="$APP/Contents/Helpers/AsideHelper.app"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ -n "$IDENTITY" ]] || fail "Developer ID identity is required"
[[ "$IDENTITY" != "-" ]] || fail "ad-hoc signing is not allowed for distribution"
[[ -d "$APP" ]] || fail "app bundle missing: $APP"
[[ -d "$HELPER_APP" ]] || fail "embedded helper missing: $HELPER_APP"
[[ -f "$MAIN_ENTITLEMENTS" ]] || fail "main entitlements missing: $MAIN_ENTITLEMENTS"
[[ -f "$HELPER_ENTITLEMENTS" ]] || fail "helper entitlements missing: $HELPER_ENTITLEMENTS"

plutil -lint "$MAIN_ENTITLEMENTS" "$HELPER_ENTITLEMENTS" >/dev/null

IDENTITY_LINE="$(security find-identity -v -p codesigning | grep -F -- "$IDENTITY" | head -1 || true)"
[[ "$IDENTITY_LINE" == *"Developer ID Application:"* ]] || \
  fail "identity is not an available Developer ID Application certificate: $IDENTITY"

sign_code() {
  local path="$1"
  echo "==> Signing nested code: $path"
  codesign --force --timestamp --options runtime --sign "$IDENTITY" "$path"
}

# py2app places extension modules and native libraries throughout the helper.
# Sign every real Mach-O file before signing framework and app containers.
while IFS= read -r -d '' candidate; do
  if file -b "$candidate" | grep -q 'Mach-O'; then
    sign_code "$candidate"
  fi
done < <(
  python3 - "$HELPER_APP" <<'PY'
import os
import sys

root = sys.argv[1]
paths = []
for current_root, _, files in os.walk(root, followlinks=False):
    for name in files:
        path = os.path.join(current_root, name)
        if not os.path.islink(path):
            paths.append(path)
for path in sorted(paths, key=lambda value: (value.count(os.sep), value), reverse=True):
    sys.stdout.buffer.write(os.fsencode(path) + b"\0")
PY
)

# Framework containers must follow their binaries and precede their host app.
while IFS= read -r -d '' framework; do
  sign_code "$framework"
done < <(
  python3 - "$HELPER_APP" <<'PY'
import os
import sys

root = sys.argv[1]
paths = []
for current_root, directories, _ in os.walk(root, followlinks=False):
    for name in directories:
        if name.endswith(".framework"):
            paths.append(os.path.join(current_root, name))
for path in sorted(paths, key=lambda value: (value.count(os.sep), value), reverse=True):
    sys.stdout.buffer.write(os.fsencode(path) + b"\0")
PY
)

echo "==> Signing helper app with helper-only entitlements"
codesign --force --timestamp --options runtime --sign "$IDENTITY" \
  --entitlements "$HELPER_ENTITLEMENTS" "$HELPER_APP"

echo "==> Signing outer SwiftUI app with main-process entitlements"
codesign --force --timestamp --options runtime --sign "$IDENTITY" \
  --entitlements "$MAIN_ENTITLEMENTS" "$APP"

echo "==> Verifying Developer ID distribution signature"
scripts/verify_swiftui_bundle.sh --distribution "$APP"
