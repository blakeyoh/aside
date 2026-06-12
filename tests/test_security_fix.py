import sys
import types
from unittest.mock import MagicMock

# Mock AppKit
sys.modules['AppKit'] = MagicMock()
sys.modules['AppKit.NSWorkspace'] = MagicMock()
sys.modules['Foundation'] = MagicMock()
sys.modules['Foundation.NSURL'] = MagicMock()

from aside import permissions
from aside.ui import settings
from aside.config import DICTIONARY_FILE

def test_open_privacy_pane_uses_webbrowser(monkeypatch):
    opened = []
    monkeypatch.setattr(permissions.webbrowser, "open", opened.append)

    permissions.open_privacy_pane("microphone")

    assert opened == [
        "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
    ]

def test_open_privacy_pane_invalid_pane(monkeypatch, caplog):
    opened = []
    monkeypatch.setattr(permissions.webbrowser, "open", opened.append)

    permissions.open_privacy_pane("invalid_pane_name_123")

    assert not opened
    assert "Invalid privacy pane requested: invalid_pane_name_123" in caplog.text

def test_open_dictionary_file_uses_os_file_association(monkeypatch):
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

    monkeypatch.setattr(settings, "ensure_dictionary_file", lambda: calls.append(("ensure", None)))
    monkeypatch.setattr(settings, "NSURL", FakeNSURL)
    monkeypatch.setattr(settings, "NSWorkspace", FakeNSWorkspace)

    settings.open_dictionary_file()

    assert calls == [
        ("ensure", None),
        ("file_url", str(DICTIONARY_FILE)),
        ("shared_workspace", None),
        ("open_url", f"file://{DICTIONARY_FILE}"),
    ]
