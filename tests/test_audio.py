from unittest.mock import MagicMock

import numpy as np

from aside.engine import audio
from aside.permissions import PermissionStatus


class FakePortAudioError(Exception):
    pass


def test_stop_closes_stream_even_when_stop_raises():
    stream = MagicMock()
    stream.stop.side_effect = RuntimeError("device vanished")
    capture = audio.AudioCapture()
    capture._stream = stream
    capture._recording = True
    capture._chunks = [np.array([[0.25]], dtype="float32")]

    result = capture.stop()

    stream.stop.assert_called_once_with()
    stream.close.assert_called_once_with()
    assert result.tolist() == [0.25]
    assert capture.is_recording is False


def test_failed_start_closes_partial_stream_and_reports_actionable_error(monkeypatch):
    stream = MagicMock()
    stream.start.side_effect = FakePortAudioError("no default device")
    errors = []
    monkeypatch.setattr(audio.sd, "PortAudioError", FakePortAudioError)
    monkeypatch.setattr(audio.sd, "InputStream", lambda **_: stream)
    monkeypatch.setattr(
        "aside.permissions.check_microphone",
        lambda: PermissionStatus.GRANTED,
    )
    capture = audio.AudioCapture(on_error=errors.append)

    assert capture.start() is False

    stream.close.assert_called_once_with()
    assert capture.is_recording is False
    assert errors == [
        "Could not open the microphone. Check that it is connected and "
        "available, then try again."
    ]


def test_warmup_closes_stream_when_stop_raises(monkeypatch):
    stream = MagicMock()
    stream.stop.side_effect = RuntimeError("stop failed")
    monkeypatch.setattr(audio.sd, "InputStream", lambda **_: stream)

    audio.AudioCapture.warmup()

    stream.close.assert_called_once_with()
