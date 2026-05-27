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
from dataclasses import dataclass
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
] + [(phrase, cmd, False) for phrase, cmd in _ACTION_PHRASES]

_PHRASE_LOOKUP = {
    phrase: (cmd, is_dictation) for phrase, cmd, is_dictation in _ALL_PHRASES
}
_PHRASE_PATTERN = re.compile(
    r"\b("
    + "|".join(
        re.escape(phrase) for phrase in sorted(_PHRASE_LOOKUP, key=len, reverse=True)
    )
    + r")\b",
    re.IGNORECASE,
)

_DICTATION_OUTPUT = {
    Command.PERIOD: ".",
    Command.COMMA: ",",
    Command.QUESTION_MARK: "?",
    Command.EXCLAMATION: "!",
    Command.NEW_LINE: "\n",
    Command.NEW_PARAGRAPH: "\n\n",
}
_PUNCTUATION_COMMANDS = {
    Command.PERIOD,
    Command.COMMA,
    Command.QUESTION_MARK,
    Command.EXCLAMATION,
}
_ACTION_COMMANDS = {
    Command.DELETE_THAT,
    Command.UNDO,
    Command.SELECT_ALL,
    Command.COPY,
}
_MODE_COMMANDS = {
    Command.NUMBERS_MODE,
    Command.WORDS_MODE,
}
_ARTIFACT_PUNCT = ".?!,;:"


@dataclass(frozen=True)
class ParsedTranscript:
    """Parsed voice-command result with both legacy and rendered text forms."""

    commands: list[Command]
    cleaned_text: str
    rendered_text: str
    action_commands: list[Command]
    mode_commands: list[Command]


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


def parse_transcript(text: str) -> ParsedTranscript:
    """Parse text and render inline dictation commands in source order."""
    if not text or not text.strip():
        return ParsedTranscript([], text, text, [], [])

    source = text.strip()
    lower = source.lower()
    commands: list[Command] = []
    clean_parts: list[str] = []
    render_parts: list[str] = []
    cursor = 0

    for match in _PHRASE_PATTERN.finditer(source):
        if match.start() < cursor:
            continue

        phrase = match.group(0).lower()
        cmd, is_dictation = _PHRASE_LOOKUP[phrase]
        start, end = match.start(), match.end()

        if not is_dictation:
            before_bound = _is_sentence_boundary_before(lower, start)
            after_bound = _is_sentence_boundary_after(lower, end)
            if not (before_bound or after_bound):
                continue

        before_text = source[cursor:start]
        skip_end = end

        if is_dictation:
            before_text = _strip_preceding_artifact(before_text, cmd)
            skip_end = _skip_following_artifact(source, end)

        _append_text(clean_parts, before_text)
        _append_text(render_parts, before_text)
        commands.append(cmd)

        if is_dictation:
            _append_dictation_output(render_parts, cmd)

        cursor = skip_end

    tail = source[cursor:]
    _append_text(clean_parts, tail)
    _append_text(render_parts, tail)

    return ParsedTranscript(
        commands=commands,
        cleaned_text="".join(clean_parts).strip(),
        rendered_text="".join(render_parts).strip(" \t"),
        action_commands=[cmd for cmd in commands if cmd in _ACTION_COMMANDS],
        mode_commands=[cmd for cmd in commands if cmd in _MODE_COMMANDS],
    )


def _append_text(parts: list[str], text: str) -> None:
    chunk = re.sub(r"\s+", " ", text).strip()
    if not chunk:
        return
    if parts:
        for i in range(len(parts) - 1, -1, -1):
            if parts[i]:
                if parts[i][-1] not in (" ", "\n"):
                    parts.append(" ")
                break
    parts.append(chunk)


def _rstrip_parts(parts: list[str]) -> None:
    if not parts:
        return
    parts[-1] = parts[-1].rstrip()
    if not parts[-1]:
        parts.pop()


def _strip_preceding_artifact(text: str, cmd: Command) -> str:
    if cmd not in _PUNCTUATION_COMMANDS:
        return text
    return re.sub(rf"\s*[{re.escape(_ARTIFACT_PUNCT)}]\s*$", " ", text)


def _skip_following_artifact(text: str, start: int) -> int:
    match = re.match(rf"\s*[{re.escape(_ARTIFACT_PUNCT)}]", text[start:])
    if match:
        return start + match.end()
    return start


def _append_dictation_output(parts: list[str], cmd: Command) -> None:
    output = _DICTATION_OUTPUT.get(cmd)
    if not output:
        return

    _rstrip_parts(parts)
    if output.startswith("\n"):
        parts.append(output)
        return

    for i in range(len(parts) - 1, -1, -1):
        if parts[i]:
            if parts[i][-1] in _ARTIFACT_PUNCT:
                parts[-1] = parts[-1].rstrip(_ARTIFACT_PUNCT).rstrip()
            break
    parts.append(output)
