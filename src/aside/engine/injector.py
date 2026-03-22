"""Text injection via Quartz keyboard events.

Injects text at the current cursor position using CGEventCreateKeyboardEvent.
Does NOT touch the clipboard. Works in any text field system-wide.
"""
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventKeyboardSetUnicodeString,
    CGEventPost,
    CGEventSetFlags,
    CGEventSourceCreate,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand,
)

# Virtual keycodes for special keys
_KEYCODE_MAP = {
    "backspace": 51,
    "z": 6,
    "a": 0,
    "c": 8,
}


def inject_text(text: str) -> int:
    """Inject text at cursor via Quartz keyboard events.

    Returns the number of characters injected (for delete_that tracking).
    """
    if not text:
        return 0
    try:
        source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        for char in text:
            for is_down in (True, False):
                evt = CGEventCreateKeyboardEvent(source, 0, is_down)
                CGEventKeyboardSetUnicodeString(evt, len(char), char)
                CGEventPost(kCGHIDEventTap, evt)
        return len(text)
    except Exception:
        return 0


def inject_keystroke(key: str, modifiers: list[str] | None = None) -> None:
    """Inject a single keystroke with optional modifiers.

    Args:
        key: Key name (e.g., "backspace", "z", "a", "c")
        modifiers: List of modifier names (e.g., ["cmd"])
    """
    keycode = _KEYCODE_MAP.get(key)
    if keycode is None:
        return

    try:
        source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        flags = 0
        if modifiers and "cmd" in modifiers:
            flags |= kCGEventFlagMaskCommand

        for is_down in (True, False):
            evt = CGEventCreateKeyboardEvent(source, keycode, is_down)
            if flags:
                CGEventSetFlags(evt, flags)
            CGEventPost(kCGHIDEventTap, evt)
    except Exception:
        pass
