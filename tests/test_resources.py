import sys
from pathlib import Path
from aside.resources import resource_path


def test_resource_path_meipass(monkeypatch):
    """Test resource_path when sys._MEIPASS is defined (PyInstaller mode)."""
    mock_meipass = "/tmp/_MEIPASS12345"
    monkeypatch.setattr(sys, "_MEIPASS", mock_meipass, raising=False)

    path = resource_path("test.txt")
    assert path == Path(mock_meipass) / "test.txt"


def test_resource_path_frozen_py2app(monkeypatch):
    """Test resource_path when sys.frozen is True (py2app mode)."""
    # Ensure _MEIPASS is NOT set
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    mock_exec = "/Applications/Aside.app/Contents/MacOS/Aside"
    monkeypatch.setattr(sys, "executable", mock_exec)

    path = resource_path("test.txt")
    # Expected: Aside.app/Contents/Resources/test.txt
    expected = Path("/Applications/Aside.app/Contents/Resources/test.txt")
    assert path == expected


def test_resource_path_source(monkeypatch):
    """Test resource_path in source mode (not frozen)."""
    # Ensure _MEIPASS is NOT set
    if hasattr(sys, "_MEIPASS"):
        monkeypatch.delattr(sys, "_MEIPASS")

    monkeypatch.setattr(sys, "frozen", False, raising=False)

    path = resource_path("test.txt")
    # In source mode, it should be 3 levels up from resources.py + filename
    # resources.py is at src/aside/resources.py
    # parent is src/aside/
    # parent.parent is src/
    # parent.parent.parent is root/
    root = Path(__file__).resolve().parent.parent
    expected = root / "test.txt"
    assert path == expected
