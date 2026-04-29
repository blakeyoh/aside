"""Build Aside.app via py2app.

Usage:
  python setup_py2app.py py2app -A   # alias/dev build
  python setup_py2app.py py2app      # release-style build
"""

from pathlib import Path
import sys

from setuptools import setup
from py2app.build_app import py2app as _py2app_command

sys.setrecursionlimit(10000)


class py2app(_py2app_command):
    """py2app command override that strips install_requires before the check.

    py2app 0.28.10 (the latest released version) rejects any distribution
    that has `install_requires` set, raising:

        error: install_requires is no longer supported

    We don't set install_requires directly, but modern setuptools auto-loads
    pyproject.toml from the cwd and populates it from `[project] dependencies`.
    Clearing the attribute (and the related setup_requires / tests_require)
    on the distribution right before py2app's check satisfies py2app while
    leaving the runtime venv install — which already happened via
    `pip install -e .` in setup.sh — untouched.
    """

    def finalize_options(self):  # noqa: D401
        for attr in ("install_requires", "setup_requires", "tests_require"):
            if hasattr(self.distribution, attr):
                setattr(self.distribution, attr, [])
        super().finalize_options()


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
    "includes": [
        "sounddevice",
        "numpy",
        "AppKit",
        "Quartz",
        "AVFoundation",
        "ApplicationServices",
    ],
    # py2app's module graph follows optional imports from packages such as
    # huggingface_hub and onnxruntime. In a stale developer venv this can pull
    # in large unused ML stacks that are not part of Aside's faster-whisper
    # runtime path.
    "excludes": [
        "IPython",
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
    cmdclass={"py2app": py2app},
)
