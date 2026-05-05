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


def test_open_dictionary_file_uses_webbrowser(monkeypatch):
    opened = []
    monkeypatch.setattr(settings.webbrowser, "open", opened.append)

    settings.open_dictionary_file()

    assert opened == [str(DICTIONARY_FILE)]
