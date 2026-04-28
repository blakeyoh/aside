"""Configuration management for Aside.

Config file: ~/.aside/config.json
Migration: WhisperDictation → HushedHippo → Aside (checks in order)
"""
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".aside"
CONFIG_FILE = CONFIG_DIR / "config.json"
DICTIONARY_FILE = CONFIG_DIR / "dictionary.txt"

DEFAULT_HOTKEY = {"modifiers": ["ctrl", "alt"], "trigger": "space"}

DEFAULT_CONFIG: dict[str, Any] = {
    "model_size": "base",
    "language": None,
    "hotkey": DEFAULT_HOTKEY.copy(),
    "toggle_hotkey": None,
    "punctuation": {
        "capitalization": "sentence",
        "smart_quotes": False,
        "trailing_space": True,
    },
    "hotwords": [],
    "replacements": {
        "alright": "all right",
        "Alright": "All right",
        "nevermind": "never mind",
    },
}

DICTIONARY_TEMPLATE = """\
# Aside Custom Dictionary
# Max 50 terms
#
# HOTWORDS — terms Whisper should recognize
# One per line:
# HIPAA
# Kubernetes
#
# REPLACEMENTS — fix consistent misrecognitions
# Format: wrong → right
# hip a → HIPAA
"""

# Old config paths to check for migration (newest first)
_MIGRATION_PATHS = [
    Path.home() / "Library" / "Application Support" / "HushedHippo" / "config.json",
    Path.home() / "Library" / "Application Support" / "WhisperDictation" / "config.json",
]


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base, recursing into nested dicts."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _try_migrate() -> dict | None:
    """Check old config paths and migrate the first one found."""
    for old_path in _MIGRATION_PATHS:
        if old_path.exists():
            try:
                data = json.loads(old_path.read_text(encoding="utf-8"))
                logger.info("Migrating config from %s", old_path)
                return data
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Migration failed for %s: %s", old_path, exc)
    return None


def load_config() -> dict:
    """Load config from ~/.aside/config.json, migrating if needed.

    Returns a complete config dict with defaults for any missing fields.
    """
    saved = {}

    if CONFIG_FILE.exists():
        try:
            saved = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Config load failed, using defaults: %s", exc)

    if not saved:
        migrated = _try_migrate()
        if migrated:
            saved = migrated
            # Persist the migrated config
            save_config(_deep_merge(DEFAULT_CONFIG, saved))

    return _deep_merge(DEFAULT_CONFIG, saved)


def save_config(cfg: dict) -> bool:
    """Save config to ~/.aside/config.json. Creates directory if needed."""
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except OSError as exc:
        logger.error("Config save failed: %s", exc)
        return False


def ensure_dictionary_file() -> None:
    """Create ~/.aside/dictionary.txt with template if it doesn't exist."""
    if not DICTIONARY_FILE.exists():
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            DICTIONARY_FILE.write_text(DICTIONARY_TEMPLATE, encoding="utf-8")
        except OSError as exc:
            logger.warning("Could not create dictionary template: %s", exc)
