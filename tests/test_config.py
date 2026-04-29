import json
import pytest
from aside.config import load_config, save_config, DEFAULT_CONFIG, CONFIG_DIR


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
