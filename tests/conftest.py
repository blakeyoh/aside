"""Test-collection shims for running the suite off macOS.

Aside is a macOS app: some modules import GUI/audio/native libraries that are
unavailable on Linux. These stubs let cloud coding agents run the runnable
subset of the suite locally. They are installed ONLY when the real library is
absent, so on macOS the genuine libraries are always used and these shims stay
inert. Tests that need real native behavior (e.g. the helper subprocess) skip
themselves on Linux and are covered by the macOS CI workflow instead.
"""
import sys
import types
from unittest.mock import MagicMock


def _real_module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _install_mock_module(name: str) -> None:
    """Register a MagicMock for a library that is only used at call time."""
    if not _real_module_available(name):
        sys.modules[name] = MagicMock()


def _install_widget_toolkit_stub(name: str) -> None:
    """Register a GUI toolkit stub whose attributes are real classes.

    customtkinter/tkinter are imported at module-load time, and some classes
    (``ctk.CTk``, ``ctk.CTkToplevel``) are used as base classes. A MagicMock
    can't be subclassed, so each attribute resolves to a permissive placeholder
    class that is both subclassable and callable.
    """
    if _real_module_available(name):
        return

    module = types.ModuleType(name)
    cache: dict[str, type] = {}

    def make_attr(attr: str):
        if attr not in cache:
            cache[attr] = type(
                attr,
                (),
                {
                    "__init__": lambda self, *a, **k: None,
                    "__getattr__": lambda self, _n: (lambda *a, **k: None),
                },
            )
        return cache[attr]

    module.__getattr__ = make_attr  # type: ignore[attr-defined]
    sys.modules[name] = module


_install_mock_module("numpy")
_install_mock_module("sounddevice")
_install_mock_module("AppKit")
_install_mock_module("Foundation")
_install_widget_toolkit_stub("tkinter")
_install_widget_toolkit_stub("customtkinter")
