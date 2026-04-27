"""Build Aside.app via py2app.

Usage:
  python setup_py2app.py py2app -A   # alias/dev build
  python setup_py2app.py py2app      # release-style build
"""

from pathlib import Path

from setuptools import setup

APP = ["src/aside/__main__.py"]
MODEL_DIR = Path("vendor/models/faster-whisper-base")

DATA_FILES = ["aside-logo.png"]

OPTIONS = {
    "iconfile": "AppIcon.icns",
    "plist": "Info.plist",
    # Note: py2app 0.28 does not support a `codesign_entitlements` option.
    # entitlements.plist is applied later by `codesign --entitlements`
    # in scripts/package_dmg.sh and the GH Actions release workflow.
    "packages": [
        "aside",
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        "huggingface_hub",
        "customtkinter",
        "PIL",
    ],
    # sounddevice / numpy are explicit Python modules; the CFFI shim
    # `_sounddevice` is *not* a Python module (it's a dlopen'd dylib loaded
    # by sounddevice itself), so listing it under `includes` would fail.
    "includes": ["sounddevice", "numpy"],
    "argv_emulation": False,
    # ctranslate2/native libs are brittle under strip
    "strip": False,
}

if MODEL_DIR.exists():
    OPTIONS["resources"] = [str(MODEL_DIR)]

setup(
    name="Aside",
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
)
