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


def test_hotkey_manager_degrades_when_event_tap_binding_missing(monkeypatch):
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", True)
    monkeypatch.setattr(hotkeys, "CGEventTapCreate", None)
    triggered = []

    manager = HotkeyManager(on_accessibility_error=lambda: triggered.append(True))

    assert manager._tap is None
    assert triggered == [True]


def test_refresh_permissions_reenables_existing_event_tap(monkeypatch):
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", False)
    manager = HotkeyManager()
    tap = object()
    enabled = []
    manager._tap = tap
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", True)
    monkeypatch.setattr(
        hotkeys,
        "CGEventTapEnable",
        lambda candidate, value: enabled.append((candidate, value)),
    )

    assert manager.refresh_permissions() is True
    assert enabled == [(tap, True)]


def test_refresh_permissions_rebuilds_missing_event_tap(monkeypatch):
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", False)
    manager = HotkeyManager()
    monkeypatch.setattr(hotkeys, "QUARTZ_AVAILABLE", True)
    monkeypatch.setattr(hotkeys, "CGEventTapEnable", lambda *_: None)

    def install(_on_error):
        manager._tap = object()

    monkeypatch.setattr(manager, "_install_event_tap", install)

    assert manager.refresh_permissions() is True
    assert manager._tap is not None
