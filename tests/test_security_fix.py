import sys
from aside import permissions
from aside.config import DICTIONARY_FILE


def test_open_privacy_pane_uses_webbrowser(monkeypatch):
    opened = []
    monkeypatch.setattr(permissions.webbrowser, "open", opened.append)

    permissions.open_privacy_pane("microphone")

    assert opened == [
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    ]


def test_open_dictionary_file_uses_os_file_association(monkeypatch):
    import pytest

    if sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    from aside.ui import settings

    calls = []

    class FakeNSURL:
        @staticmethod
        def fileURLWithPath_(path):
            calls.append(("file_url", path))
            return f"file://{path}"

    class FakeWorkspace:
        def openURL_(self, url):
            calls.append(("open_url", url))

    class FakeNSWorkspace:
        @staticmethod
        def sharedWorkspace():
            calls.append(("shared_workspace", None))
            return FakeWorkspace()

    monkeypatch.setattr(
        settings, "ensure_dictionary_file", lambda: calls.append(("ensure", None))
    )
    monkeypatch.setattr(settings, "NSURL", FakeNSURL)
    monkeypatch.setattr(settings, "NSWorkspace", FakeNSWorkspace)

    settings.open_dictionary_file()

    assert calls == [
        ("ensure", None),
        ("file_url", str(DICTIONARY_FILE)),
        ("shared_workspace", None),
        ("open_url", f"file://{DICTIONARY_FILE}"),
    ]


def test_add_hotword_sanitizes_input(monkeypatch, tmp_path):
    import pytest

    if sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    monkeypatch.setitem(
        sys.modules,
        "AppKit",
        type("MockAppKit", (), {"NSAlert": type("NSAlert", (), {})})(),
    )
    monkeypatch.setitem(sys.modules, "Quartz", type("MockQuartz", (), {})())
    from aside.ui.app import App

    dict_file = tmp_path / "dictionary.txt"
    monkeypatch.setattr("aside.ui.app.DICTIONARY_FILE", dict_file)
    monkeypatch.setattr("aside.ui.app.ensure_dictionary_file", lambda: None)

    app = App.__new__(App)

    class FakeEntry:
        def __init__(self, val):
            self.val = val

        def get(self):
            return self.val

        def delete(self, *args):
            pass

        def focus(self):
            pass

    app._widgets = {"hw_entry": FakeEntry("bad\nword\r")}

    # Mock methods called after writing
    app._check_hw_add_state = lambda: None
    app._refresh_dict_count = lambda: None
    app._show_status_message = lambda *args, **kwargs: None

    app._on_add_hotword()

    assert dict_file.read_text(encoding="utf-8") == "\nbad word"


def test_add_replacement_sanitizes_input(monkeypatch, tmp_path):
    import pytest

    if sys.platform != "darwin":
        pytest.skip("Test requires macOS")

    monkeypatch.setitem(
        sys.modules,
        "AppKit",
        type("MockAppKit", (), {"NSAlert": type("NSAlert", (), {})})(),
    )
    monkeypatch.setitem(sys.modules, "Quartz", type("MockQuartz", (), {})())
    from aside.ui.app import App

    dict_file = tmp_path / "dictionary.txt"
    monkeypatch.setattr("aside.ui.app.DICTIONARY_FILE", dict_file)
    monkeypatch.setattr("aside.ui.app.ensure_dictionary_file", lambda: None)

    app = App.__new__(App)

    class FakeEntry:
        def __init__(self, val):
            self.val = val

        def get(self):
            return self.val

        def delete(self, *args):
            pass

        def focus(self):
            pass

    app._widgets = {
        "rep_wrong": FakeEntry("bad\nwrong\r"),
        "rep_right": FakeEntry("good\nright\r"),
    }

    # Mock methods called after writing
    app._check_rep_add_state = lambda: None
    app._refresh_dict_count = lambda: None
    app._show_status_message = lambda *args, **kwargs: None

    app._on_add_replacement()

    assert dict_file.read_text(encoding="utf-8") == "\nbad wrong \u2192 good right"
