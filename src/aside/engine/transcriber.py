"""Whisper transcription pipeline conductor.

Orchestrates the 8-stage pipeline:
1. Hotkey Detection (handled by HotkeyManager)
2. Audio Capture (handled by AudioCapture)
3. Dictionary Pre-Processing → hotwords + initial_prompt
4. Whisper Transcription → raw text
5. Voice Command Detection → commands + cleaned text
6. Post-Processing → replacements + punctuation
7. Text Injection → characters at cursor
8. Context Update → rolling buffer

Stages 3-8 happen in this module's transcribe() method.
"""
import logging
import threading
from pathlib import Path
from typing import Callable, Optional

from aside.commands.actions import execute_commands
from aside.commands.numbers import NumberMode
from aside.commands.parser import Command, parse_commands
from aside.config import DICTIONARY_FILE
from aside.dictionary.context import ContextBuffer
from aside.dictionary.hotwords import parse_dictionary
from aside.dictionary.replacements import apply_replacements
from aside.engine.injector import inject_text, inject_keystroke
from aside.punctuation.formatter import format_text

try:
    from faster_whisper import WhisperModel
except ImportError as e:
    raise SystemExit(f"faster-whisper not installed — run setup.sh\n{e}")

logger = logging.getLogger(__name__)


class Transcriber:
    """Manages Whisper model and runs the transcription pipeline."""

    def __init__(
        self,
        model_size: str = "base",
        language: str | None = None,
        punctuation_config: dict | None = None,
        on_status: Callable[[str], None] | None = None,
        on_transcription: Callable[[str], None] | None = None,
    ):
        self._model: WhisperModel | None = None
        self._lock = threading.Lock()
        self.model_size = model_size
        self.language = language
        self._punctuation_config = punctuation_config or {
            "capitalization": "sentence",
            "smart_quotes": False,
            "trailing_space": True,
        }
        self._on_status = on_status or (lambda _: None)
        self._on_transcription = on_transcription or (lambda _: None)

        # Pipeline state
        self._context = ContextBuffer()
        self._number_mode = NumberMode()
        self._last_injection_length = 0
        self._dictionary_path = DICTIONARY_FILE

    def load_model(self) -> None:
        """Load Whisper model (call from background thread)."""
        try:
            model = WhisperModel(self.model_size, device="cpu", compute_type="int8")
            with self._lock:
                self._model = model
            self._on_status("ready")
        except Exception as exc:
            self._on_status(f"error: {exc}")

    def reload_model(self, model_size: str) -> None:
        """Swap to a different model size (async)."""
        with self._lock:
            self._model = None
        self.model_size = model_size
        self._on_status("loading")
        threading.Thread(target=self.load_model, daemon=True).start()

    @property
    def model_loaded(self) -> bool:
        with self._lock:
            return self._model is not None

    def transcribe(self, audio) -> None:
        """Run the full pipeline: Stages 3-8. Call from background thread."""
        try:
            with self._lock:
                model = self._model
            if model is None:
                self._on_status("ready")
                return

            # Stage 3: Dictionary Pre-Processing
            dict_data = parse_dictionary(self._dictionary_path)
            hotwords_str = dict_data.whisper_hotwords or None
            initial_prompt = self._context.build_initial_prompt(dict_data.hotwords) or None

            # Stage 4: Whisper Transcription
            kwargs = {"vad_filter": True}
            if self.language:
                kwargs["language"] = self.language
            if hotwords_str:
                kwargs["hotwords"] = hotwords_str
            if initial_prompt:
                kwargs["initial_prompt"] = initial_prompt

            segments, _info = model.transcribe(audio, **kwargs)
            raw_text = "".join(seg.text for seg in segments).strip()

            if not raw_text:
                self._on_status("ready")
                return

            # Stage 5: Voice Command Detection
            commands, cleaned_text = parse_commands(raw_text)

            # Handle number mode toggles
            for cmd in commands:
                if cmd == Command.NUMBERS_MODE:
                    self._number_mode.activate()
                elif cmd == Command.WORDS_MODE:
                    self._number_mode.deactivate()

            # Apply number mode to remaining text
            if self._number_mode.is_active and cleaned_text:
                cleaned_text = self._number_mode.process(cleaned_text)

            # Stage 6: Post-Processing
            if cleaned_text:
                cleaned_text = apply_replacements(cleaned_text, dict_data.replacements)
                cleaned_text = format_text(
                    cleaned_text,
                    capitalization=self._punctuation_config.get("capitalization", "sentence"),
                    smart_quotes=self._punctuation_config.get("smart_quotes", False),
                    trailing_space=self._punctuation_config.get("trailing_space", True),
                )

            # Stage 7: Text Injection
            non_toggle_cmds = [c for c in commands if c not in (Command.NUMBERS_MODE, Command.WORDS_MODE)]
            if non_toggle_cmds:
                execute_commands(
                    non_toggle_cmds,
                    inject_text_fn=inject_text,
                    inject_keystroke_fn=inject_keystroke,
                    last_injection_length=self._last_injection_length,
                )

            if cleaned_text:
                chars_injected = inject_text(cleaned_text)
                self._last_injection_length = chars_injected

            # Stage 8: Context Update
            if cleaned_text:
                self._context.append(cleaned_text)

            self._on_transcription(raw_text)
            self._on_status("ready")

        except Exception as exc:
            logger.error("Transcription failed: %s", exc)
            self._on_status(f"error: {exc}")

    def update_punctuation(self, config: dict) -> None:
        self._punctuation_config = config

    def update_language(self, language: str | None) -> None:
        self.language = language

    def reload_dictionary(self) -> None:
        """Force re-read of dictionary file (called after UI edits)."""
        pass
