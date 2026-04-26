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
if MODEL_DIR.exists():
    # Keep model inside app resources under models/faster-whisper-base
    DATA_FILES.append(("models", [str(MODEL_DIR)]))

OPTIONS = {
    "iconfile": "AppIcon.icns",
    "plist": "Info.plist",
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
    # py2app should pull from the active environment site-packages
    "site_packages": True,
    "arch": "arm64",
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={"py2app": OPTIONS},
    setup_requires=["py2app>=0.28"],
)
