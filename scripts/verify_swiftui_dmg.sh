#!/usr/bin/env bash
set -euo pipefail

VERIFY_FLAG="--codesign"
COPY_TO=""
DMG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --distribution)
      VERIFY_FLAG="--distribution"
      shift
      ;;
    --copy-to)
      COPY_TO="${2:-}"
      [[ -n "$COPY_TO" ]] || {
        echo "ERROR: --copy-to requires a directory" >&2
        exit 1
      }
      shift 2
      ;;
    -*)
      echo "Usage: scripts/verify_swiftui_dmg.sh [--distribution] [--copy-to DIR] path/to/Aside.dmg" >&2
      exit 1
      ;;
    *)
      DMG="$1"
      shift
      ;;
  esac
done

[[ -n "$DMG" && -f "$DMG" ]] || {
  echo "ERROR: DMG not found: $DMG" >&2
  exit 1
}

hdiutil verify "$DMG"
MOUNT_DIR="$(mktemp -d)"

cleanup() {
  hdiutil detach "$MOUNT_DIR" >/dev/null 2>&1 || true
  rmdir "$MOUNT_DIR" >/dev/null 2>&1 || true
}
trap cleanup EXIT

hdiutil attach "$DMG" -nobrowse -readonly -mountpoint "$MOUNT_DIR" >/dev/null
MOUNTED_APP="$MOUNT_DIR/Aside.app"
[[ -d "$MOUNTED_APP" ]] || {
  echo "ERROR: Aside.app missing from DMG root" >&2
  exit 1
}

scripts/verify_swiftui_bundle.sh "$VERIFY_FLAG" "$MOUNTED_APP"

if [[ "$VERIFY_FLAG" == "--distribution" ]]; then
  codesign --verify --verbose=2 "$DMG"
  xcrun stapler validate "$DMG"
  spctl --assess --type open --context context:primary-signature --verbose=4 "$DMG"
  spctl --assess --type execute --verbose=4 "$MOUNTED_APP"
fi

if [[ -n "$COPY_TO" ]]; then
  mkdir -p "$COPY_TO"
  INSTALLED_APP="$COPY_TO/Aside.app"
  [[ ! -e "$INSTALLED_APP" ]] || {
    echo "ERROR: copy target already exists: $INSTALLED_APP" >&2
    exit 1
  }
  ditto "$MOUNTED_APP" "$INSTALLED_APP"
  scripts/verify_swiftui_bundle.sh "$VERIFY_FLAG" "$INSTALLED_APP"
  echo "Installed app copy: $INSTALLED_APP"
fi

echo "SwiftUI DMG verification passed: $DMG"
