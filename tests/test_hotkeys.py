from aside.engine.hotkeys import hotkeys_equal, parse_hotkey


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
