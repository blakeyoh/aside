import json
import pytest
from aside.config import (
    load_config,
    save_config,
    ensure_dictionary_file,
    _deep_merge,
    DEFAULT_CONFIG,
    DICTIONARY_TEMPLATE,
    CONFIG_DIR,
)


@pytest.fixture
def tmp_aside_dir(tmp_path, monkeypatch):
    """Redirect ~/.aside to a temp dir and clear migration paths for isolation."""
    aside_dir = tmp_path / ".aside"
    monkeypatch.setattr("aside.config.CONFIG_DIR", aside_dir)
    monkeypatch.setattr("aside.config.CONFIG_FILE", aside_dir / "config.json")
    # Block migration from finding real system configs
    monkeypatch.setattr("aside.config._MIGRATION_PATHS", [])
    return aside_dir


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_aside_dir):
        cfg = load_config()
        assert cfg["model_size"] == "base"
        assert cfg["language"] is None
        assert cfg["first_run_complete"] is False
        assert cfg["hotkey"] == {"modifiers": ["ctrl", "alt"], "trigger": "space"}
        assert cfg["toggle_hotkey"] is None
        assert cfg["punctuation"]["capitalization"] == "sentence"
        assert cfg["punctuation"]["smart_quotes"] is False
        assert cfg["punctuation"]["trailing_space"] is True
        assert cfg["hotwords"] == []
        assert cfg["replacements"] == {
            "alright": "all right",
            "Alright": "All right",
            "nevermind": "never mind",
        }

    def test_loads_existing_config(self, tmp_aside_dir):
        tmp_aside_dir.mkdir(parents=True)
        (tmp_aside_dir / "config.json").write_text(json.dumps({
            "model_size": "small",
            "language": "es",
        }))
        cfg = load_config()
        assert cfg["model_size"] == "small"
        assert cfg["language"] == "es"
        # Defaults for missing fields
        assert cfg["punctuation"]["capitalization"] == "sentence"

    def test_corrupt_json_returns_defaults(self, tmp_aside_dir):
        tmp_aside_dir.mkdir(parents=True)
        (tmp_aside_dir / "config.json").write_text("NOT JSON{{{")
        cfg = load_config()
        assert cfg["model_size"] == "base"


class TestSaveConfig:
    def test_creates_dir_and_saves(self, tmp_aside_dir):
        assert not tmp_aside_dir.exists()
        save_config({"model_size": "large-v3", "language": "ja"})
        assert tmp_aside_dir.exists()
        saved = json.loads((tmp_aside_dir / "config.json").read_text())
        assert saved["model_size"] == "large-v3"
        assert saved["language"] == "ja"

    def test_returns_false_on_write_error(self, tmp_aside_dir, monkeypatch):
        def boom(*args, **kwargs):
            raise OSError("disk full")

        monkeypatch.setattr("pathlib.Path.write_text", boom)
        assert save_config({"model_size": "base"}) is False


class TestDeepMerge:
    def test_recurses_into_nested_dicts_without_mutating_base(self):
        base = {"a": 1, "punctuation": {"x": 1, "y": 2}}
        override = {"punctuation": {"y": 9, "z": 3}, "b": 2}

        merged = _deep_merge(base, override)

        assert merged == {"a": 1, "punctuation": {"x": 1, "y": 9, "z": 3}, "b": 2}
        assert base == {"a": 1, "punctuation": {"x": 1, "y": 2}}

    def test_non_dict_override_replaces_value(self):
        assert _deep_merge({"k": {"nested": 1}}, {"k": "scalar"}) == {"k": "scalar"}


class TestEnsureDictionaryFile:
    def test_creates_template_when_missing(self, tmp_aside_dir, monkeypatch):
        dict_file = tmp_aside_dir / "dictionary.txt"
        monkeypatch.setattr("aside.config.DICTIONARY_FILE", dict_file)

        ensure_dictionary_file()

        assert dict_file.read_text() == DICTIONARY_TEMPLATE

    def test_does_not_overwrite_existing(self, tmp_aside_dir, monkeypatch):
        tmp_aside_dir.mkdir(parents=True)
        dict_file = tmp_aside_dir / "dictionary.txt"
        dict_file.write_text("my custom terms")
        monkeypatch.setattr("aside.config.DICTIONARY_FILE", dict_file)

        ensure_dictionary_file()

        assert dict_file.read_text() == "my custom terms"


class TestMigration:
    def test_migrates_from_hushed_hippo(self, tmp_aside_dir, tmp_path, monkeypatch):
        old_dir = tmp_path / "Library" / "Application Support" / "HushedHippo"
        old_dir.mkdir(parents=True)
        (old_dir / "config.json").write_text(json.dumps({
            "model_size": "medium",
            "hotkey": {"modifiers": ["cmd"], "trigger": "a"},
        }))
        monkeypatch.setattr("aside.config._MIGRATION_PATHS", [
            old_dir / "config.json",
        ])
        cfg = load_config()
        assert cfg["model_size"] == "medium"
        assert cfg["hotkey"] == {"modifiers": ["cmd"], "trigger": "a"}
        # New fields get defaults
        assert cfg["language"] is None
        assert cfg["punctuation"]["capitalization"] == "sentence"
        # File was migrated
        assert (tmp_aside_dir / "config.json").exists()

    def test_migrates_from_whisper_dictation(self, tmp_aside_dir, tmp_path, monkeypatch):
        old_dir = tmp_path / "Library" / "Application Support" / "WhisperDictation"
        old_dir.mkdir(parents=True)
        (old_dir / "config.json").write_text(json.dumps({"model_size": "small"}))
        monkeypatch.setattr("aside.config._MIGRATION_PATHS", [old_dir / "config.json"])

        assert load_config()["model_size"] == "small"

    def test_newest_path_wins_when_both_legacy_configs_exist(
        self, tmp_aside_dir, tmp_path, monkeypatch
    ):
        hushed = tmp_path / "HushedHippo" / "config.json"
        whisper = tmp_path / "WhisperDictation" / "config.json"
        hushed.parent.mkdir(parents=True)
        whisper.parent.mkdir(parents=True)
        hushed.write_text(json.dumps({"model_size": "medium"}))
        whisper.write_text(json.dumps({"model_size": "tiny"}))
        # Ordered newest-first: HushedHippo before WhisperDictation
        monkeypatch.setattr("aside.config._MIGRATION_PATHS", [hushed, whisper])

        assert load_config()["model_size"] == "medium"
