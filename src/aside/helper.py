"""Stdio JSON helper for the SwiftUI spike.

The native shell supervises this process and talks to it over newline-delimited
JSON on stdin/stdout. The helper intentionally keeps the existing Python engine
ownership for the spike: hotkeys, audio capture, transcription, text injection,
dictionary handling, and config compatibility remain in Python.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import sys
import threading
import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, TextIO

from aside.config import (
    DEFAULT_CONFIG,
    DICTIONARY_FILE,
    ensure_dictionary_file,
    load_config,
    save_config,
)
from aside.dictionary.hotwords import MAX_TERMS, parse_dictionary
from aside.engine.audio import AudioCapture
from aside.engine.hotkeys import (
    HotkeyManager,
    hotkeys_equal,
    kCGEventFlagsChanged,
    kCGEventKeyDown,
    kCGEventKeyUp,
    parse_hotkey,
)
from aside.engine.transcriber import Transcriber
from aside.permissions import (
    PermissionStatus,
    check_accessibility,
    check_input_monitoring,
    check_microphone,
    request_privacy_access,
)

logger = logging.getLogger(__name__)

HELPER_PROTOCOL_VERSION = 1
POLL_INTERVAL_SECONDS = 0.01
PROTOCOL_SMOKE_ENV = "ASIDE_HELPER_PROTOCOL_SMOKE"

STATUS_LOADING = "loading"
STATUS_READY = "ready"
STATUS_RECORDING = "recording"
STATUS_TRANSCRIBING = "transcribing"
STATUS_ERROR = "error"


def normalize_engine_status(status: str) -> tuple[str, str | None]:
    """Convert engine callback strings into shell-facing state + detail."""
    if status.startswith("error:"):
        return STATUS_ERROR, status.removeprefix("error:").strip()
    if status in {
        STATUS_LOADING,
        STATUS_READY,
        STATUS_RECORDING,
        STATUS_TRANSCRIBING,
        STATUS_ERROR,
    }:
        return status, None
    return STATUS_ERROR, status


def permission_name(status: PermissionStatus) -> str:
    return status.name.lower()


def permission_snapshot() -> dict[str, str]:
    """Return current macOS permission state for the SwiftUI shell."""
    return {
        "microphone": permission_name(check_microphone()),
        "accessibility": permission_name(check_accessibility()),
        "inputMonitoring": permission_name(check_input_monitoring()),
    }


def protocol_smoke_permission_snapshot() -> dict[str, str]:
    """Return stable permission placeholders without touching macOS frameworks."""
    return {
        "microphone": "not_determined",
        "accessibility": "not_determined",
        "inputMonitoring": "not_determined",
    }


def protocol_smoke_config() -> dict[str, Any]:
    """Return isolated defaults for subprocess protocol smoke tests."""
    return deepcopy(DEFAULT_CONFIG)


def no_audio_warmup() -> None:
    """Skip native audio initialization for subprocess protocol smoke tests."""
    return None


@dataclass
class HelperDependencies:
    audio_factory: Callable[..., AudioCapture] = AudioCapture
    transcriber_factory: Callable[..., Transcriber] = Transcriber
    hotkey_factory: Callable[..., HotkeyManager] = HotkeyManager
    config_loader: Callable[[], dict[str, Any]] = load_config
    config_saver: Callable[[dict[str, Any]], bool] = save_config
    permission_snapshot_factory: Callable[[], dict[str, str]] = permission_snapshot
    audio_warmup: Callable[[], None] = AudioCapture.warmup


class ProtocolSmokeTranscriber:
    """No-op transcriber used only by explicit protocol smoke tests."""

    model_size = "base"

    def __init__(
        self,
        *,
        on_status: Callable[[str], None] | None = None,
        on_transcription: Callable[[str], None] | None = None,
        **_: Any,
    ) -> None:
        self._on_status = on_status or (lambda _: None)
        self._on_transcription = on_transcription or (lambda _: None)

    def load_model(self) -> None:
        self._on_status(STATUS_READY)

    def transcribe(self, audio: Any) -> None:
        self._on_transcription("")
        self._on_status(STATUS_READY)

    def update_punctuation(self, config: dict) -> None:
        pass

    def update_language(self, language: str | None) -> None:
        pass

    def reload_model(self, model_size: str) -> None:
        self.model_size = model_size
        self._on_status(STATUS_READY)

    def reload_dictionary(self) -> None:
        pass


class ProtocolSmokeHotkeys:
    """No-op hotkey manager used only by explicit protocol smoke tests."""

    def __init__(self, **_: Any) -> None:
        pass

    def poll(self) -> None:
        pass

    def update_hotkey(self, config: dict) -> None:
        pass

    def update_toggle_hotkey(self, config: dict | None) -> None:
        pass

    def shutdown(self) -> None:
        pass


class ProtocolSmokeAudio:
    """No-op audio capture used only by explicit protocol smoke tests."""

    def __init__(self, on_mic_denied: Callable[[], None] | None = None) -> None:
        self._on_mic_denied = on_mic_denied

    def start(self) -> bool:
        return False

    def stop(self) -> None:
        return None


def dependencies_from_environment() -> HelperDependencies:
    """Select real dependencies unless an explicit protocol-smoke env is set."""
    if os.environ.get(PROTOCOL_SMOKE_ENV) == "1":
        return HelperDependencies(
            audio_factory=ProtocolSmokeAudio,
            transcriber_factory=ProtocolSmokeTranscriber,
            hotkey_factory=ProtocolSmokeHotkeys,
            config_loader=protocol_smoke_config,
            config_saver=lambda _: True,
            permission_snapshot_factory=protocol_smoke_permission_snapshot,
            audio_warmup=no_audio_warmup,
        )
    return HelperDependencies()


class AsideStdioHelper:
    """Owns engine components and exposes a JSON command/event loop."""

    def __init__(
        self,
        *,
        stdin: TextIO = sys.stdin,
        stdout: TextIO = sys.stdout,
        dependencies: HelperDependencies | None = None,
    ) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.dependencies = dependencies or HelperDependencies()
        self._commands: queue.Queue[dict[str, Any]] = queue.Queue()
        self._stop = threading.Event()
        self._write_lock = threading.Lock()
        self._state = STATUS_LOADING
        self._toggle_active = False
        self._components_started = False

        self.cfg = self.dependencies.config_loader()
        if hotkeys_equal(self.cfg.get("hotkey"), self.cfg.get("toggle_hotkey")):
            logger.warning(
                "Toggle hotkey matched push-to-talk hotkey; disabling toggle"
            )
            self.cfg["toggle_hotkey"] = None
            self.dependencies.config_saver(self.cfg)

        self._audio = self.dependencies.audio_factory(on_mic_denied=self._on_mic_denied)
        self._transcriber = self.dependencies.transcriber_factory(
            model_size=self.cfg["model_size"],
            language=self.cfg.get("language"),
            punctuation_config=self.cfg.get("punctuation"),
            hotwords=self.cfg.get("hotwords"),
            replacements=self.cfg.get("replacements"),
            on_status=self._on_engine_status,
            on_transcription=self._on_transcription,
        )
        self._hotkeys = self.dependencies.hotkey_factory(
            hotkey_config=self.cfg.get("hotkey"),
            toggle_hotkey_config=self.cfg.get("toggle_hotkey"),
            on_event=self._on_hotkey_event,
            on_accessibility_error=self._on_accessibility_error,
        )

    @property
    def state(self) -> str:
        return self._state

    def emit(self, payload: dict[str, Any]) -> None:
        payload.setdefault("protocolVersion", HELPER_PROTOCOL_VERSION)
        with self._write_lock:
            self.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
            self.stdout.flush()

    def start(self) -> int:
        """Run until stdin closes or a shutdown command arrives."""
        self.emit({"type": "hello"})
        self.emit({"type": "config", "config": self._public_config()})
        self.emit_dictionary()
        self.emit_permissions()
        self._set_status(STATUS_LOADING)
        self._start_components()
        threading.Thread(
            target=self._read_stdin, daemon=True, name="helper-stdin"
        ).start()

        try:
            while not self._stop.is_set():
                self._poll_once()
                time.sleep(POLL_INTERVAL_SECONDS)
        finally:
            self.shutdown()
        return 0

    def _start_components(self) -> None:
        if self._components_started:
            return
        self._components_started = True
        threading.Thread(
            target=self._transcriber.load_model,
            daemon=True,
            name="model-load",
        ).start()
        threading.Thread(
            target=self.dependencies.audio_warmup,
            daemon=True,
            name="audio-warmup",
        ).start()

    def _read_stdin(self) -> None:
        for line in self.stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self.emit({"type": "error", "message": f"invalid JSON command: {exc}"})
                continue
            if isinstance(message, dict):
                self._commands.put(message)
            else:
                self.emit({"type": "error", "message": "command must be a JSON object"})
        self._stop.set()

    def _poll_once(self) -> None:
        try:
            self._hotkeys.poll()
        except Exception as exc:
            logger.exception("Hotkey polling failed")
            self._set_status(STATUS_ERROR, f"hotkey polling failed: {exc}")

        while True:
            try:
                command = self._commands.get_nowait()
            except queue.Empty:
                break
            self.handle_command(command)

    def handle_command(self, command: dict[str, Any]) -> None:
        name = command.get("command")
        if name == "startRecording":
            self._start_recording()
        elif name == "stopRecording":
            self._stop_recording()
        elif name == "getPermissions":
            self.emit_permissions()
        elif name == "requestPermission":
            pane = str(command.get("permission", ""))
            self._request_permission(pane)
        elif name == "reloadConfig":
            self._reload_config()
        elif name == "setConfig":
            self._set_config(command)
        elif name == "startHotkeyCapture":
            self._start_hotkey_capture(str(command.get("target", "hotkey")))
        elif name == "cancelHotkeyCapture":
            self._hotkeys.stop_capture()
            self.emit({"type": "capture", "target": None, "active": False})
        elif name == "clearToggleHotkey":
            self.cfg["toggle_hotkey"] = None
            self.dependencies.config_saver(self.cfg)
            self._hotkeys.update_toggle_hotkey(None)
            self.emit({"type": "config", "config": self._public_config()})
        elif name == "getDictionary":
            self.emit_dictionary()
        elif name == "addHotword":
            self._add_hotword(str(command.get("term", "")))
        elif name == "addReplacement":
            self._add_replacement(
                str(command.get("wrong", "")),
                str(command.get("right", "")),
            )
        elif name == "removeHotword":
            self._remove_hotword(str(command.get("term", "")))
        elif name == "removeReplacement":
            self._remove_replacement(str(command.get("wrong", "")))
        elif name == "openDictionary":
            self._open_dictionary()
        elif name == "shutdown":
            self._stop.set()
        else:
            self.emit({"type": "error", "message": f"unknown command: {name}"})

    def emit_permissions(self) -> None:
        self.emit(
            {
                "type": "permissions",
                "permissions": self.dependencies.permission_snapshot_factory(),
            }
        )

    def _request_permission(self, pane: str) -> None:
        pane_map = {
            "microphone": "microphone",
            "accessibility": "accessibility",
            "inputMonitoring": "input_monitoring",
        }
        if pane not in pane_map:
            self.emit({"type": "error", "message": f"unknown permission: {pane}"})
            return
        request_privacy_access(pane_map[pane])
        self.emit_permissions()

    def _reload_config(self) -> None:
        self.cfg = self.dependencies.config_loader()
        self._transcriber.update_punctuation(self.cfg.get("punctuation", {}))
        self._transcriber.update_language(self.cfg.get("language"))
        if self.cfg.get("model_size") != self._transcriber.model_size:
            self._transcriber.reload_model(self.cfg["model_size"])
        self._hotkeys.update_hotkey(self.cfg["hotkey"])
        self._hotkeys.update_toggle_hotkey(self.cfg.get("toggle_hotkey"))
        self.emit({"type": "config", "config": self._public_config()})
        self.emit_dictionary()

    def _set_config(self, command: dict[str, Any]) -> None:
        old_model_size = self.cfg.get("model_size")
        if "modelSize" in command:
            self.cfg["model_size"] = str(command["modelSize"])
        if "language" in command:
            language = command["language"]
            self.cfg["language"] = str(language) if language else None
        if "punctuation" in command and isinstance(command["punctuation"], dict):
            punctuation = command["punctuation"]
            self.cfg["punctuation"] = {
                "capitalization": punctuation.get("capitalization", "sentence"),
                "smart_quotes": bool(punctuation.get("smartQuotes", False)),
                "trailing_space": bool(punctuation.get("trailingSpace", True)),
            }

        self.dependencies.config_saver(self.cfg)
        self._transcriber.update_punctuation(self.cfg.get("punctuation", {}))
        self._transcriber.update_language(self.cfg.get("language"))
        if self.cfg.get("model_size") != old_model_size:
            self._transcriber.reload_model(self.cfg["model_size"])
        self.emit({"type": "config", "config": self._public_config()})

    def _start_hotkey_capture(self, target: str) -> None:
        if target not in {"hotkey", "toggleHotkey"}:
            self.emit({"type": "error", "message": f"unknown hotkey target: {target}"})
            return

        self.emit({"type": "capture", "target": target, "active": True})

        def on_captured(config: dict) -> None:
            if target == "hotkey":
                if hotkeys_equal(config, self.cfg.get("toggle_hotkey")):
                    self.emit({"type": "error", "message": "hotkeys must be distinct"})
                    self.emit({"type": "capture", "target": target, "active": False})
                    return
                self.cfg["hotkey"] = config
                self._hotkeys.update_hotkey(config)
            else:
                if hotkeys_equal(config, self.cfg.get("hotkey")):
                    self.emit({"type": "error", "message": "hotkeys must be distinct"})
                    self.emit({"type": "capture", "target": target, "active": False})
                    return
                self.cfg["toggle_hotkey"] = config
                self._hotkeys.update_toggle_hotkey(config)

            self.dependencies.config_saver(self.cfg)
            self.emit({"type": "capture", "target": target, "active": False})
            self.emit({"type": "config", "config": self._public_config()})

        self._hotkeys.start_capture(on_captured)

    def emit_dictionary(self) -> None:
        data = parse_dictionary(DICTIONARY_FILE)
        self.emit(
            {
                "type": "dictionary",
                "dictionary": {
                    "hotwords": data.hotwords,
                    "replacements": [
                        {"wrong": wrong, "right": right}
                        for wrong, right in data.replacements.items()
                    ],
                    "termCount": data.term_count,
                    "maxTerms": MAX_TERMS,
                    "overLimit": data.over_limit,
                },
            }
        )

    def _add_hotword(self, term: str) -> None:
        term = term.strip()
        if not term:
            self.emit({"type": "error", "message": "hotword cannot be empty"})
            return
        data = parse_dictionary(DICTIONARY_FILE)
        if data.term_count >= MAX_TERMS:
            self.emit({"type": "error", "message": "dictionary term limit reached"})
            return
        ensure_dictionary_file()
        with open(DICTIONARY_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"\n{term}")
        try:
            DICTIONARY_FILE.chmod(0o600)
        except OSError as exc:
            logger.warning(f"Could not enforce 0o600 on {DICTIONARY_FILE}: {exc}")
        self._transcriber.reload_dictionary()
        self.emit_dictionary()

    def _add_replacement(self, wrong: str, right: str) -> None:
        wrong = wrong.strip()
        right = right.strip()
        if not wrong or not right:
            self.emit(
                {"type": "error", "message": "replacement fields cannot be empty"}
            )
            return
        data = parse_dictionary(DICTIONARY_FILE)
        if data.term_count >= MAX_TERMS:
            self.emit({"type": "error", "message": "dictionary term limit reached"})
            return
        ensure_dictionary_file()
        with open(DICTIONARY_FILE, "a", encoding="utf-8") as handle:
            handle.write(f"\n{wrong} → {right}")
        try:
            DICTIONARY_FILE.chmod(0o600)
        except OSError as exc:
            logger.warning(f"Could not enforce 0o600 on {DICTIONARY_FILE}: {exc}")
        self._transcriber.reload_dictionary()
        self.emit_dictionary()

    def _remove_hotword(self, term: str) -> None:
        term = term.strip()
        data = parse_dictionary(DICTIONARY_FILE)
        if term not in data.hotwords:
            return
        data.hotwords = [hotword for hotword in data.hotwords if hotword != term]
        self._write_dictionary(data.hotwords, data.replacements)
        self._transcriber.reload_dictionary()
        self.emit_dictionary()

    def _remove_replacement(self, wrong: str) -> None:
        wrong = wrong.strip()
        data = parse_dictionary(DICTIONARY_FILE)
        if wrong not in data.replacements:
            return
        data.replacements.pop(wrong, None)
        self._write_dictionary(data.hotwords, data.replacements)
        self._transcriber.reload_dictionary()
        self.emit_dictionary()

    def _write_dictionary(
        self, hotwords: list[str], replacements: dict[str, str]
    ) -> None:
        ensure_dictionary_file()
        lines = [
            "# Aside Custom Dictionary",
            "# Managed by Aside.",
            "",
            "# HOTWORDS",
            *hotwords,
            "",
            "# REPLACEMENTS",
            *[f"{wrong} → {right}" for wrong, right in replacements.items()],
            "",
        ]
        DICTIONARY_FILE.write_text("\n".join(lines), encoding="utf-8")
        DICTIONARY_FILE.chmod(0o600)

    def _open_dictionary(self) -> None:
        ensure_dictionary_file()
        try:
            from AppKit import NSWorkspace
            from Foundation import NSURL

            url = NSURL.fileURLWithPath_(str(DICTIONARY_FILE))
            NSWorkspace.sharedWorkspace().openURL_(url)
        except Exception as exc:
            self.emit({"type": "error", "message": f"could not open dictionary: {exc}"})

    def _public_config(self) -> dict[str, Any]:
        punctuation = self.cfg.get("punctuation", {})
        return {
            "modelSize": self.cfg.get("model_size"),
            "language": self.cfg.get("language"),
            "hotkey": self.cfg.get("hotkey"),
            "toggleHotkey": self.cfg.get("toggle_hotkey"),
            "punctuation": {
                "capitalization": punctuation.get("capitalization", "sentence"),
                "smartQuotes": punctuation.get("smart_quotes", False),
                "trailingSpace": punctuation.get("trailing_space", True),
            },
        }

    def _on_hotkey_event(self, event_type: int, keycode: int, flags: int) -> None:
        hk_mod, hk_key = parse_hotkey(self.cfg["hotkey"])
        tg_cfg = self.cfg.get("toggle_hotkey")
        tg_mod, tg_key = parse_hotkey(tg_cfg) if tg_cfg else (0, -1)

        if event_type == kCGEventFlagsChanged:
            if (
                self._state == STATUS_RECORDING
                and not self._toggle_active
                and hk_mod > 0
                and (flags & hk_mod) != hk_mod
            ):
                self._stop_recording()
            return

        if hk_key >= 0 and keycode == hk_key and (flags & hk_mod) == hk_mod:
            if event_type == kCGEventKeyDown:
                self._start_recording()
            elif event_type == kCGEventKeyUp:
                self._stop_recording()
            return

        if tg_key >= 0 and keycode == tg_key and (flags & tg_mod) == tg_mod:
            if event_type == kCGEventKeyDown:
                if self._toggle_active:
                    self._stop_recording()
                else:
                    self._toggle_active = self._start_recording()

    def _start_recording(self) -> bool:
        if self._state != STATUS_READY:
            return False
        if self._audio.start():
            self._set_status(STATUS_RECORDING)
            return True
        return False

    def _stop_recording(self) -> bool:
        if self._state != STATUS_RECORDING:
            return False
        self._toggle_active = False
        self._set_status(STATUS_TRANSCRIBING)
        threading.Thread(
            target=self._run_transcription,
            daemon=True,
            name="transcribe",
        ).start()
        return True

    def _run_transcription(self) -> None:
        audio = self._audio.stop()
        if audio is not None and len(audio) > 0:
            self._transcriber.transcribe(audio)
        else:
            self._on_engine_status(STATUS_READY)

    def _on_engine_status(self, status: str) -> None:
        state, detail = normalize_engine_status(status)
        self._set_status(state, detail)

    def _on_transcription(self, text: str) -> None:
        self.emit({"type": "transcription", "text": text})

    def _on_mic_denied(self) -> None:
        self.emit_permissions()
        self._set_status(STATUS_ERROR, "microphone access denied")

    def _on_accessibility_error(self) -> None:
        self.emit_permissions()
        self._set_status(STATUS_ERROR, "could not create event tap")

    def _set_status(self, state: str, detail: str | None = None) -> None:
        self._state = state
        payload = {"type": "status", "state": state}
        if detail:
            payload["message"] = detail
        self.emit(payload)

    def shutdown(self) -> None:
        if self._state == STATUS_RECORDING:
            try:
                self._audio.stop()
            except Exception:
                logger.debug("Audio cleanup failed during shutdown", exc_info=True)
        try:
            self._hotkeys.shutdown()
        except Exception:
            logger.debug("Hotkey cleanup failed during shutdown", exc_info=True)
        self.emit({"type": "exit"})


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    return AsideStdioHelper(dependencies=dependencies_from_environment()).start()


if __name__ == "__main__":
    raise SystemExit(main())
