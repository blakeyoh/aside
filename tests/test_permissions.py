import sys
import types

from aside import permissions
from aside.permissions import PermissionStatus


def _module(**attrs):
    module = types.ModuleType("fake")
    for key, value in attrs.items():
        setattr(module, key, value)
    return module


def test_input_monitoring_uses_coregraphics_preflight_when_granted(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "Quartz",
        _module(CGPreflightListenEventAccess=lambda: True),
    )
    monkeypatch.setattr(
        permissions,
        "_check_input_monitoring_iohid",
        lambda: PermissionStatus.DENIED,
    )

    assert permissions.check_input_monitoring() == PermissionStatus.GRANTED


def test_input_monitoring_falls_back_to_iohid_when_preflight_denies(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "Quartz",
        _module(CGPreflightListenEventAccess=lambda: False),
    )
    monkeypatch.setattr(
        permissions,
        "_check_input_monitoring_iohid",
        lambda: PermissionStatus.NOT_DETERMINED,
    )

    assert permissions.check_input_monitoring() == PermissionStatus.NOT_DETERMINED


def test_request_privacy_access_does_not_open_settings_when_native_prompt_grants(
    monkeypatch,
):
    opened = []
    monkeypatch.setattr(
        permissions,
        "request_input_monitoring",
        lambda: PermissionStatus.GRANTED,
    )
    monkeypatch.setattr(permissions, "open_privacy_pane", opened.append)

    assert permissions.request_privacy_access("input_monitoring") == PermissionStatus.GRANTED
    assert opened == []


def test_request_privacy_access_opens_settings_when_still_ungranted(monkeypatch):
    opened = []
    monkeypatch.setattr(
        permissions,
        "request_accessibility",
        lambda: PermissionStatus.DENIED,
    )
    monkeypatch.setattr(permissions, "open_privacy_pane", opened.append)

    assert permissions.request_privacy_access("accessibility") == PermissionStatus.DENIED
    assert opened == ["accessibility"]
