#!/bin/bash
set -e

echo ""
echo "============================================"
echo "  Aside — Setup"
echo "============================================"
echo ""

# ── Python 3.13+ ──────────────────────────────────────────────────────────────
PYTHON=""

# Prefer Homebrew Python 3.13
for candidate in \
    /opt/homebrew/bin/python3.13 \
    /usr/local/bin/python3.13 \
    python3.13 \
    python3; do
    if command -v "$candidate" &>/dev/null; then
        VERSION=$("$candidate" --version 2>&1 | awk '{print $2}')
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 13 ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    echo "⚠️   Python 3.13+ not found."
    echo ""

    # Ensure Homebrew is available before attempting auto-install
    if ! command -v brew &>/dev/null; then
        echo "    Homebrew is also missing. Install it first:"
        echo "      /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        echo ""
        echo "    Then re-run: ./setup.sh"
        exit 1
    fi

    echo "    Installing Python 3.13 via Homebrew…"
    brew install python@3.13

    # Re-probe after install
    for candidate in /opt/homebrew/bin/python3.13 /usr/local/bin/python3.13 python3.13; do
        if command -v "$candidate" &>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    done

    if [ -z "$PYTHON" ]; then
        echo "❌  Python 3.13 install failed. Try manually: brew install python@3.13"
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
for pkg in portaudio; do
    if ! brew list "$pkg" &>/dev/null 2>&1; then
        echo "Installing $pkg…"
        brew install "$pkg"
    fi
done
echo "✅  portaudio"

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

# ── Python packages ───────────────────────────────────────────────────────────
echo ""
echo "Installing Aside and dependencies (this takes a few minutes on first run)…"
pip install --upgrade pip --quiet
pip install -e "$SCRIPT_DIR" --quiet
echo "✅  Aside package installed (editable)"

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
    ('faster_whisper', 'faster-whisper'),
    ('sounddevice',    'sounddevice'),
    ('numpy',          'numpy'),
    ('Quartz',         'pyobjc-framework-Quartz'),
    ('AppKit',         'pyobjc-framework-Cocoa'),
    ('customtkinter',  'customtkinter'),
    ('PIL',            'pillow'),
    ('aside',          'aside'),
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
echo "  Or build a packaged .app:"
echo "    scripts/build_app.sh release   # produces dist/Aside.app"
echo "    scripts/package_dmg.sh         # wraps it in a DMG"
echo ""
echo "Hotkey: hold  Ctrl + Option + Space  to record, release to transcribe."
echo ""
