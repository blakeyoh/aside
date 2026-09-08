"""Audio capture via sounddevice.

Manages InputStream lifecycle. Accumulates numpy chunks during recording.
stream.stop() MUST be called from a background thread (it blocks).
"""

import logging
import threading
import numpy as np
import sounddevice as sd
from typing import Callable, Optional

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000


class AudioCapture:
    """Manages audio recording sessions."""

    def __init__(
        self,
        on_mic_denied: Optional[Callable[[], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        self._stream: Optional[sd.InputStream] = None
        self._chunks: list = []
        self._recording = False
        self._on_mic_denied = on_mic_denied
        self._on_error = on_error
        self._lock = threading.Lock()

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def start(self) -> bool:
        """Start recording. Returns True on success."""
        with self._lock:
            if self._recording:
                return False

        from aside.permissions import check_microphone, PermissionStatus

        if check_microphone() == PermissionStatus.DENIED:
            logger.warning("Microphone access denied")
            if self._on_mic_denied:
                self._on_mic_denied()
            return False

        with self._lock:
            self._chunks = []
            self._recording = True

        def callback(indata, *_):
            with self._lock:
                if self._recording:
                    self._chunks.append(indata.copy())

        stream = None
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=callback,
            )
            stream.start()
            with self._lock:
                if self._recording:
                    self._stream = stream
                    stream = None
            if stream is not None:
                try:
                    stream.stop()
                except Exception:
                    logger.debug("Abandoned audio stream stop failed", exc_info=True)
                finally:
                    try:
                        stream.close()
                    except Exception:
                        logger.debug(
                            "Abandoned audio stream close failed", exc_info=True
                        )
                return False
            return True
        except sd.PortAudioError as exc:
            with self._lock:
                self._recording = False
                self._stream = None
                self._chunks = []
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    logger.debug("Failed to close unusable audio stream", exc_info=True)
            logger.error("Microphone unavailable: %s", exc)
            if self._on_error:
                self._on_error(
                    "Could not open the microphone. Check that it is connected "
                    "and available, then try again."
                )
            return False

    def stop(self) -> np.ndarray | None:
        """Stop recording and return audio as 1D numpy array.

        MUST be called from a background thread (stream.stop() blocks).
        Returns None if no audio was captured.
        """
        with self._lock:
            self._recording = False
            stream = self._stream
            self._stream = None
            chunks = self._chunks
            self._chunks = []

        if stream is not None:
            try:
                stream.stop()
            except Exception:
                logger.debug("Audio stream stop failed", exc_info=True)
            finally:
                try:
                    stream.close()
                except Exception:
                    logger.debug("Audio stream close failed", exc_info=True)

        if not chunks:
            return None
        return np.concatenate(chunks).flatten()

    @staticmethod
    def warmup() -> None:
        """Pre-initialize PortAudio to avoid first-recording latency."""
        stream = None
        try:
            stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=lambda *_: None,
            )
            stream.start()
            stream.stop()
        except Exception:
            logger.debug("Audio warmup failed", exc_info=True)
        finally:
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    logger.debug("Audio warmup close failed", exc_info=True)
