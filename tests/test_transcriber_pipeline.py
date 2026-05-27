from aside.commands.parser import Command
from aside.engine import transcriber as transcriber_module
from aside.engine.transcriber import Transcriber


class _Segment:
    def __init__(self, text: str):
        self.text = text


class _FakeModel:
    def __init__(self, text: str):
        self._text = text
        self.kwargs = None

    def transcribe(self, audio, **kwargs):
        self.kwargs = kwargs
        return [_Segment(self._text)], None


def _loaded_transcriber(
    text: str,
    tmp_path,
    *,
    hotwords=None,
    replacements=None,
    dictionary_text: str = "",
    **kwargs,
) -> Transcriber:
    transcriber = Transcriber(hotwords=hotwords, replacements=replacements, **kwargs)
    transcriber._model = _FakeModel(text)
    dictionary = tmp_path / "dictionary.txt"
    dictionary.write_text(dictionary_text)
    transcriber._dictionary_path = dictionary
    return transcriber


def _capture_injections(monkeypatch) -> list[str]:
    injected: list[str] = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )
    return injected


# ── rendering / command pipeline ────────────────────────────────────────


def test_transcriber_injects_rendered_inline_commands(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("hello comma world period", tmp_path)
    transcriber.transcribe(audio=[1])
    assert injected == ["Hello, world."]


def test_transcriber_keeps_newline_in_text_order(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("first line new line second line", tmp_path)
    transcriber.transcribe(audio=[1])
    assert injected == ["First line\nSecond line"]


def test_transcriber_preserves_whisper_punctuation_as_secondary(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("hello, I am here period are you there?", tmp_path)
    transcriber.transcribe(audio=[1])
    assert injected == ["Hello, I am here. Are you there?"]


def test_transcriber_executes_actions_without_punctuation_commands(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    executed = []
    monkeypatch.setattr(
        "aside.engine.transcriber.execute_commands",
        lambda commands, **kwargs: executed.extend(commands),
    )

    transcriber = _loaded_transcriber("delete that", tmp_path)
    transcriber.transcribe(audio=[1])

    assert injected == []
    assert executed == [Command.DELETE_THAT]


# ── replacements (folded in from test_default_replacements.py) ───────────


def test_transcriber_applies_default_replacements(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber(
        "alright then", tmp_path, replacements={"alright": "all right"}
    )
    transcriber.transcribe(audio=[1])
    assert injected == ["All right then"]


def test_transcriber_user_dictionary_overrides_default_replacements(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber(
        "alright then",
        tmp_path,
        replacements={"alright": "all right"},
        dictionary_text="alright → okay",
    )
    transcriber.transcribe(audio=[1])
    assert injected == ["Okay then"]


# ── stateful number mode persists across transcriptions ──────────────────


def test_number_mode_persists_across_transcriptions(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("numbers mode", tmp_path)

    transcriber.transcribe(audio=[1])  # toggles numbers mode on, injects nothing
    assert injected == []

    transcriber._model = _FakeModel("call one two now")
    transcriber.transcribe(audio=[1])
    assert injected == ["Call 12 now"]


# ── dictionary mtime cache ───────────────────────────────────────────────


def test_dictionary_parsed_once_until_reload(monkeypatch, tmp_path):
    calls = []
    real_parse = transcriber_module.parse_dictionary
    monkeypatch.setattr(
        transcriber_module,
        "parse_dictionary",
        lambda path: calls.append(path) or real_parse(path),
    )
    _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("hello", tmp_path)

    transcriber.transcribe(audio=[1])
    transcriber.transcribe(audio=[1])
    assert len(calls) == 1  # unchanged mtime → cached

    transcriber.reload_dictionary()
    transcriber.transcribe(audio=[1])
    assert len(calls) == 2  # cache invalidated → re-read


# ── empty transcription is a no-op that returns to ready ─────────────────


def test_empty_transcription_injects_nothing_and_reports_ready(monkeypatch, tmp_path):
    injected = _capture_injections(monkeypatch)
    statuses = []
    transcriber = _loaded_transcriber("   ", tmp_path, on_status=statuses.append)

    transcriber.transcribe(audio=[1])

    assert injected == []
    assert statuses[-1] == "ready"


# ── decode kwargs and context buffer ─────────────────────────────────────


def test_language_hotwords_and_initial_prompt_reach_the_model(monkeypatch, tmp_path):
    _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber(
        "hello", tmp_path, hotwords=["HIPAA"], language="es"
    )
    transcriber._context.append("earlier sentence")

    transcriber.transcribe(audio=[1])

    kwargs = transcriber._model.kwargs
    assert kwargs["vad_filter"] is True
    assert kwargs["language"] == "es"
    assert "HIPAA" in kwargs["hotwords"]
    assert "HIPAA" in kwargs["initial_prompt"]


def test_successful_transcription_appends_to_context(monkeypatch, tmp_path):
    _capture_injections(monkeypatch)
    transcriber = _loaded_transcriber("hello world", tmp_path)

    transcriber.transcribe(audio=[1])

    assert "Hello world" in list(transcriber._context._buffer)


# ── model load error ─────────────────────────────────────────────────────


def test_load_model_reports_actionable_error_when_faster_whisper_missing(monkeypatch):
    statuses = []
    transcriber = Transcriber(on_status=statuses.append)
    monkeypatch.setattr(transcriber_module, "WhisperModel", None)

    transcriber.load_model()

    assert statuses == [
        "error: faster-whisper is not installed. Install dependency: pip install faster-whisper"
    ]
