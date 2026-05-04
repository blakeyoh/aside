"""Resource location helpers for source and packaged app modes."""

from pathlib import Path
import sys


def resource_path(name: str) -> Path:
    """Locate bundled resources in source checkouts and frozen app bundles."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        if getattr(sys, "frozen", False):
            # py2app app layout: Aside.app/Contents/Resources/<name>
            base_path = Path(sys.executable).resolve().parent.parent / "Resources"
        else:
            # Source mode: repository root
            base_path = Path(__file__).resolve().parent.parent.parent

    return Path(base_path) / name
