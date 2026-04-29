"""Resource location helpers for source and packaged app modes."""

from pathlib import Path
import sys


def resource_path(name: str) -> Path:
    """Locate bundled resources in source checkouts and frozen app bundles."""
    if getattr(sys, "frozen", False):
        # py2app app layout: Aside.app/Contents/Resources/<name>
        return Path(sys.executable).resolve().parent.parent / "Resources" / name

    # Source mode: repository root
    return Path(__file__).resolve().parent.parent.parent / name
