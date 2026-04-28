from aside.engine import hotkeys
from aside.engine.hotkeys import HotkeyManager, hotkeys_equal, parse_hotkey


def test_parse_hotkey_resolves_default_combo():
    mod_mask, keycode = parse_hotkey({"modifiers": ["ctrl", "alt"], "trigger": "space"})
    assert mod_mask > 0
    assert keycode == 49


def test_hotkeys_equal_ignores_modifier_order():
    first = {"modifiers": ["ctrl", "alt"], "trigger": "space"}
    second = {"modifiers": ["alt", "ctrl"], "trigger": "space"}
    assert hotkeys_equal(first, second)


def test_hotkeys_equal_rejects_different_trigger():
    first = {"modifiers": ["ctrl", "alt"], "trigger": "space"}
    second = {"modifiers": ["ctrl", "alt"], "trigger": "d"}
    assert not hotkeys_equal(first, second)


def test_hotkeys_equal_rejects_missing_toggle():
    first = {"modifiers": ["ctrl", "alt"], "trigger": "space"}
    assert not hotkeys_equal(first, None)


def test_hotkey_manager_degrades_gracefully_when_quartz_missing(monkeypatch):
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", False)
    triggered = []

    manager = HotkeyManager(on_accessibility_error=lambda: triggered.append(True))

    assert manager._tap is None
    assert triggered == [True]
