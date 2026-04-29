#!/usr/bin/env bash
set -euo pipefail

# Build Aside.app with py2app and prefetch bundled Whisper model.
#
# Usage:
#   scripts/build_app.sh dev      # py2app alias mode (-A)
#   scripts/build_app.sh release  # full bundle build
#
# MODEL_REVISION pins the HuggingFace snapshot of the bundled Whisper model
# so two runs of the same tagged release package identical bytes. Override
# from the caller (release workflow / local build) with a real commit SHA:
#
#   MODEL_REVISION=<40-char-hex-sha> scripts/build_app.sh release
#
# Look up the current SHA with:
#   git ls-remote https://huggingface.co/Systran/faster-whisper-base main
#
# Release builds reject "main" / non-SHA values to guarantee reproducibility.
MODEL_REVISION="${MODEL_REVISION:-main}"

MODE="${1:-release}"

if [[ "$MODE" != "dev" && "$MODE" != "release" ]]; then
  echo "Usage: scripts/build_app.sh [dev|release]"
  exit 1
fi

# Release artifacts must be reproducible — refuse to build against a
# moving branch. Dev builds may use "main" for fast iteration.
if [[ "$MODE" == "release" ]]; then
  if [[ ! "$MODEL_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
    echo "ERROR: release builds require MODEL_REVISION pinned to a 40-char commit SHA."
    echo "       Current value: '${MODEL_REVISION}'"
    echo ""
    echo "Look up the latest SHA:"
    echo "  git ls-remote https://huggingface.co/Systran/faster-whisper-base main"
    echo ""
    echo "Then re-run:"
    echo "  MODEL_REVISION=<sha> scripts/build_app.sh release"
    exit 1
  fi
fi

if [[ ! -f "setup_py2app.py" ]]; then
  echo "Run this script from the repository root."
  exit 1
fi

for required_file in Info.plist AppIcon.icns aside-logo.png entitlements.plist; do
  if [[ ! -f "$required_file" ]]; then
    echo "ERROR: required packaging input is missing: $required_file"
    exit 1
  fi
done

if ! command -v python >/dev/null 2>&1; then
  echo "python not found on PATH"
  exit 1
fi

# Preflight: verify the active python is the project venv with the build
# toolchain installed. The user may have been bounced to system Python
# (anaconda, /usr/bin/python3) which is missing huggingface_hub / py2app
# and silently produces confusing failures hundreds of lines later.
PYTHON_EXE="$(command -v python)"
if [[ ! "$PYTHON_EXE" =~ \.venv/bin/python$ ]]; then
  echo "ERROR: build_app.sh expects the project venv on PATH, got: $PYTHON_EXE"
  echo ""
  echo "Activate it first:"
  echo "  source .venv/bin/activate"
  echo ""
  echo "If .venv is missing, run ./setup.sh first."
  exit 1
fi

if ! python -c "import huggingface_hub, py2app" >/dev/null 2>&1; then
  echo "ERROR: build toolchain missing from venv (huggingface_hub or py2app)."
  echo ""
  echo "Re-run ./setup.sh to install the toolchain, or manually:"
  echo "  pip install 'setuptools<70' wheel 'py2app==0.28.10' 'huggingface_hub>=0.20'"
  exit 1
fi

# Verify every package py2app will be asked to bundle is importable in this
# venv, BEFORE py2app starts churning. py2app failures are slow, noisy, and
# rarely point at the actual missing dep. Catching it here means one clear
# error line instead of a 200-line traceback.
echo "==> Verifying py2app input modules are importable"
python - <<'PY'
import sys
mods = [
    ("aside",          "aside"),
    ("faster_whisper", "faster-whisper"),
    ("ctranslate2",    "ctranslate2"),
    ("tokenizers",     "tokenizers"),
    ("huggingface_hub","huggingface_hub"),
    ("customtkinter",  "customtkinter"),
    ("PIL",            "pillow"),
    ("sounddevice",    "sounddevice"),
    ("numpy",          "numpy"),
    ("Quartz",         "pyobjc-framework-Quartz"),
    ("AppKit",         "pyobjc-framework-Cocoa"),
    ("AVFoundation",   "pyobjc-framework-AVFoundation"),
    ("ApplicationServices", "pyobjc-framework-ApplicationServices"),
    ("tkinter",        "python-tk@3.13 (Homebrew)"),
]
failed = []
for module, package in mods:
    try:
        __import__(module)
    except Exception as exc:
        failed.append((module, package, exc))
if failed:
    print("ERROR: py2app input modules failed to import:", file=sys.stderr)
    for module, package, exc in failed:
        print(f"  - {package}: import {module} failed: {exc}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Fix the venv (re-run ./setup.sh or pip install the missing package)", file=sys.stderr)
    print("before invoking build_app.sh again.", file=sys.stderr)
    sys.exit(1)
print("All py2app input modules importable.")
PY

echo "==> Cleaning old build artifacts"
if ! rm -rf build dist .eggs; then
  # Finder can leave hidden .DS_Store metadata inside dist/ after a bundle
  # has been opened. Clear generated Finder metadata and retry once.
  find build dist .eggs -name .DS_Store -delete 2>/dev/null || true
  rm -rf build dist .eggs
fi

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

if [[ "$MODE" == "dev" ]]; then
  echo "==> Building alias app (py2app -A)"
  python setup_py2app.py py2app -A
else
  echo "==> Building release app (py2app)"
  python setup_py2app.py py2app
fi

echo "==> Build complete"
echo "App bundle: dist/Aside.app"

echo "==> Optional dylib audit command"
echo "otool -L dist/Aside.app/Contents/Resources/lib/python*/ctranslate2/_ext*.so"
