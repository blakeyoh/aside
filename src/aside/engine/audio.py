"""Audio capture via sounddevice.

Manages InputStream lifecycle. Accumulates numpy chunks during recording.
stream.stop() MUST be called from a background thread (it blocks).
"""

import logging
import numpy as np
import sounddevice as sd
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class AudioCapture:
    """Manages audio recording sessions."""

    def __init__(self, on_mic_denied: Optional[Callable[[], None]] = None):
        self._stream: Optional[sd.InputStream] = None
        self._chunks: list = []
        self._recording = False
        self._on_mic_denied = on_mic_denied

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self) -> bool:
        """Start recording. Returns True on success."""
        if self._recording:
            return False

        from aside.permissions import check_microphone, PermissionStatus

        if check_microphone() == PermissionStatus.DENIED:
            logger.warning("Microphone access denied")
            if self._on_mic_denied:
                self._on_mic_denied()
            return False

        self._chunks = []
        self._recording = True

        def callback(indata, *_):
            if self._recording:
                self._chunks.append(indata.copy())

        try:
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=callback,
            )
            self._stream.start()
            return True
        except sd.PortAudioError as exc:
            self._recording = False
            logger.error("Microphone unavailable: %s", exc)
            return False

    def stop(self) -> np.ndarray | None:
        """Stop recording and return audio as 1D numpy array.

        MUST be called from a background thread (stream.stop() blocks).
        Returns None if no audio was captured.
        """
        self._recording = False
        stream = self._stream
        self._stream = None
        chunks = self._chunks
        self._chunks = []

        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass

        if not chunks:
            return None
        return np.concatenate(chunks).flatten()

    @staticmethod
    def warmup() -> None:
        """Pre-initialize PortAudio to avoid first-recording latency."""
        try:
            s = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=lambda *_: None,
            )
            s.start()
            s.stop()
            s.close()
        except Exception:
            pass
