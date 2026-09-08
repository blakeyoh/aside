#!/usr/bin/env bash
set -euo pipefail

# Verify the installable SwiftUI app bundle. This is intentionally stricter
# than "does the directory exist": it checks the Swift executable, embedded
# helper, bundled model, version metadata, and native-library portability.

VERIFY_CODESIGN=0
VERIFY_DISTRIBUTION=0
APP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codesign)
      VERIFY_CODESIGN=1
      shift
      ;;
    --distribution)
      VERIFY_CODESIGN=1
      VERIFY_DISTRIBUTION=1
      shift
      ;;
    -*)
      echo "Usage: scripts/verify_swiftui_bundle.sh [--codesign|--distribution] [path/to/Aside.app]" >&2
      exit 1
      ;;
    *)
      APP="$1"
      shift
      ;;
  esac
done

APP="${APP:-dist-swiftui/Aside.app}"
PLIST_BUDDY="/usr/libexec/PlistBuddy"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

file_size() {
  if stat -f%z "$1" >/dev/null 2>&1; then
    stat -f%z "$1"
  else
    wc -c < "$1" | tr -d ' '
  fi
}

plist_value() {
  "$PLIST_BUDDY" -c "Print :$2" "$1"
}

EXPECTED_VERSION="${EXPECTED_VERSION:-$(python3 -c "import sys; sys.path.insert(0,'src'); from aside import __version__; print(__version__)")}"
HELPER_APP="$APP/Contents/Helpers/AsideHelper.app"
MODEL_DIR="$HELPER_APP/Contents/Resources/faster-whisper-base"

echo "==> Verifying SwiftUI bundle: $APP"

[[ -d "$APP" ]] || fail "app bundle missing: $APP"
[[ -f "$APP/Contents/Info.plist" ]] || fail "Info.plist missing"
[[ -x "$APP/Contents/MacOS/Aside" ]] || fail "SwiftUI executable missing or not executable"
[[ -f "$APP/Contents/Resources/AppIcon.icns" ]] || fail "AppIcon.icns missing"
[[ -f "$APP/Contents/Resources/NEW-aside-logo.png" ]] || fail "SwiftUI logo asset missing"

[[ "$(plist_value "$APP/Contents/Info.plist" CFBundleExecutable)" == "Aside" ]] || fail "CFBundleExecutable is not Aside"
[[ "$(plist_value "$APP/Contents/Info.plist" CFBundleIdentifier)" == "com.blakeyoh.aside" ]] || fail "unexpected CFBundleIdentifier"
[[ "$(plist_value "$APP/Contents/Info.plist" CFBundleShortVersionString)" == "$EXPECTED_VERSION" ]] || fail "version mismatch"
[[ "$(plist_value "$APP/Contents/Info.plist" LSMinimumSystemVersion)" == "13.0" ]] || fail "SwiftUI app must require macOS 13.0"
[[ "$(plist_value "$APP/Contents/Info.plist" LSUIElement)" == "false" ]] || fail "SwiftUI app must be a regular visible app"

if command -v lipo >/dev/null 2>&1; then
  ARCHS="$(lipo -archs "$APP/Contents/MacOS/Aside")"
  echo "SwiftUI executable archs: $ARCHS"
  [[ "$ARCHS" == "arm64" ]] || fail "SwiftUI executable must be arm64-only"
fi

[[ -d "$HELPER_APP" ]] || fail "embedded AsideHelper.app missing"
[[ -f "$HELPER_APP/Contents/Info.plist" ]] || fail "helper Info.plist missing"
[[ -x "$HELPER_APP/Contents/MacOS/AsideHelper" ]] || fail "helper executable missing or not executable"
[[ "$(plist_value "$HELPER_APP/Contents/Info.plist" CFBundleExecutable)" == "AsideHelper" ]] || fail "helper CFBundleExecutable is not AsideHelper"
[[ "$(plist_value "$HELPER_APP/Contents/Info.plist" CFBundleIdentifier)" == "com.blakeyoh.aside.helper" ]] || fail "unexpected helper CFBundleIdentifier"
[[ "$(plist_value "$HELPER_APP/Contents/Info.plist" CFBundleDisplayName)" == "Aside" ]] || fail "helper user-facing display name must be Aside"
[[ "$(plist_value "$HELPER_APP/Contents/Info.plist" CFBundleShortVersionString)" == "$EXPECTED_VERSION" ]] || fail "helper version mismatch"
[[ "$(plist_value "$HELPER_APP/Contents/Info.plist" LSMinimumSystemVersion)" == "13.0" ]] || fail "helper must require macOS 13.0"

