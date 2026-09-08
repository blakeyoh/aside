from aside.dictionary.replacements import apply_replacements, _get_compiled_pattern


class TestApplyReplacements:
    def test_no_rules_returns_text_unchanged(self):
        assert apply_replacements("hello world", {}) == "hello world"

    def test_simple_replacement(self):
        rules = {"hip a": "HIPAA"}
        assert (
            apply_replacements("the hip a regulation", rules) == "the HIPAA regulation"
        )

    def test_case_insensitive(self):
        rules = {"hip a": "HIPAA"}
        assert apply_replacements("The HIP A law", rules) == "The HIPAA law"

    def test_word_boundary_prevents_partial_match(self):
        rules = {"a": "THE"}
        result = apply_replacements("a cat sat on a mat", rules)
        assert result == "THE cat sat on THE mat"

    def test_multiple_rules(self):
        rules = {"hip a": "HIPAA", "a.w.s.": "AWS"}
        text = "hip a on a.w.s."
        result = apply_replacements(text, rules)
        assert "HIPAA" in result
        assert "AWS" in result

    def test_replacement_with_arrow_in_value(self):
        rules = {"go to": "navigate → proceed"}
        assert (
            apply_replacements("go to the store", rules)
            == "navigate → proceed the store"
        )

    def test_empty_text(self):
        assert apply_replacements("", {"a": "b"}) == ""

    def test_unicode_replacement(self):
        rules = {"resume": "résumé"}
        assert apply_replacements("send your resume", rules) == "send your résumé"

    def test_pattern_ending_in_nonword_char_matches(self):
        # \b would fail after the trailing "."; lookarounds (?<!\w)/(?!\w) handle it
        rules = {"a.w.s.": "AWS"}
        assert apply_replacements("deploy a.w.s. today", rules) == "deploy AWS today"

    def test_accepts_precompiled_pattern_list(self):
        rules = [(_get_compiled_pattern("hip a"), "HIPAA")]
        assert apply_replacements("the hip a rule", rules) == "the HIPAA rule"
