"""Quartz CGEventTap for hotkey detection.

Runs on a dedicated background CFRunLoop thread. The callback is GIL-safe:
it reads hotkey attributes (atomic under CPython GIL) and pushes raw ints
to a queue. It NEVER acquires threading.Lock.

Call poll() from your UI's event loop (~10ms interval) to drain the queue.
"""
import queue
import threading
from typing import Callable, Optional

from Quartz import (
    CGEventTapCreate,
    CGEventTapEnable,
    CGEventGetIntegerValueField,
    CGEventGetFlags,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventFlagsChanged,
    kCGKeyboardEventKeycode,
    kCGEventFlagMaskControl,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCGEventTapDisabledByTimeout,
    CFMachPortCreateRunLoopSource,
    CFRunLoopGetCurrent,
    CFRunLoopAddSource,
    CFRunLoopRun,
    CFRunLoopStop,
    kCFRunLoopCommonModes,
)

DEFAULT_HOTKEY = {"modifiers": ["ctrl", "alt"], "trigger": "space"}
ACCESSIBILITY_ERROR = (
    "error: could not create event tap (check Accessibility permissions)"
)

# Map config modifier strings to CGEvent flag masks
_MOD_FLAG_MAP = {
    "ctrl": kCGEventFlagMaskControl,
    "alt": kCGEventFlagMaskAlternate,
    "cmd": kCGEventFlagMaskCommand,
    "shift": kCGEventFlagMaskShift,
}

# Reverse map: flag mask → config string (for capture mode)
_FLAG_TO_MOD = {
    kCGEventFlagMaskControl: "ctrl",
    kCGEventFlagMaskAlternate: "alt",
    kCGEventFlagMaskCommand: "cmd",
    kCGEventFlagMaskShift: "shift",
}

# Map trigger strings to macOS virtual keycodes
_KEYCODE_MAP = {
    "space": 49, "return": 36, "tab": 48, "escape": 53, "backspace": 51,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31,
    "p": 35, "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9,
    "w": 13, "x": 7, "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21,
    "5": 23, "6": 22, "7": 26, "8": 28, "9": 25,
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
}

# Reverse map: keycode → config trigger name (for capture mode)
_KEYCODE_TO_NAME = {v: k for k, v in _KEYCODE_MAP.items()}

# Modifier keycodes (not triggers — skip these during capture)
_MODIFIER_KEYCODES = {54, 55, 56, 57, 58, 59, 60, 61, 62, 63}


def parse_hotkey(config: dict) -> tuple[int, int]:
    """Convert hotkey config dict to (modifier_mask, keycode) for Quartz."""
    mod_mask = 0
    for m in config.get("modifiers", ["ctrl", "alt"]):
        mod_mask |= _MOD_FLAG_MAP.get(m, 0)
    trigger_str = config.get("trigger", "space").lower()
    keycode = _KEYCODE_MAP.get(trigger_str, -1)
    return mod_mask, keycode


def hotkeys_equal(first: dict | None, second: dict | None) -> bool:
    """Return True when two valid hotkey configs resolve to the same combo."""
    if not first or not second:
        return False
    first_mod, first_key = parse_hotkey(first)
    second_mod, second_key = parse_hotkey(second)
    if first_key < 0 or second_key < 0:
        return False
    return first_mod == second_mod and first_key == second_key


