import pytest
from aside.engine.transcriber import Transcriber

class _Segment:
    def __init__(self, text: str):
        self.text = text

class _FakeModel:
    def __init__(self, text: str):
        self._text = text

    def transcribe(self, audio, **kwargs):
        return [_Segment(self._text)], None

def _loaded_transcriber(text: str, tmp_path, hotwords=None, replacements=None) -> Transcriber:
    transcriber = Transcriber(hotwords=hotwords, replacements=replacements)
    transcriber._model = _FakeModel(text)
    dictionary = tmp_path / "dictionary.txt"
    dictionary.write_text("")
    transcriber._dictionary_path = dictionary
    return transcriber

def test_transcriber_applies_default_replacements(monkeypatch, tmp_path):
    injected = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )

    replacements = {"alright": "all right"}
    transcriber = _loaded_transcriber("alright then", tmp_path, replacements=replacements)
    # Mocking format_text to avoid capitalization interference if needed,
    # but here we can just check if "all right" is in the result.
    transcriber.transcribe(audio=[1])

    # "alright then" -> "all right then" -> "All right then" (due to default capitalization)
    assert injected == ["All right then"]

def test_transcriber_user_replacements_override_defaults(monkeypatch, tmp_path):
    injected = []
    monkeypatch.setattr(
        "aside.engine.transcriber.inject_text",
        lambda text: injected.append(text) or len(text),
    )

    default_reps = {"alright": "all right"}
    transcriber = _loaded_transcriber("alright then", tmp_path, replacements=default_reps)

    # User dictionary replacement
    dictionary = tmp_path / "dictionary.txt"
    dictionary.write_text("alright \u2192 okay")
    transcriber._dictionary_path = dictionary

    transcriber.transcribe(audio=[1])

    assert injected == ["Okay then"]
