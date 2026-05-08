#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ASIDE_PYTHON:-$ROOT/.venv/bin/python3}"
SWIFT_BUILD_DIR="native/AsideShell/.build"
CLANG_MODULE_CACHE="$ROOT/native/AsideShell/.build/clang-module-cache"
SWIFT_MODULE_CACHE="$ROOT/native/AsideShell/.build/swift-module-cache"

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Python helper interpreter is missing or not executable: $PYTHON"
  echo ""
  echo "Run ./setup.sh first, or set ASIDE_PYTHON to a project venv Python."
  exit 1
fi

if ! command -v swift >/dev/null 2>&1; then
  echo "ERROR: swift is not on PATH. Install Xcode or Command Line Tools."
  exit 1
fi

echo "==> Building SwiftUI spike shell"
cd "$ROOT"
env \
  CLANG_MODULE_CACHE_PATH="$CLANG_MODULE_CACHE" \
  SWIFTPM_MODULECACHE_OVERRIDE="$SWIFT_MODULE_CACHE" \
  swift build \
    --package-path native/AsideShell \
    --scratch-path "$SWIFT_BUILD_DIR"

echo "==> Launching AsideShell"
echo "    ASIDE_REPO_ROOT=$ROOT"
echo "    ASIDE_PYTHON=$PYTHON"
ASIDE_REPO_ROOT="$ROOT" ASIDE_PYTHON="$PYTHON" \
  "$ROOT/native/AsideShell/.build/debug/AsideShell"
