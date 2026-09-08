import io
import json
from copy import deepcopy

from aside import helper
from aside.config import DEFAULT_CONFIG
from aside.helper import AsideStdioHelper, HelperDependencies
from aside.permissions import PermissionStatus


class FakeAudio:
    def __init__(self, on_mic_denied=None, on_error=None):
        self.on_mic_denied = on_mic_denied
        self.on_error = on_error
        self.started = False
        self.stopped = False

    def start(self):
        self.started = True
        return True

    def stop(self):
        self.stopped = True
        return [0.1, 0.2, 0.3]


class FakeTranscriber:
    def __init__(self, **kwargs):
        self.model_size = kwargs["model_size"]
        self.on_status = kwargs["on_status"]
        self.on_transcription = kwargs["on_transcription"]
        self.punctuation = kwargs["punctuation_config"]
        self.language = kwargs["language"]

    def load_model(self):
        self.on_status("ready")

    def transcribe(self, audio):
        self.on_transcription("hello world")
        self.on_status("ready")

    def update_punctuation(self, config):
        self.punctuation = config

    def update_language(self, language):
        self.language = language

    def reload_model(self, model_size):
        self.model_size = model_size
        self.on_status("loading")

    def reload_dictionary(self):
        self.dictionary_reloaded = True


class FakeHotkeys:
    def __init__(self, **kwargs):
        self.on_event = kwargs["on_event"]
        self.shutdown_called = False

    def poll(self):
        pass

    def update_hotkey(self, config):
        self.hotkey = config

    def update_toggle_hotkey(self, config):
        self.toggle_hotkey = config

    def refresh_permissions(self):
        self.permissions_refreshed = True
        return True

    def shutdown(self):
        self.shutdown_called = True


def _make_helper(stdout):
    config = deepcopy(DEFAULT_CONFIG)
    config["first_run_complete"] = True
    saved = []
    deps = HelperDependencies(
        audio_factory=FakeAudio,
        transcriber_factory=FakeTranscriber,
        hotkey_factory=FakeHotkeys,
        config_loader=lambda: config.copy(),
        config_saver=lambda cfg: saved.append(deepcopy(cfg)) or True,
    )
    app = AsideStdioHelper(stdin=io.StringIO(), stdout=stdout, dependencies=deps)
    app.saved_configs = saved
    return app


def _events(stdout):
    return [json.loads(line) for line in stdout.getvalue().splitlines()]


def test_normalize_engine_status_splits_error_detail():
    state, detail = helper.normalize_engine_status("error: model failed")

    assert state == "error"
    assert detail == "model failed"


def test_permission_snapshot_uses_public_status_names(monkeypatch):
    monkeypatch.setattr(helper, "check_microphone", lambda: PermissionStatus.GRANTED)
    monkeypatch.setattr(helper, "check_accessibility", lambda: PermissionStatus.DENIED)
    monkeypatch.setattr(
        helper,
        "check_input_monitoring",
        lambda: PermissionStatus.NOT_DETERMINED,
    )

    assert helper.permission_snapshot() == {
        "microphone": "granted",
        "accessibility": "denied",
        "inputMonitoring": "not_determined",
    }


def test_helper_commands_drive_recording_transcription_and_shutdown():
    stdout = io.StringIO()
    app = _make_helper(stdout)
    app._on_engine_status("ready")

    app.handle_command({"command": "startRecording"})
    app.handle_command({"command": "stopRecording"})
    app.shutdown()

    events = _events(stdout)
    status_events = [event["state"] for event in events if event["type"] == "status"]

    assert status_events == ["ready", "recording", "transcribing", "ready"]
    assert {
        "type": "transcription",
        "text": "hello world",
        "protocolVersion": 1,
    } in events
    assert events[-1]["type"] == "exit"


def test_model_ready_does_not_overwrite_permission_error():
    stdout = io.StringIO()
    app = _make_helper(stdout)
    app.dependencies.enforce_permissions = True
    app.dependencies.permission_snapshot_factory = lambda: {
        "microphone": "denied",
        "accessibility": "granted",
        "inputMonitoring": "granted",
    }

    app.emit_permissions()
    app._on_engine_status("ready")

    assert app.state == "error"
    status = [event for event in _events(stdout) if event["type"] == "status"][-1]
    assert status["modelReady"] is True
    assert status["permissionsReady"] is False
    assert "microphone" in status["message"]


