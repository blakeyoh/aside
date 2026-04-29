from aside.commands.parser import Command
from aside.engine import transcriber as transcriber_module
from aside.engine.transcriber import Transcriber


class _Segment:
    def __init__(self, text: str):
        self.text = text


class _FakeModel:
    def __init__(self, text: str):
        self._text = text

    def transcribe(self, audio, **kwargs):
        return [_Segment(self._text)], None


def _loaded_transcriber(text: str, tmp_path) -> Transcriber:
    transcriber = Transcriber()
    transcriber._model = _FakeModel(text)
    dictionary = tmp_path / "dictionary.txt"
    dictionary.write_text("")
    transcriber._dictionary_path = dictionary
    return transcriber


def test_transcriber_injects_rendered_inline_commands(monkeypatch, tmp_path):
    injected = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )

    transcriber = _loaded_transcriber("hello comma world period", tmp_path)
    transcriber.transcribe(audio=[1])

    assert injected == ["Hello, world."]


def test_transcriber_keeps_newline_in_text_order(monkeypatch, tmp_path):
    injected = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )

    transcriber = _loaded_transcriber("first line new line second line", tmp_path)
    transcriber.transcribe(audio=[1])

    assert injected == ["First line\nSecond line"]


def test_transcriber_preserves_whisper_punctuation_as_secondary(monkeypatch, tmp_path):
    injected = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )

    transcriber = _loaded_transcriber("hello, I am here period are you there?", tmp_path)
    transcriber.transcribe(audio=[1])

    assert injected == ["Hello, I am here. Are you there?"]


def test_transcriber_executes_actions_without_punctuation_commands(monkeypatch, tmp_path):
    injected = []
    executed = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )
    monkeypatch.setattr(
        "aside.engine.transcriber.execute_commands",
        lambda commands, **kwargs: executed.extend(commands),
    )

    transcriber = _loaded_transcriber("delete that", tmp_path)
    transcriber.transcribe(audio=[1])

    assert injected == []
    assert executed == [Command.DELETE_THAT]


def test_load_model_reports_actionable_error_when_faster_whisper_missing(monkeypatch):
    statuses = []
    transcriber = Transcriber(on_status=statuses.append)
    monkeypatch.setattr(transcriber_module, "WhisperModel", None)

    transcriber.load_model()

    assert statuses == [
        "error: faster-whisper is not installed. Install dependency: pip install faster-whisper"
    ]
