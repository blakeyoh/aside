import queue

from aside.ui import app as app_module
from aside.ui.app import (
    App,
    UI_ACTION_SHOW_ONBOARDING,
    UI_ACTION_SHOW_SETTINGS,
    initial_launch_target,
    register_macos_reopen_handlers,
    scroll_units_from_delta,
)


def test_initial_launch_target_uses_onboarding_until_first_run_complete():
    assert initial_launch_target({}) == "onboarding"
    assert initial_launch_target({"first_run_complete": False}) == "onboarding"


def test_initial_launch_target_uses_settings_after_first_run_complete():
    assert initial_launch_target({"first_run_complete": True}) == "settings"


class FakeTkRoot:
    def __init__(self):
        self.commands = []

    def createcommand(self, name, callback):
        self.commands.append((name, callback))


def test_register_macos_reopen_handlers_registers_dock_and_preferences(monkeypatch):
    monkeypatch.setattr(app_module.sys, "platform", "darwin")
    root = FakeTkRoot()
    callback = object()

    registered = register_macos_reopen_handlers(root, callback)

    assert registered == (
        "tk::mac::ReopenApplication",
        "tk::mac::ShowPreferences",
    )
    assert root.commands == [
        ("tk::mac::ReopenApplication", callback),
        ("tk::mac::ShowPreferences", callback),
    ]


def test_register_macos_reopen_handlers_noops_off_macos(monkeypatch):
    monkeypatch.setattr(app_module.sys, "platform", "linux")
    root = FakeTkRoot()

    assert register_macos_reopen_handlers(root, object()) == ()
    assert root.commands == []


def test_scroll_units_from_delta_preserves_macos_trackpad_direction():
    assert scroll_units_from_delta(1, "darwin") == -1
    assert scroll_units_from_delta(-1, "darwin") == 1
    assert scroll_units_from_delta(0.25, "darwin") == -1
    assert scroll_units_from_delta(0, "darwin") == 0


def test_menu_requests_enqueue_without_touching_tk():
    app = App.__new__(App)
    app._ui_actions = queue.Queue()

    App._request_show_settings(app)
    App._request_show_onboarding(app)

    assert app._ui_actions.get_nowait() == UI_ACTION_SHOW_SETTINGS
    assert app._ui_actions.get_nowait() == UI_ACTION_SHOW_ONBOARDING


def test_ui_action_poller_runs_queued_actions_on_tk_side():
    app = App.__new__(App)
    app._ui_actions = queue.Queue()
    app._is_quitting = True
    calls = []
    app._show_settings = lambda: calls.append("settings")
    app._show_onboarding = lambda: calls.append("onboarding")
    app._ui_actions.put(UI_ACTION_SHOW_SETTINGS)
    app._ui_actions.put(UI_ACTION_SHOW_ONBOARDING)

    App._poll_ui_actions(app)

    assert calls == ["settings", "onboarding"]
