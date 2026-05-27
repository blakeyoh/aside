import pytest
from aside.dictionary.hotwords import parse_dictionary, DictionaryData


class TestParseDictionary:
    def test_empty_file(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("")
        result = parse_dictionary(f)
        assert result.hotwords == []
        assert result.replacements == {}

    def test_comments_and_blanks_ignored(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("# comment\n\n  \n# another\n")
        result = parse_dictionary(f)
        assert result.hotwords == []

    def test_hotwords_parsed(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("HIPAA\nKubernetes\nkubectl\n")
        result = parse_dictionary(f)
        assert result.hotwords == ["HIPAA", "Kubernetes", "kubectl"]

    def test_replacements_parsed(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("hip a → HIPAA\ncube control → kubectl\n")
        result = parse_dictionary(f)
        assert result.replacements == {
            "hip a": "HIPAA",
            "cube control": "kubectl",
        }

    def test_mixed_hotwords_and_replacements(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("# Hotwords\nHIPAA\nPHI\n\n# Replacements\nhip a → HIPAA\n")
        result = parse_dictionary(f)
        assert result.hotwords == ["HIPAA", "PHI"]
        assert result.replacements == {"hip a": "HIPAA"}
        assert result.term_count == 3

    def test_50_term_cap(self, tmp_path):
        f = tmp_path / "dict.txt"
        lines = [f"term{i}" for i in range(60)]
        f.write_text("\n".join(lines))
        result = parse_dictionary(f)
        assert result.term_count == 50
        assert len(result.hotwords) == 50
        assert result.over_limit is True

    def test_first_arrow_is_delimiter(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("a → b → c\n")
        result = parse_dictionary(f)
        assert result.replacements == {"a": "b → c"}

    def test_missing_file_returns_empty(self, tmp_path):
        f = tmp_path / "nonexistent.txt"
        result = parse_dictionary(f)
        assert result.hotwords == []
        assert result.replacements == {}

    def test_unicode_terms(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("café\nnaïve\nresumé → résumé\n", encoding="utf-8")
        result = parse_dictionary(f)
        assert "café" in result.hotwords
        assert result.replacements == {"resumé": "résumé"}

    def test_duplicate_detection(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("HIPAA\nHIPAA\n")
        result = parse_dictionary(f)
        assert result.hotwords == ["HIPAA"]
        assert result.term_count == 1

    def test_whisper_hotwords_string(self, tmp_path):
        f = tmp_path / "dict.txt"
        f.write_text("HIPAA\nKubernetes\n")
        result = parse_dictionary(f)
        assert result.whisper_hotwords == "HIPAA Kubernetes"

    def test_compiled_replacements_drive_substitution(self, tmp_path):
        from aside.dictionary.replacements import apply_replacements

        f = tmp_path / "dict.txt"
        f.write_text("hip a → HIPAA\n")
        result = parse_dictionary(f)

        assert result.compiled_replacements  # pre-compiled, ready for reuse
        assert (
            apply_replacements("the hip a rule", result.compiled_replacements)
            == "the HIPAA rule"
        )
