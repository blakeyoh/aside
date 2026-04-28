"""Post-processing find/replace for transcribed text."""
import re


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
            escaped = re.escape(pattern)
            result = re.sub(
                rf"(?<!\w){escaped}(?!\w)",
                replacement,
                result,
                flags=re.IGNORECASE,
            )
    else:
        for pattern, replacement in rules:
            result = pattern.sub(replacement, result)

    return result
