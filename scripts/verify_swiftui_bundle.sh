#!/usr/bin/env bash
set -euo pipefail

# Verify the installable SwiftUI app bundle. This is intentionally stricter
# than "does the directory exist": it checks the Swift executable, embedded
# helper, bundled model, version metadata, and native-library portability.

VERIFY_CODESIGN=0
APP=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --codesign)
      VERIFY_CODESIGN=1
      shift
      ;;
    -*)
      echo "Usage: scripts/verify_swiftui_bundle.sh [--codesign] [path/to/Aside.app]" >&2
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
HELPER_APP="$APP/Contents/Resources/AsideHelper.app"
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

[[ -d "$MODEL_DIR" ]] || fail "bundled faster-whisper model directory missing"
for model_file in model.bin tokenizer.json config.json; do
  [[ -f "$MODEL_DIR/$model_file" ]] || fail "model file missing: $model_file"
done
MODEL_SIZE="$(file_size "$MODEL_DIR/model.bin")"
echo "model.bin size: $MODEL_SIZE bytes"
[[ "$MODEL_SIZE" -gt 100000000 ]] || fail "model.bin is too small; download is likely incomplete"

BAD=0
LIB_ROOT="$HELPER_APP/Contents/Resources/lib"
if [[ -d "$LIB_ROOT" ]]; then
  while IFS= read -r ext; do
    [[ -f "$ext" ]] || continue
    if otool -L "$ext" | tail -n +2 | grep -E '^[[:space:]]+(/opt/homebrew|/usr/local|/Users/runner|/Users/[^[:space:]]+/claude-code)/'; then
      echo "ERROR: native extension links to a non-portable local path: $ext" >&2
      BAD=1
    fi
  done < <(find "$LIB_ROOT" -type f \( -name '*.so' -o -name '*.dylib' \) 2>/dev/null)
fi
[[ "$BAD" == "0" ]] || fail "non-portable native-library link detected"

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
  codesign -dv --entitlements - "$APP" >/dev/null
fi

echo "SwiftUI bundle verification passed."
