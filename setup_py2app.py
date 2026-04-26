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
    "codesign_entitlements": "entitlements.plist",
    "packages": [
        "aside",
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        "huggingface_hub",
        "customtkinter",
        "PIL",
    ],
    "includes": ["sounddevice", "_sounddevice", "numpy"],
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
    setup_requires=["py2app>=0.28"],
)
