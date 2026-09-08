import sys

from aside.config import DICTIONARY_FILE
from aside.ui import settings


def test_open_dictionary_file_uses_os_file_association(monkeypatch):
    """Dictionary opens via the OS file association (NSWorkspace), not a shell."""
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

    app._widgets = {
        "hw_entry": FakeEntry(
            "bad\nword\rterm\vnext\fmore\x1cfoo\x1dbar\x1ebaz\x85qux\u2028quux\u2029end"
        )
    }

    # Mock methods called after writing
    app._check_hw_add_state = lambda: None
    app._refresh_dict_count = lambda: None
    app._show_status_message = lambda *args, **kwargs: None

    app._on_add_hotword()

    assert dict_file.read_text(encoding="utf-8") == (
        "\nbad word term next more foo bar baz qux quux end"
    )


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
        "rep_wrong": FakeEntry("bad\u2028wrong\x85term"),
        "rep_right": FakeEntry("good\u2029right\x1eterm"),
    }

    # Mock methods called after writing
    app._check_rep_add_state = lambda: None
    app._refresh_dict_count = lambda: None
    app._show_status_message = lambda *args, **kwargs: None

    app._on_add_replacement()

    assert dict_file.read_text(encoding="utf-8") == (
        "\nbad wrong term → good right term"
    )