class HotkeyManager:
    """Manages the Quartz CGEventTap and hotkey detection.

    Threading model:
    - Event tap callback runs on background CFRunLoop thread
    - Callback reads hotkey attributes (GIL-atomic, no locks)
    - Events pushed to queue as raw ints
    - poll() drains queue on main thread
    """

    def __init__(
        self,
        hotkey_config: dict | None = None,
        toggle_hotkey_config: dict | None = None,
        on_event: Callable[[int, int, int], None] | None = None,
        on_accessibility_error: Callable[[], None] | None = None,
    ):
        hk_mod, hk_key = parse_hotkey(hotkey_config or DEFAULT_HOTKEY)
        tg_mod, tg_key = (
            parse_hotkey(toggle_hotkey_config) if toggle_hotkey_config else (0, -1)
        )

        # Written under lock by update methods; read without lock by callback
        self._hotkey_mod_mask = hk_mod
        self._hotkey_keycode = hk_key
        self._toggle_mod_mask = tg_mod
        self._toggle_keycode = tg_key

        self._lock = threading.Lock()
        self._tap = None
        self._tap_loop = None
        self._event_queue: queue.Queue = queue.Queue()
        self._on_event = on_event or (lambda *_: None)
        self._capture_callback: Callable[[dict], None] | None = None

        self._install_event_tap(on_accessibility_error)

    def _install_event_tap(self, on_error: Callable | None) -> None:
        event_mask = (
            (1 << kCGEventKeyDown)
            | (1 << kCGEventKeyUp)
            | (1 << kCGEventFlagsChanged)
        )
        eq = self._event_queue

        def callback(proxy, event_type, event, refcon):
            if event_type == kCGEventTapDisabledByTimeout:
                CGEventTapEnable(self._tap, True)
                return event
            keycode = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
            flags = int(CGEventGetFlags(event))
            eq.put_nowait((int(event_type), keycode, flags))
            # Suppress trigger keypresses — read attributes without lock
            # (CPython GIL atomicity for individual reads)
            if event_type == kCGEventKeyDown:
                hk_mask = self._hotkey_mod_mask
                hk_key = self._hotkey_keycode
                tg_mask = self._toggle_mod_mask
                tg_key = self._toggle_keycode
                if hk_mask > 0 and keycode == hk_key and (flags & hk_mask) == hk_mask:
                    return None
                if tg_mask > 0 and tg_key >= 0 and keycode == tg_key and (flags & tg_mask) == tg_mask:
                    return None
            return event

        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            0,  # kCGEventTapOptionDefault — not exported by pyobjc
            event_mask,
            callback,
            None,
        )
        if tap is None:
            if on_error:
                on_error()
            return

        self._tap = tap
        source = CFMachPortCreateRunLoopSource(None, tap, 0)

        def run_loop():
            loop = CFRunLoopGetCurrent()
            self._tap_loop = loop
            CFRunLoopAddSource(loop, source, kCFRunLoopCommonModes)
            CGEventTapEnable(tap, True)
            CFRunLoopRun()

        threading.Thread(target=run_loop, daemon=True, name="event-tap").start()

    def poll(self) -> None:
        """Drain event queue. Call from main thread ~10ms interval."""
        while True:
            try:
                event_type, keycode, flags = self._event_queue.get_nowait()
            except queue.Empty:
                break
            if self._capture_callback is not None:
                self._process_capture(event_type, keycode, flags)
            else:
                self._on_event(event_type, keycode, flags)

    def _process_capture(self, event_type: int, keycode: int, flags: int) -> None:
        if event_type != kCGEventKeyDown:
            return
        if keycode in _MODIFIER_KEYCODES:
            return
        trigger = _KEYCODE_TO_NAME.get(keycode)
        if not trigger:
            return
        mods = [name for mask, name in _FLAG_TO_MOD.items() if flags & mask]
        if not mods:
            return
        config = {"modifiers": sorted(mods), "trigger": trigger}
        cb = self._capture_callback
        self._capture_callback = None
        cb(config)

    def start_capture(self, on_captured: Callable[[dict], None]) -> None:
        self._capture_callback = on_captured

    def stop_capture(self) -> None:
        self._capture_callback = None

    def update_hotkey(self, config: dict) -> None:
        mod_mask, keycode = parse_hotkey(config)
        with self._lock:
            self._hotkey_mod_mask = mod_mask
            self._hotkey_keycode = keycode

    def update_toggle_hotkey(self, config: dict | None) -> None:
        if config:
            mod_mask, keycode = parse_hotkey(config)
        else:
            mod_mask, keycode = 0, -1
        with self._lock:
            self._toggle_mod_mask = mod_mask
            self._toggle_keycode = keycode

    def shutdown(self) -> None:
        if self._tap is not None:
            CGEventTapEnable(self._tap, False)
            if self._tap_loop is not None:
                CFRunLoopStop(self._tap_loop)
            self._tap_loop = None
            self._tap = None
