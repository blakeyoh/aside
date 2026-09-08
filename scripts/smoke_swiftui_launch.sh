#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ASIDE_PYTHON:-$ROOT/.venv/bin/python3}"
APP_BUNDLE=""
APP_PID=""
LOG_PATH="${ASIDE_SWIFTUI_SMOKE_LOG:-$ROOT/swiftui-launch.log}"
TIMEOUT_SECONDS="${ASIDE_SWIFTUI_SMOKE_TIMEOUT:-30}"
SWIFT_BUILD_DIR="native/AsideShell/.build"
CLANG_MODULE_CACHE="$ROOT/native/AsideShell/.build/clang-module-cache"
SWIFT_MODULE_CACHE="$ROOT/native/AsideShell/.build/swift-module-cache"
DEV_APP="$ROOT/dist-swiftui-dev/Aside.app"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --app)
      APP_BUNDLE="${2:-}"
      if [[ -z "$APP_BUNDLE" ]]; then
        echo "ERROR: --app requires a path to Aside.app" >&2
        exit 1
      fi
      APP_BUNDLE="$(cd "$(dirname "$APP_BUNDLE")" && pwd)/$(basename "$APP_BUNDLE")"
      shift 2
      ;;
    *)
      echo "Usage: scripts/smoke_swiftui_launch.sh [--app path/to/Aside.app]" >&2
      exit 1
      ;;
  esac
done

cleanup() {
  if [[ -n "$APP_PID" ]] && kill -0 "$APP_PID" 2>/dev/null; then
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
  fi
  if [[ -n "${APP_EXECUTABLE:-}" ]]; then
    pkill -f "$APP_EXECUTABLE" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [[ -z "$APP_BUNDLE" && ! -x "$PYTHON" ]]; then
  echo "ERROR: Python helper interpreter is missing or not executable: $PYTHON"
  echo "Run ./setup.sh first, or set ASIDE_PYTHON to a project venv Python."
  exit 1
fi

cd "$ROOT"

if [[ -n "$APP_BUNDLE" ]]; then
  APP_EXECUTABLE="$APP_BUNDLE/Contents/MacOS/Aside"
  if [[ ! -x "$APP_EXECUTABLE" ]]; then
    echo "ERROR: bundled SwiftUI executable missing or not executable: $APP_EXECUTABLE" >&2
    exit 1
  fi
else
  echo "==> Building SwiftUI spike shell"
  env \
    CLANG_MODULE_CACHE_PATH="$CLANG_MODULE_CACHE" \
    SWIFTPM_MODULECACHE_OVERRIDE="$SWIFT_MODULE_CACHE" \
    swift build \
      --package-path native/AsideShell \
      --scratch-path "$SWIFT_BUILD_DIR"
  APP_BUNDLE="$DEV_APP"
  APP_EXECUTABLE="$APP_BUNDLE/Contents/MacOS/Aside"
  rm -rf "$ROOT/dist-swiftui-dev"
  mkdir -p "$APP_BUNDLE/Contents/MacOS" "$APP_BUNDLE/Contents/Resources"
  cp "$ROOT/Info.plist" "$APP_BUNDLE/Contents/Info.plist"
  cp "$ROOT/native/AsideShell/.build/debug/AsideShell" "$APP_EXECUTABLE"
  cp "$ROOT/assets/NEW-AppIcon.icns" "$APP_BUNDLE/Contents/Resources/AppIcon.icns"
  cp "$ROOT/assets/NEW-aside-logo.png" "$APP_BUNDLE/Contents/Resources/NEW-aside-logo.png"
  printf "APPL????" > "$APP_BUNDLE/Contents/PkgInfo"
  chmod +x "$APP_EXECUTABLE"
fi

echo "==> Launching AsideShell in protocol-smoke mode"
rm -f "$LOG_PATH"
if [[ -n "$APP_BUNDLE" && "$APP_BUNDLE" != "$DEV_APP" ]]; then
  open -W -n "$APP_BUNDLE" --args \
    --aside-protocol-smoke \
    --aside-smoke-log "$LOG_PATH" &
else
  open -W -n "$APP_BUNDLE" --args \
    --aside-protocol-smoke \
    --aside-smoke-log "$LOG_PATH" \
    --aside-repo-root "$ROOT" \
    --aside-python "$PYTHON" &
fi
APP_PID="$!"

rc=""
for ((i = 0; i < TIMEOUT_SECONDS; i++)); do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    if wait "$APP_PID"; then
      rc=0
    else
      rc=$?
    fi
    break
  fi
  sleep 1
done

if [[ -z "$rc" ]]; then
  echo "ERROR: AsideShell did not exit after helper readiness within ${TIMEOUT_SECONDS}s."
  kill -TERM "$APP_PID" 2>/dev/null || true
  wait "$APP_PID" 2>/dev/null || true
  cat "$LOG_PATH" 2>/dev/null || true
  exit 1
fi

echo "app pid: $APP_PID"
echo "exit code: $rc"
echo "-- swiftui-launch.log --"
if [[ -f "$LOG_PATH" ]]; then
  cat "$LOG_PATH"
else
  echo "(no launch log written)"
fi

if [[ "$rc" != "0" ]]; then
  echo "ERROR: SwiftUI app exited with unexpected code $rc." >&2
  exit 1
fi

if grep -Eqi "(Traceback|ImportError|ModuleNotFoundError|Library not loaded|dyld:|Abort trap|Segmentation fault)" "$LOG_PATH"; then
  echo "ERROR: detected explicit runtime crash signature in SwiftUI launch log." >&2
  exit 1
fi

for expected in "launched helper pid" "helper protocol ready" "protocol smoke passed: helper ready"; do
  if ! grep -q "$expected" "$LOG_PATH"; then
    echo "ERROR: SwiftUI launch log missing expected marker: $expected" >&2
    exit 1
  fi
done

echo "SwiftUI launch smoke passed."
