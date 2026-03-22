"""Post-processing find/replace for transcribed text."""
import re


def apply_replacements(text: str, rules: dict[str, str]) -> str:
    """Apply dictionary replacement rules to transcribed text.

    Each rule is a case-insensitive, word-boundary-aware find/replace.
    Rules are applied in insertion order.
    """
    if not text or not rules:
        return text

    result = text
    for pattern, replacement in rules.items():
        escaped = re.escape(pattern)
        result = re.sub(
            rf"(?<!\w){escaped}(?!\w)",
            replacement,
            result,
            flags=re.IGNORECASE,
        )
    return result
