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
