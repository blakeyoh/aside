from aside.ui.menubar import hotkey_display


def test_default_combo_uses_symbols_and_double_space():
    assert hotkey_display({"modifiers": ["ctrl", "alt"], "trigger": "space"}) == "⌃  ⌥  Space"


def test_modifiers_render_in_canonical_order_regardless_of_input():
    # ctrl, alt, cmd, shift — independent of the order supplied
    assert hotkey_display({"modifiers": ["cmd", "ctrl"], "trigger": "a"}) == "⌃  ⌘  A"
    assert (
        hotkey_display({"modifiers": ["shift", "cmd", "alt", "ctrl"], "trigger": "tab"})
        == "⌃  ⌥  ⌘  ⇧  Tab"
    )


def test_special_trigger_uses_key_display_glyph():
    assert hotkey_display({"modifiers": [], "trigger": "backspace"}) == "⌫"


def test_unknown_trigger_is_capitalized():
    assert hotkey_display({"modifiers": [], "trigger": "k"}) == "K"


def test_unrecognized_modifier_is_ignored():
    assert hotkey_display({"modifiers": ["ctrl", "fn"], "trigger": "space"}) == "⌃  Space"


def test_missing_fields_fall_back_to_default_trigger():
    assert hotkey_display({}) == "Space"
