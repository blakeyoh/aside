#!/usr/bin/env bash
set -euo pipefail

# Build Aside.app with py2app and prefetch bundled Whisper model.
#
# Usage:
#   scripts/build_app.sh dev      # py2app alias mode (-A)
#   scripts/build_app.sh release  # full bundle build

# Pin to a specific HuggingFace commit for reproducible builds.
# To update: git ls-remote https://huggingface.co/Systran/faster-whisper-base main
# Replace "main" with the full commit SHA before tagging a release.
MODEL_REVISION="main"

MODE="${1:-release}"

if [[ "$MODE" != "dev" && "$MODE" != "release" ]]; then
  echo "Usage: scripts/build_app.sh [dev|release]"
  exit 1
fi

if [[ ! -f "setup_py2app.py" ]]; then
  echo "Run this script from the repository root."
  exit 1
fi

if ! command -v python >/dev/null 2>&1; then
  echo "python not found on PATH"
  exit 1
fi

echo "==> Cleaning old build artifacts"
rm -rf build dist

echo "==> Prefetching Systran/faster-whisper-base model into vendor/"
python - "$MODEL_REVISION" <<'PY'
import sys
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="Systran/faster-whisper-base",
    revision=sys.argv[1],
    local_dir="vendor/models/faster-whisper-base",
    local_dir_use_symlinks=False,
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
