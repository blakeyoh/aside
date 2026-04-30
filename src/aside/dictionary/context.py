"""Rolling context buffer for Whisper's initial_prompt parameter."""
from collections import deque


class ContextBuffer:
    """Maintains a FIFO buffer of recent transcriptions.

    Builds initial_prompt by combining a glossary priming sentence
    with the rolling context window.
    """

    def __init__(self, max_entries: int = 3, max_tokens: int = 500):
        self._buffer: deque[str] = deque(maxlen=max_entries)
        self._max_tokens = max_tokens

    def append(self, text: str) -> None:
        """Add a transcription to the context buffer."""
        stripped = text.strip()
        if stripped:
            self._buffer.append(stripped)

    def build_initial_prompt(self, hotwords: list[str]) -> str:
        """Build initial_prompt from glossary terms + rolling context.

        Format: "Terms: HIPAA, PHI. [previous transcriptions joined by space]"
        Truncated to ~max_tokens words.
        """
        parts: list[str] = []

        if hotwords:
            terms = ", ".join(hotwords)
            parts.append(f"Terms: {terms}.")

        if self._buffer:
            context = " ".join(self._buffer)
            parts.append(context)

        if not parts:
            return ""

        combined = " ".join(parts)
        return self._truncate(combined)

    def _truncate(self, text: str) -> str:
        """Truncate to approximately max_tokens words."""
        words = text.split()
        if len(words) <= self._max_tokens:
            return text
        return " ".join(words[:self._max_tokens])
