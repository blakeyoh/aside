"""AppKit menu bar integration for Aside.

Creates the system status bar item with icon, recording indicator,
and dropdown menu (About, Settings, Quit).
"""
import logging
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    from AppKit import (
        NSApplication, NSApplicationActivationPolicyAccessory,
        NSObject, NSAlert, NSSound,
        NSStatusBar, NSVariableStatusItemLength,
        NSMenu, NSMenuItem,
        NSImage, NSBezierPath, NSColor,
    )
    APPKIT_AVAILABLE = True
except Exception:
    APPKIT_AVAILABLE = False


def play_sound(name: str) -> None:
    if not APPKIT_AVAILABLE:
        return
    try:
        sound = NSSound.soundNamed_(name)
        if sound:
            sound.play()
    except Exception:
        pass


def hotkey_display(cfg: dict) -> str:
    """Format a hotkey config as a human-readable string."""
    from aside.ui.theme import MOD_SYMBOLS, KEY_DISPLAY
    mods = cfg.get("modifiers", [])
    trigger = cfg.get("trigger", "space")
    parts = [
        MOD_SYMBOLS.get(m, m.capitalize())
        for m in ["ctrl", "alt", "cmd", "shift"]
        if m in mods
    ]
    parts.append(KEY_DISPLAY.get(trigger, trigger.capitalize()))
    return "  ".join(parts)


if APPKIT_AVAILABLE:
    class _MenuDelegate(NSObject):
        _show_cb = None
        _quit_cb = None
        _permissions_cb = None

        def showWindow_(self, sender):
            if self._show_cb:
                try:
                    self._show_cb()
                except Exception:
                    logger.exception("Failed to run menu callback: showWindow")
                    self._show_callback_failure_alert(
                        "Unable to open settings.",
                        "Please check logs for details."
                    )

        def showPermissions_(self, sender):
            if self._permissions_cb:
                try:
                    self._permissions_cb()
                except Exception:
                    logger.exception("Failed to run menu callback: showPermissions")
                    self._show_callback_failure_alert(
                        "Unable to open permissions.",
                        "Please check logs for details."
                    )

        @staticmethod
        def _show_callback_failure_alert(message: str, info: str) -> None:
            try:
                alert = NSAlert.alloc().init()
                alert.setMessageText_(message)
                alert.setInformativeText_(info)
                alert.runModal()
            except Exception:
                logger.exception("Failed to show callback failure alert")

        def aboutApp_(self, sender):
            try:
                alert = NSAlert.alloc().init()
                alert.setMessageText_("Aside")
                alert.setInformativeText_(
                    "Private voice dictation for Mac.\n"
                    "100% local. Powered by Whisper."
                )
                alert.runModal()
            except Exception:
                pass

        def quitApp_(self, sender):
            if self._quit_cb:
                self._quit_cb()


class MenuBar:
    """Manages the macOS menu bar status item."""

    def __init__(
        self,
        icon_path: Path,
        show_callback: Callable,
        quit_callback: Callable,
        permissions_callback: Optional[Callable] = None,
    ):
        self._status_item = None
        self._idle_icon = None
        self._record_icon = None
        self._transcribe_icon = None

        if not APPKIT_AVAILABLE:
            return

        NSApplication.sharedApplication().setActivationPolicy_(
            NSApplicationActivationPolicyAccessory
        )

        delegate = _MenuDelegate.alloc().init()
        delegate._show_cb = show_callback
        delegate._quit_cb = quit_callback
        delegate._permissions_cb = permissions_callback
        self._delegate = delegate  # prevent GC

        bar = NSStatusBar.systemStatusBar()
        item = bar.statusItemWithLength_(NSVariableStatusItemLength)

        bar_image = NSImage.alloc().initWithContentsOfFile_(str(icon_path))
        if bar_image is not None:
            bar_image.setTemplate_(True)
            item.button().setImage_(bar_image)
            item.button().setTitle_("")
            self._idle_icon = bar_image
            self._record_icon = self._make_badged_icon(
                bar_image, (1.0, 0.624, 0.039, 1.0)
            )
            self._transcribe_icon = self._make_badged_icon(
                bar_image, (0.039, 0.518, 1.0, 1.0)
            )
        else:
            logger.warning("Menu bar icon not found: %s", icon_path)
            item.button().setTitle_("A")

        menu = NSMenu.alloc().init()

        about = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "About Aside", "aboutApp:", ""
        )
        about.setTarget_(delegate)
        menu.addItem_(about)
        menu.addItem_(NSMenuItem.separatorItem())

        show = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Settings\u2026", "showWindow:", ""
        )
        show.setTarget_(delegate)
        menu.addItem_(show)

        permissions = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Permissions\u2026", "showPermissions:", ""
        )
        permissions.setTarget_(delegate)
        menu.addItem_(permissions)
        menu.addItem_(NSMenuItem.separatorItem())

        quit_item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            "Quit Aside", "quitApp:", ""
        )
        quit_item.setTarget_(delegate)
        menu.addItem_(quit_item)

        item.setMenu_(menu)
        self._status_item = item

    def set_recording(self, is_recording: bool) -> None:
        self.set_state("recording" if is_recording else "ready")

    def set_state(self, state: str) -> None:
        if not self._status_item:
            return
        try:
            if state == "recording":
                icon = self._record_icon
            elif state == "transcribing":
                icon = self._transcribe_icon
            else:
                icon = self._idle_icon
            if icon:
                self._status_item.button().setImage_(icon)
        except Exception:
            pass

    @staticmethod
    def _make_badged_icon(
        idle_icon: "NSImage",
        rgba: tuple[float, float, float, float],
    ) -> "NSImage":
        size = 22.0
        img = NSImage.alloc().initWithSize_((size, size))
        img.lockFocus()
        NSColor.colorWithSRGBRed_green_blue_alpha_(*rgba).setFill()
        NSBezierPath.bezierPathWithOvalInRect_(((0.0, 0.0), (size, size))).fill()
        if idle_icon:
            idle_icon.drawInRect_(((0.0, 0.0), (size, size)))
        img.unlockFocus()
        return img
