"""Post-processing find/replace for transcribed text."""

import functools
import re


@functools.lru_cache(maxsize=512)
def _get_compiled_pattern(pattern: str) -> re.Pattern:
    """Compile and cache a word-boundary-aware regex pattern."""
    escaped = re.escape(pattern)
    return re.compile(rf"(?<!\w){escaped}(?!\w)", flags=re.IGNORECASE)


def apply_replacements(
    text: str, rules: dict[str, str] | list[tuple[re.Pattern, str]]
) -> str:
    """Apply dictionary replacement rules to transcribed text.

    Each rule is a case-insensitive, word-boundary-aware find/replace.
    Rules are applied in insertion order.

    The `rules` parameter can be a dictionary of {pattern: replacement}
    or a list of (compiled_regex_pattern, replacement) tuples for better performance.
    """
    if not text or not rules:
        return text

    result = text
    if isinstance(rules, dict):
        for pattern, replacement in rules.items():
            compiled_pattern = _get_compiled_pattern(pattern)
            result = compiled_pattern.sub(replacement, result)
    else:
        for pattern, replacement in rules:
            result = pattern.sub(replacement, result)

    return result
