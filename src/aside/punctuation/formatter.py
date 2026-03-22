"""Auto-punctuation formatting for transcribed text.

Three configurable settings:
- capitalization: "sentence" | "as-spoken" | "off"
- smart_quotes: bool
- trailing_space: bool (space after punctuation marks)
"""
import re

_SENTENCE_ENDINGS = ".?!"


def format_text(
    text: str,
    *,
    capitalization: str = "sentence",
    smart_quotes: bool = False,
    trailing_space: bool = True,
) -> str:
    """Apply punctuation formatting to transcribed text."""
    if not text or text.isspace():
        return text

    result = text

    # Trailing space: ensure space after punctuation (before applying capitalization)
    if trailing_space:
        result = _ensure_trailing_space(result)

    # Capitalization
    if capitalization == "sentence":
        result = _sentence_case(result)
    elif capitalization == "off":
        result = result.lower()
    # "as-spoken" — no change

    # Smart quotes
    if smart_quotes:
        result = _apply_smart_quotes(result)

    return result


def _ensure_trailing_space(text: str) -> str:
    """Add space after punctuation marks if not already present."""
    result = re.sub(r'([.?!,;:])([^\s])', r'\1 \2', text)
    result = re.sub(r'  +', ' ', result)
    return result


def _sentence_case(text: str) -> str:
    """Capitalize first letter and first letter after sentence-ending punctuation."""
    if not text:
        return text

    chars = list(text)
    capitalize_next = True

    for i, ch in enumerate(chars):
        if capitalize_next and ch.isalpha():
            chars[i] = ch.upper()
            capitalize_next = False
        elif ch in _SENTENCE_ENDINGS:
            capitalize_next = True

    return "".join(chars)


def _apply_smart_quotes(text: str) -> str:
    """Replace straight quotes with curly/smart quotes."""
    result = text
    result = re.sub(r'"([^"]*)"', '\u201c\\1\u201d', result)
    result = result.replace("'", "\u2019")
    return result
