"""Number dictation mode — convert spoken numbers to digits."""


_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19,
}

_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}


class NumberMode:
    """Stateful number dictation toggle.

    When active, converts number words to digit strings.
    Consecutive number tokens are concatenated without spaces;
    non-number words retain normal space separation.
    State persists across transcriptions until explicitly toggled off.
    """

    def __init__(self) -> None:
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def reset(self) -> None:
        self._active = False

    def process(self, text: str) -> str:
        """Convert number words to digits if active. Pass through unchanged if not."""
        if not self._active:
            return text

        words = text.lower().split()
        # Each element is either a digit string (from a number word) or a plain word.
        # We tag each token so we can join runs of digits without spaces.
        tokens: list[tuple[str, bool]] = []  # (value, is_number)
        i = 0

        while i < len(words):
            word = words[i]

            # "hundred" attaches to the preceding number token
            if word == "hundred" and tokens and tokens[-1][1]:
                prev_val = int(tokens.pop()[0])
                accumulated = prev_val * 100
                i += 1
                # Consume optional tens+ones after "hundred"
                if i < len(words):
                    parsed = self._parse_number_word(words, i)
                    if parsed is not None:
                        num, consumed = parsed
                        accumulated += num
                        i += consumed
                tokens.append((str(accumulated), True))
                continue

            parsed = self._parse_number_word(words, i)
            if parsed is not None:
                num, consumed = parsed
                tokens.append((str(num), True))
                i += consumed
                continue

            tokens.append((words[i], False))
            i += 1

        return _join_tokens(tokens)

    def _parse_number_word(self, words: list[str], i: int) -> tuple[int, int] | None:
        """Try to parse a number starting at position i.

        Returns (value, words_consumed) or None.
        """
        word = words[i]

        if word in _ONES:
            return _ONES[word], 1

        if word in _TENS:
            val = _TENS[word]
            if i + 1 < len(words) and words[i + 1] in _ONES and _ONES[words[i + 1]] < 10:
                return val + _ONES[words[i + 1]], 2
            return val, 1

        return None


def _join_tokens(tokens: list[tuple[str, bool]]) -> str:
    """Join tokens so that consecutive number runs are concatenated and
    text tokens are space-separated from each other and from number runs."""
    if not tokens:
        return ""

    parts: list[str] = []
    run: list[str] = []
    prev_is_number: bool | None = None

    for value, is_number in tokens:
        if is_number:
            if prev_is_number is False:
                # flush text before starting a number run
                if run:
                    parts.append(" ".join(run))
                    run = []
            run.append(value)
        else:
            if prev_is_number is True:
                # flush number run before starting text
                if run:
                    parts.append("".join(run))
                    run = []
            run.append(value)
        prev_is_number = is_number

    # flush remaining
    if run:
        if prev_is_number:
            parts.append("".join(run))
        else:
            parts.append(" ".join(run))

    return " ".join(parts)