def test_permission_refresh_recovers_ready_state():
    stdout = io.StringIO()
    app = _make_helper(stdout)
    app.dependencies.enforce_permissions = True
    snapshots = iter(
        [
            {
                "microphone": "denied",
                "accessibility": "granted",
                "inputMonitoring": "granted",
            },
            {
                "microphone": "granted",
                "accessibility": "granted",
                "inputMonitoring": "granted",
            },
        ]
    )
    app.dependencies.permission_snapshot_factory = lambda: next(snapshots)

    app.emit_permissions()
    app._on_engine_status("ready")
    app.handle_command({"command": "getPermissions"})

    assert app._hotkeys.permissions_refreshed is True
    assert app.state == "ready"
    status = [event for event in _events(stdout) if event["type"] == "status"][-1]
    assert status["modelReady"] is True
    assert status["permissionsReady"] is True


def test_audio_stop_failure_is_actionable():
    stdout = io.StringIO()
    app = _make_helper(stdout)

    def fail_stop():
        raise RuntimeError("device disappeared")

    app._audio.stop = fail_stop
    app._run_transcription()

    status = [event for event in _events(stdout) if event["type"] == "status"][-1]
    assert status["state"] == "error"
    assert "Could not stop the microphone cleanly" in status["message"]


def test_sleep_cleanup_discards_capture_and_restores_operational_state():
    stdout = io.StringIO()
    app = _make_helper(stdout)
    app._on_engine_status("ready")
    app._set_status("recording")
    app._toggle_active = True

    app._release_audio_for_sleep()

    assert app._audio.stopped is True
    assert app._toggle_active is False
    assert app.state == "ready"


def test_helper_rejects_unknown_command():
    stdout = io.StringIO()
    app = _make_helper(stdout)

    app.handle_command({"command": "bogus"})

    events = _events(stdout)
    assert events[-1]["type"] == "error"
    assert "unknown command" in events[-1]["message"]


def test_helper_set_config_updates_model_language_and_punctuation():
    stdout = io.StringIO()
    app = _make_helper(stdout)

    app.handle_command(
        {
            "command": "setConfig",
            "modelSize": "small",
            "language": "en",
            "punctuation": {
                "capitalization": "off",
                "smartQuotes": True,
                "trailingSpace": False,
            },
        }
    )

    assert app.cfg["model_size"] == "small"
    assert app.cfg["language"] == "en"
    assert app.cfg["punctuation"] == {
        "capitalization": "off",
        "smart_quotes": True,
        "trailing_space": False,
    }
    assert app.saved_configs[-1]["model_size"] == "small"
    assert app._transcriber.model_size == "small"
    assert app._transcriber.language == "en"


def test_helper_dictionary_add_and_remove(monkeypatch, tmp_path):
    dictionary_path = tmp_path / "dictionary.txt"
    monkeypatch.setattr(helper, "DICTIONARY_FILE", dictionary_path)
    stdout = io.StringIO()
    app = _make_helper(stdout)

    app.handle_command({"command": "addHotword", "term": "HIPAA"})
    app.handle_command(
        {"command": "addReplacement", "wrong": "hip a", "right": "HIPAA"}
    )
    app.handle_command({"command": "removeHotword", "term": "HIPAA"})
    app.handle_command({"command": "removeReplacement", "wrong": "hip a"})

    events = _events(stdout)
    dictionary_events = [
        event["dictionary"] for event in events if event["type"] == "dictionary"
    ]

    assert dictionary_events[-1]["hotwords"] == []
    assert dictionary_events[-1]["replacements"] == []
    assert dictionary_path.exists()


def test_helper_dictionary_sanitizes_input(monkeypatch, tmp_path):
    dictionary_path = tmp_path / "dictionary.txt"
    monkeypatch.setattr(helper, "DICTIONARY_FILE", dictionary_path)
    stdout = io.StringIO()
    app = _make_helper(stdout)

    app.handle_command(
        {
            "command": "addHotword",
            "term": "bad\nword\rterm\vnext\fmore\x1cfoo\x1dbar\x1ebaz\x85qux\u2028quux\u2029end",
        }
    )
    app.handle_command(
        {
            "command": "addReplacement",
            "wrong": "bad\u2028wrong\x85term",
            "right": "good\u2029right\x1eterm",
        }
    )

    content = dictionary_path.read_text(encoding="utf-8")
    assert "\nbad word term next more foo bar baz qux quux end" in content
    assert "\nbad wrong term → good right term" in content
