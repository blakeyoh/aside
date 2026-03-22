"""Detect voice commands in transcribed text.

Commands trigger at sentence boundaries: start/end of text, or after punctuation.
Embedded phrases (e.g., "I'll delete that section") do not trigger.

Two categories of commands:
- Dictation commands (punctuation/formatting): always trigger when spoken as a
  standalone word/phrase (not embedded within other words).
- Action commands (edit/mode): only trigger at sentence boundaries (start/end of
  text, or immediately after punctuation).
"""
import re
from enum import Enum, auto


class Command(Enum):
    NEW_LINE = auto()
    NEW_PARAGRAPH = auto()
    PERIOD = auto()
    COMMA = auto()
    QUESTION_MARK = auto()
    EXCLAMATION = auto()
    DELETE_THAT = auto()
    UNDO = auto()
    SELECT_ALL = auto()
    COPY = auto()
    NUMBERS_MODE = auto()
    WORDS_MODE = auto()


# Punctuation characters that create a command boundary
_BOUNDARY_PUNCT = ".?!,;:"

# Dictation commands: always trigger when recognized at a word boundary
# (not embedded within other words, but can be surrounded by other words/commands)
_DICTATION_PHRASES: list[tuple[str, Command]] = [
    ("new paragraph", Command.NEW_PARAGRAPH),
    ("new line", Command.NEW_LINE),
    ("newline", Command.NEW_LINE),
    ("full stop", Command.PERIOD),
    ("question mark", Command.QUESTION_MARK),
    ("exclamation point", Command.EXCLAMATION),
    ("exclamation mark", Command.EXCLAMATION),
    ("period", Command.PERIOD),
    ("comma", Command.COMMA),
]

# Action commands: only trigger at sentence boundaries (start/end of text or
# immediately after punctuation) to prevent accidental mid-sentence triggers
_ACTION_PHRASES: list[tuple[str, Command]] = [
    ("delete that", Command.DELETE_THAT),
    ("select all", Command.SELECT_ALL),
    ("copy that", Command.COPY),
    ("copy all", Command.COPY),
    ("undo", Command.UNDO),
    ("numbers mode", Command.NUMBERS_MODE),
    ("words mode", Command.WORDS_MODE),
]

# All phrases for exhaustive matching, dictation first (longest match wins)
_ALL_PHRASES: list[tuple[str, Command, bool]] = [
    (phrase, cmd, True) for phrase, cmd in _DICTATION_PHRASES
] + [
    (phrase, cmd, False) for phrase, cmd in _ACTION_PHRASES
]


def _is_sentence_boundary_before(text: str, start: int) -> bool:
    """Return True if `start` is a sentence-level boundary (start of text or after punct)."""
    if start == 0:
        return True
    before = text[:start].rstrip()
    return bool(before) and before[-1] in _BOUNDARY_PUNCT


def _is_sentence_boundary_after(text: str, end: int) -> bool:
    """Return True if `end` is a sentence-level boundary (end of text or before punct)."""
    if end >= len(text):
        return True
    after = text[end:].lstrip()
    return not after or after[0] in _BOUNDARY_PUNCT


def parse_commands(text: str) -> tuple[list[Command], str]:
    """Parse voice commands from transcribed text.

    Returns (list_of_commands, cleaned_text_without_commands).

    Dictation commands (punctuation/formatting) trigger whenever spoken as a
    standalone phrase — they can appear anywhere in the utterance.

    Action commands (delete, undo, copy, etc.) only trigger at sentence
    boundaries: start of text, end of text, or immediately after punctuation.
    """
    if not text or not text.strip():
        return [], text

    commands: list[Command] = []
    working = text.strip()

    # Multiple passes — extract commands until no more found
    changed = True
    while changed:
        changed = False
        lower = working.lower()

        for phrase, cmd, is_dictation in _ALL_PHRASES:
            pattern = re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)

            for match in pattern.finditer(lower):
                start, end = match.start(), match.end()

                if is_dictation:
                    # Dictation commands: trigger at any word boundary (no embedded
                    # partial matches — \b already ensures word boundary)
                    triggers = True
                else:
                    # Action commands: require sentence-level boundary on at least
                    # one side, AND not mid-sentence (both sides surrounded by words)
                    before_bound = _is_sentence_boundary_before(lower, start)
                    after_bound = _is_sentence_boundary_after(lower, end)
                    triggers = before_bound or after_bound

                if triggers:
                    commands.append(cmd)
                    before_text = working[:start].rstrip()
                    after_text = working[end:].lstrip()
                    if before_text and after_text:
                        working = before_text + " " + after_text
                    else:
                        working = before_text + after_text
                    changed = True
                    break

            if changed:
                break

    return commands, working.strip()
