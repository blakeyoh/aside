"""Build the Python stdio helper as an embeddable py2app bundle.

The SwiftUI app launches this helper from:
  Aside.app/Contents/Helpers/AsideHelper.app/Contents/MacOS/AsideHelper
"""

from pathlib import Path
import sys

from setuptools import setup
from py2app.build_app import py2app as _py2app_command

sys.setrecursionlimit(10000)


class py2app(_py2app_command):
    """Clear pyproject-derived dependency metadata that py2app rejects."""

    def finalize_options(self):  # noqa: D401
        for attr in ("install_requires", "setup_requires", "tests_require"):
            if hasattr(self.distribution, attr):
                setattr(self.distribution, attr, [])
        super().finalize_options()


APP = ["src/aside/helper.py"]
MODEL_DIR = Path("vendor/models/faster-whisper-base")

OPTIONS = {
    "plist": {
        "CFBundleName": "AsideHelper",
        # Keep the executable/bundle identity distinct while making any TCC
        # attribution user-facing and consistent with the containing app.
        "CFBundleDisplayName": "Aside",
        "CFBundleIdentifier": "com.blakeyoh.aside.helper",
        "CFBundleExecutable": "AsideHelper",
        "CFBundlePackageType": "APPL",
        "LSMinimumSystemVersion": "13.0",
        "LSUIElement": True,
        "NSMicrophoneUsageDescription": "Aside needs microphone access to transcribe your speech locally.",
    },
    "packages": [
        "aside",
        "faster_whisper",
        "ctranslate2",
        "tokenizers",
        "huggingface_hub",
        "PIL",
    ],
    "includes": [
        "sounddevice",
        "numpy",
        "AppKit",
        "Quartz",
        "AVFoundation",
        "ApplicationServices",
    ],
    "excludes": [
        "IPython",
        "customtkinter",
        "jax",
        "llvmlite",
        "matplotlib",
        "numba",
        "pandas",
        "scipy",
        "sympy",
        "tensorflow",
        "torch",
        "torchaudio",
        "torchgen",
        "torchvision",
        "transformers",
        "triton",
    ],
    "argv_emulation": False,
    "strip": False,
}

if MODEL_DIR.exists():
    OPTIONS["resources"] = [str(MODEL_DIR)]

setup(
    name="AsideHelper",
    app=APP,
    options={"py2app": OPTIONS},
    cmdclass={"py2app": py2app},
)