[[ -d "$MODEL_DIR" ]] || fail "bundled faster-whisper model directory missing"
for model_file in model.bin tokenizer.json config.json; do
  [[ -f "$MODEL_DIR/$model_file" ]] || fail "model file missing: $model_file"
done
MODEL_SIZE="$(file_size "$MODEL_DIR/model.bin")"
echo "model.bin size: $MODEL_SIZE bytes"
[[ "$MODEL_SIZE" -gt 100000000 ]] || fail "model.bin is too small; download is likely incomplete"

BAD=0
MACHO_COUNT=0
while IFS= read -r -d '' native_file; do
  if ! file -b "$native_file" | grep -q 'Mach-O'; then
    continue
  fi

  MACHO_COUNT=$((MACHO_COUNT + 1))
  if command -v lipo >/dev/null 2>&1; then
    NATIVE_ARCHS="$(lipo -archs "$native_file")"
    if [[ " $NATIVE_ARCHS " != *" arm64 "* ]]; then
      echo "ERROR: nested Mach-O has no arm64 slice: $native_file ($NATIVE_ARCHS)" >&2
      BAD=1
    fi
  fi

  if otool -L "$native_file" | tail -n +2 | \
      grep -E '^[[:space:]]+(/opt/homebrew|/usr/local|/Users/runner|/Users/[^[:space:]]+/claude-code)/'; then
    echo "ERROR: nested Mach-O links to a non-portable local path: $native_file" >&2
    BAD=1
  fi
done < <(find "$HELPER_APP" -type f -print0 2>/dev/null)
echo "Nested helper Mach-O files: $MACHO_COUNT"
[[ "$MACHO_COUNT" -gt 0 ]] || fail "embedded helper contains no Mach-O code"
[[ "$BAD" == "0" ]] || fail "non-portable nested Mach-O detected"

while IFS= read -r link_path; do
  target="$(readlink "$link_path")"
  case "$target" in
    /opt/homebrew/*|/usr/local/*|/Users/runner/*|/Users/*/claude-code/*)
      fail "bundle contains absolute symlink to local build machine: $link_path -> $target"
      ;;
  esac
done < <(find "$APP" -type l 2>/dev/null)

if [[ "$VERIFY_CODESIGN" == "1" ]]; then
  codesign --verify --deep --strict --verbose=2 "$APP"
fi

if [[ "$VERIFY_DISTRIBUTION" == "1" ]]; then
  verify_distribution_signature() {
    local path="$1"
    local label="$2"
    local details
    details="$(codesign --display --verbose=2 "$path" 2>&1)"
    grep -q '^Authority=Developer ID Application:' <<<"$details" || \
      fail "$label is not signed with Developer ID Application"
    grep -Eq '^TeamIdentifier=[A-Z0-9]+$' <<<"$details" || \
      fail "$label has no valid TeamIdentifier"
    grep -Eq '^CodeDirectory .*flags=.*\(runtime\)' <<<"$details" || \
      fail "$label does not enable hardened runtime"
  }

  verify_distribution_signature "$HELPER_APP" "helper"
  verify_distribution_signature "$APP" "main app"

  ENTITLEMENTS_DIR="$(mktemp -d)"
  trap 'rm -rf "$ENTITLEMENTS_DIR"' EXIT
  codesign --display --entitlements "$ENTITLEMENTS_DIR/main.plist" --xml "$APP" 2>/dev/null
  codesign --display --entitlements "$ENTITLEMENTS_DIR/helper.plist" --xml "$HELPER_APP" 2>/dev/null
  python3 - "$ENTITLEMENTS_DIR/main.plist" "$ENTITLEMENTS_DIR/helper.plist" <<'PY'
import plistlib
import sys

with open(sys.argv[1], "rb") as handle:
    main = plistlib.load(handle)
with open(sys.argv[2], "rb") as handle:
    helper = plistlib.load(handle)

expected_helper = {
    "com.apple.security.cs.allow-unsigned-executable-memory": True,
    "com.apple.security.device.audio-input": True,
}
if main:
    raise SystemExit(f"main app has unexpected entitlements: {sorted(main)}")
if helper != expected_helper:
    raise SystemExit(
        "helper entitlements differ from the reviewed minimum: "
        f"{sorted(helper)}"
    )
PY
fi

echo "SwiftUI bundle verification passed."
