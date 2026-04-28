"""Parse ~/.aside/dictionary.txt into hotwords and replacement rules."""
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_TERMS = 50
ARROW = "→"


@dataclass
class DictionaryData:
    """Parsed dictionary contents."""
    hotwords: list[str] = field(default_factory=list)
    replacements: dict[str, str] = field(default_factory=dict)
    compiled_replacements: list[tuple[re.Pattern, str]] = field(default_factory=list)
    over_limit: bool = False

    @property
    def term_count(self) -> int:
        return len(self.hotwords) + len(self.replacements)

    @property
    def whisper_hotwords(self) -> str:
        """Space-joined hotwords string for faster-whisper's hotwords param."""
        return " ".join(self.hotwords)


def parse_dictionary(path: Path) -> DictionaryData:
    """Parse a dictionary file into hotwords and replacements.

    - Lines starting with # are comments (ignored)
    - Blank/whitespace lines are ignored
    - Lines containing → are replacements (first → is delimiter)
    - All other lines are hotwords
    - 50-term cap (hotwords + replacements combined)
    - Duplicates silently skipped
    """
    data = DictionaryData()

    if not path.exists():
        return data

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("Cannot read dictionary at %s: %s", path, exc)
        return data

    seen: set[str] = set()
    total = 0

    for line_num, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if total >= MAX_TERMS:
            data.over_limit = True
            break

        if ARROW in line:
            parts = line.split(ARROW, maxsplit=1)
            key = parts[0].strip()
            value = parts[1].strip()
            if not key or not value:
                logger.warning("Malformed replacement at line %d: %r", line_num, raw_line)
                continue
            if key in seen:
                continue
            seen.add(key)
            data.replacements[key] = value

            # Pre-compile for performance (case-insensitive, word-boundary aware)
            escaped = re.escape(key)
            pattern = re.compile(rf"(?<!\w){escaped}(?!\w)", flags=re.IGNORECASE)
            data.compiled_replacements.append((pattern, value))

            total += 1
        else:
            if line in seen:
                continue
            seen.add(line)
            data.hotwords.append(line)
            total += 1

    return data
