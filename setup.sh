#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  Aside — Setup"
echo "============================================"
echo ""

# ── Python ────────────────────────────────────────────────────────────────────
# Aside is currently validated against a single Python minor version. To extend
# support to a new minor release (e.g., 3.14):
#   1. Add the new version to SUPPORTED_PYTHONS BEFORE the existing entries.
#   2. Push and let .github/workflows/build-smoke.yml exercise the full
#      install + py2app build path on macos-14.
#   3. Update .github/workflows/{build-smoke,release}.yml to install the new
#      python@X.Y + python-tk@X.Y formulas.
#   4. Update README + docs/packaging-status.md.
# Restricting to a known-tested allow-list catches the silently-wrong-Python
# case (e.g., faster-whisper / ctranslate2 wheels lag behind new CPython
# releases by weeks-to-months) before py2app eats 30 minutes of build time.
SUPPORTED_PYTHONS=("3.13")
DEFAULT_PYTHON_VERSION="${SUPPORTED_PYTHONS[0]}"

PYTHON=""
PYTHON_MINOR_VERSION=""

# Locate any supported python3.X interpreter, preferring earlier list entries.
find_python() {
    local ver="$1"
    for candidate in \
        "/opt/homebrew/bin/python${ver}" \
        "/usr/local/bin/python${ver}" \
        "python${ver}"; do
        if command -v "$candidate" &>/dev/null; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

for ver in "${SUPPORTED_PYTHONS[@]}"; do
    if found=$(find_python "$ver"); then
        PYTHON="$found"
        PYTHON_MINOR_VERSION="$ver"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "⚠️   No supported Python found (looked for: ${SUPPORTED_PYTHONS[*]})."
    echo ""

    # Ensure Homebrew is available before attempting auto-install
    if ! command -v brew &>/dev/null; then
        echo "    Homebrew is also missing. Install it first:"
        echo "      /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        echo "    Then re-run: ./setup.sh"
        exit 1
    fi

    echo "    Installing Python ${DEFAULT_PYTHON_VERSION} via Homebrew…"
    brew install "python@${DEFAULT_PYTHON_VERSION}"

    if PYTHON=$(find_python "$DEFAULT_PYTHON_VERSION"); then
        PYTHON_MINOR_VERSION="$DEFAULT_PYTHON_VERSION"
    fi

    if [ -z "$PYTHON" ]; then
        echo "❌  Python ${DEFAULT_PYTHON_VERSION} install failed. Try manually: brew install python@${DEFAULT_PYTHON_VERSION}"
        exit 1
    fi
fi
echo "✅  Python $($PYTHON --version | cut -d' ' -f2)  ($PYTHON)"

# ── Homebrew ──────────────────────────────────────────────────────────────────
if ! command -v brew &>/dev/null; then
    echo ""
    echo "Installing Homebrew…"
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
fi
echo "✅  Homebrew"

# ── System deps ───────────────────────────────────────────────────────────────
# python-tk@X.Y supplies _tkinter for Homebrew python@X.Y — without it,
# `import customtkinter` fails. Homebrew's python ships without Tk bindings;
# they are packaged separately. The version MUST match the chosen interpreter
# (see PYTHON_MINOR_VERSION above), otherwise the venv will create with one
# Python but the Tk binding will load against another and `import tkinter`
# will fail downstream.
TK_FORMULA="python-tk@${PYTHON_MINOR_VERSION}"
for pkg in portaudio "${TK_FORMULA}"; do
    if ! brew list "$pkg" &>/dev/null 2>&1; then
        echo "Installing $pkg…"
        brew install "$pkg"
    fi
done
echo "✅  portaudio + ${TK_FORMULA}"

# ── Python venv ───────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$SCRIPT_DIR/.venv"

if [ ! -d "$VENV" ]; then
    echo ""
    echo "Creating Python virtual environment…"
    "$PYTHON" -m venv "$VENV"
fi
source "$VENV/bin/activate"
echo "✅  Virtual environment"

# Verify Tk is actually wired into this Python before we try to install
# customtkinter / launch any UI. Homebrew's python@X.Y routinely ships
# without _tkinter, in which case every UI import fails downstream with a
# generic ImportError that's hard to trace back to here.
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "❌  Python is missing the tkinter / _tkinter module."
    echo "    Install the matching Homebrew Tk bindings and re-run setup:"
    echo "      brew install ${TK_FORMULA}"
    exit 1
fi
echo "✅  tkinter available"

# ── Python packages ───────────────────────────────────────────────────────────
echo ""
echo "Installing Aside and dependencies (this takes a few minutes on first run)…"
pip install --upgrade pip --quiet
# Pin setuptools < 70 so py2app 0.28 (the latest release) can run.
# Newer setuptools removed the legacy `install_requires` keyword that py2app's
# build_app command reads; without this pin, `scripts/build_app.sh release`
# fails with `error: install_requires is no longer supported`. wheel is needed
# for any source-only deps installed below.
pip install --quiet "setuptools<70" "wheel"
pip install -e "$SCRIPT_DIR" --quiet
echo "✅  Aside package installed (editable)"

# Install the build toolchain (py2app + huggingface_hub) so that
# scripts/build_app.sh works without manual surgery on the venv.
# pytest is included so PF-4 in docs/smoke-test-plan.md and the build-smoke
# CI workflow can run the unit suite without a separate install step.
echo "Installing build + dev toolchain (py2app, huggingface_hub, pytest)…"
pip install --quiet "py2app==0.28.10" "huggingface_hub>=0.20" "pytest>=8"
echo "✅  Build + dev toolchain installed"

# ── Config directory ──────────────────────────────────────────────────────────
ASIDE_DIR="$HOME/.aside"
mkdir -p "$ASIDE_DIR"
echo "✅  Config directory: $ASIDE_DIR"

# ── Dictionary template ───────────────────────────────────────────────────────
DICT_FILE="$ASIDE_DIR/dictionary.txt"
if [ ! -f "$DICT_FILE" ]; then
    cat > "$DICT_FILE" <<'DICT'
# Aside — Personal Dictionary
#
# Format:  spoken phrase => replacement
# Lines starting with # are comments.
#
# Examples:
#   gonna => going to
#   wanna => want to
#   lol => laughing out loud
#   my email => yourname@example.com
#
DICT
    echo "✅  Dictionary template created: $DICT_FILE"
else
    echo "✅  Dictionary already exists: $DICT_FILE"
fi

# ── Download Whisper model ────────────────────────────────────────────────────
echo ""
echo "Downloading Whisper 'base' model (~140 MB)…"
python3 -c "
from faster_whisper import WhisperModel
print('  Downloading model weights…')
WhisperModel('base', device='cpu', compute_type='int8')
print('  Model ready.')
"
echo "✅  Whisper model downloaded"

# ── Verify installation ───────────────────────────────────────────────────────
echo ""
echo "Verifying installation…"
python3 -c "
import sys
deps = [
    ('faster_whisper',  'faster-whisper'),
    ('sounddevice',     'sounddevice'),
    ('numpy',           'numpy'),
    ('Quartz',          'pyobjc-framework-Quartz'),
    ('AppKit',          'pyobjc-framework-Cocoa'),
    ('AVFoundation',    'pyobjc-framework-AVFoundation'),
    ('customtkinter',   'customtkinter'),
    ('PIL',             'pillow'),
    ('aside',           'aside'),
    ('py2app',          'py2app'),
    ('huggingface_hub', 'huggingface_hub'),
]
failed = []
for module, pkg in deps:
    try:
        __import__(module)
        print(f'  ✅  {pkg}')
    except ImportError:
        print(f'  ❌  {pkg} (missing)')
        failed.append(pkg)
if failed:
    print(f'\\nFailed: {failed}')
    sys.exit(1)
"
echo "✅  All dependencies verified"

# ── Register install path ─────────────────────────────────────────────────────
# Stored so a packaged Aside.app (dist/Aside.app from scripts/build_app.sh)
# can locate this venv if moved to /Applications.
ASIDE_DIR="$HOME/.aside"
mkdir -p "$ASIDE_DIR"
echo "$SCRIPT_DIR" > "$ASIDE_DIR/install_path.txt"
echo "✅  Install path registered: $SCRIPT_DIR"

# ── Permissions reminder ──────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "⚠️   IMPORTANT: grant these permissions before launching."
echo ""
echo "System Settings → Privacy & Security"
echo ""
echo "  • Microphone       → add Terminal (or iTerm2 / Warp / whichever you use)"
echo "  • Accessibility    → add Terminal (same app you ran this script from)"
echo "  • Input Monitoring → add Terminal (same app)"
echo ""
echo "macOS may prompt automatically on first use — click Allow when it does."
echo ""
echo "─────────────────────────────────────────────"
echo ""
echo "To launch:"
echo ""
echo "  Terminal:"
echo "    source .venv/bin/activate && python -m aside"
echo ""
echo "  Or build a packaged .app for local preview:"
echo "    scripts/build_app.sh dev       # alias build, no SHA needed"
echo ""
echo "  Reproduce a CI release build (requires a pinned model SHA):"
echo "    MODEL_REVISION=\$(git ls-remote https://huggingface.co/Systran/faster-whisper-base main | cut -f1) \\"
echo "      scripts/build_app.sh release"
echo "    scripts/package_dmg.sh         # wraps dist/Aside.app in a DMG"
echo ""
echo "Hotkey: hold  Ctrl + Option + Space  to record, release to transcribe."
echo ""
