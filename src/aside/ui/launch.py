"""GUI-free launch helpers for the app shell.

Kept separate from ``aside.ui.app`` so they can be imported and unit-tested
without pulling in customtkinter (which needs a system Tk install).
"""
import logging
import sys

logger = logging.getLogger(__name__)

UI_ACTION_SHOW_SETTINGS = "show_settings"
UI_ACTION_SHOW_ONBOARDING = "show_onboarding"


def initial_launch_target(config: dict) -> str:
    """Return the first visible surface to show after startup."""
    return "settings" if config.get("first_run_complete") else "onboarding"


def register_macos_reopen_handlers(root, callback) -> tuple[str, ...]:
    """Register Tk macOS app-menu callbacks that reopen the settings window."""
    if sys.platform != "darwin":
        return ()

    registered = []
    for command_name in ("tk::mac::ReopenApplication", "tk::mac::ShowPreferences"):
        try:
            root.createcommand(command_name, callback)
            registered.append(command_name)
        except Exception:
            logger.debug("Unable to register %s", command_name, exc_info=True)
    return tuple(registered)


def scroll_units_from_delta(delta, platform: str = sys.platform) -> int:
    """Convert a Tk MouseWheel delta into conservative canvas scroll units."""
    try:
        numeric_delta = float(delta)
    except (TypeError, ValueError):
        return 0

    if numeric_delta == 0:
        return 0

    if platform.startswith("win"):
        magnitude = int(abs(numeric_delta) / 120)
    else:
        magnitude = int(abs(numeric_delta))

    magnitude = max(1, min(magnitude, 12))
    return -magnitude if numeric_delta > 0 else magnitude
