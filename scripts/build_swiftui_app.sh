#!/usr/bin/env bash
set -euo pipefail

# Build a distributable SwiftUI Aside.app bundle.
#
# Output:
#   dist-swiftui/Aside.app
#
# The app bundle uses the SwiftUI shell as the main executable and embeds a
# py2app-built Python helper at Contents/Resources/AsideHelper.app.

MODE="${1:-release}"

if [[ "$MODE" != "release" ]]; then
  echo "Usage: scripts/build_swiftui_app.sh release"
  exit 1
fi

if [[ ! -f "native/AsideShell/Package.swift" || ! -f "setup_py2app_helper.py" ]]; then
  echo "Run this script from the repository root."
  exit 1
fi

if [[ -z "${MODEL_REVISION:-}" ]]; then
  echo "ERROR: MODEL_REVISION is unset or empty."
  echo "       SwiftUI release builds require a 40-char Hugging Face commit SHA."
  exit 1
fi

if [[ ! "$MODEL_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "ERROR: MODEL_REVISION is set but not a 40-char commit SHA."
  echo "       Current value: '${MODEL_REVISION}'"
  exit 1
fi

if ! command -v swift >/dev/null 2>&1; then
  echo "ERROR: swift is not on PATH. Install Xcode or Command Line Tools."
  exit 1
fi

if ! command -v python >/dev/null 2>&1; then
  echo "ERROR: python is not on PATH."
  exit 1
fi

PYTHON_EXE="$(command -v python)"
if [[ ! "$PYTHON_EXE" =~ \.venv/bin/python$ ]]; then
  echo "ERROR: build_swiftui_app.sh expects the project venv on PATH, got: $PYTHON_EXE"
  echo "Activate it first: source .venv/bin/activate"
  exit 1
fi

for required_file in Info.plist assets/NEW-AppIcon.icns entitlements.plist assets/NEW-aside-logo.png; do
  if [[ ! -f "$required_file" ]]; then
    echo "ERROR: required packaging input is missing: $required_file"
    exit 1
  fi
done

if ! python -c "import huggingface_hub, py2app" >/dev/null 2>&1; then
  echo "ERROR: build toolchain missing from venv (huggingface_hub or py2app)."
  exit 1
fi

echo "==> Verifying SwiftUI helper input modules are importable"
python - <<'PY'
import sys
mods = [
    ("aside", "aside"),
    ("faster_whisper", "faster-whisper"),
    ("ctranslate2", "ctranslate2"),
    ("tokenizers", "tokenizers"),
    ("huggingface_hub", "huggingface_hub"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
    ("Quartz", "pyobjc-framework-Quartz"),
    ("AppKit", "pyobjc-framework-Cocoa"),
    ("AVFoundation", "pyobjc-framework-AVFoundation"),
    ("ApplicationServices", "pyobjc-framework-ApplicationServices"),
]
failed = []
for module, package in mods:
    try:
        __import__(module)
    except Exception as exc:
        failed.append((module, package, exc))
if failed:
    print("ERROR: helper input modules failed to import:", file=sys.stderr)
    for module, package, exc in failed:
        print(f"  - {package}: import {module} failed: {exc}", file=sys.stderr)
    sys.exit(1)
print("All SwiftUI helper input modules importable.")
PY

echo "==> Cleaning SwiftUI build artifacts"
rm -rf build dist/AsideHelper.app dist-swiftui

echo "==> Prefetching Systran/faster-whisper-base model into vendor/"
python - "$MODEL_REVISION" <<'PY'
import sys
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Systran/faster-whisper-base",
    revision=sys.argv[1],
    local_dir="vendor/models/faster-whisper-base",
)
print("Model snapshot ready at vendor/models/faster-whisper-base")
PY

SWIFT_BUILD_DIR="native/AsideShell/.build"
CLANG_MODULE_CACHE="$PWD/native/AsideShell/.build/clang-module-cache"
SWIFT_MODULE_CACHE="$PWD/native/AsideShell/.build/swift-module-cache"

echo "==> Building SwiftUI shell"
env \
  CLANG_MODULE_CACHE_PATH="$CLANG_MODULE_CACHE" \
  SWIFTPM_MODULECACHE_OVERRIDE="$SWIFT_MODULE_CACHE" \
  swift build \
    --configuration release \
    --package-path native/AsideShell \
    --scratch-path "$SWIFT_BUILD_DIR"

echo "==> Building bundled Python helper"
python setup_py2app_helper.py py2app

HELPER_APP="dist/AsideHelper.app"
SWIFT_EXE="native/AsideShell/.build/release/AsideShell"
APP="dist-swiftui/Aside.app"

test -x "$SWIFT_EXE"
test -x "$HELPER_APP/Contents/MacOS/AsideHelper"

echo "==> Assembling $APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp Info.plist "$APP/Contents/Info.plist"
cp "$SWIFT_EXE" "$APP/Contents/MacOS/Aside"
cp assets/NEW-AppIcon.icns "$APP/Contents/Resources/AppIcon.icns"
cp assets/NEW-aside-logo.png "$APP/Contents/Resources/NEW-aside-logo.png"
cp -R "$HELPER_APP" "$APP/Contents/Resources/AsideHelper.app"
printf "APPL????" > "$APP/Contents/PkgInfo"
chmod +x "$APP/Contents/MacOS/Aside"

echo "==> Verifying SwiftUI bundle structure"
test -f "$APP/Contents/Info.plist"
test -x "$APP/Contents/MacOS/Aside"
test -f "$APP/Contents/Resources/AppIcon.icns"
test -f "$APP/Contents/Resources/NEW-aside-logo.png"
test -x "$APP/Contents/Resources/AsideHelper.app/Contents/MacOS/AsideHelper"
test -f "$APP/Contents/Resources/AsideHelper.app/Contents/Resources/faster-whisper-base/model.bin"

echo "==> Build complete"
echo "App bundle: $APP"
