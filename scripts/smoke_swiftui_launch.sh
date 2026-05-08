#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ASIDE_PYTHON:-$ROOT/.venv/bin/python3}"
APP="$ROOT/native/AsideShell/.build/debug/AsideShell"
APP_PID=""
SWIFT_BUILD_DIR="native/AsideShell/.build"
CLANG_MODULE_CACHE="$ROOT/native/AsideShell/.build/clang-module-cache"
SWIFT_MODULE_CACHE="$ROOT/native/AsideShell/.build/swift-module-cache"

cleanup() {
  if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Python helper interpreter is missing or not executable: $PYTHON"
  echo "Run ./setup.sh first, or set ASIDE_PYTHON to a project venv Python."
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

echo "==> Launching AsideShell in helper protocol-smoke mode"
ASIDE_REPO_ROOT="$ROOT" \
ASIDE_PYTHON="$PYTHON" \
ASIDE_HELPER_PROTOCOL_SMOKE=1 \
  "$APP" &
APP_PID="$!"

sleep 5

if ! kill -0 "$APP_PID" 2>/dev/null; then
  echo "ERROR: AsideShell exited before the launch smoke window."
  wait "$APP_PID"
fi

HELPER_PID="$(pgrep -P "$APP_PID" -f 'python.*aside.helper' | head -n 1 || true)"
if [[ -z "$HELPER_PID" ]]; then
  echo "ERROR: AsideShell is running, but no child aside.helper process was found."
  exit 1
fi

echo "Launch smoke passed: AsideShell pid=$APP_PID helper pid=$HELPER_PID"
