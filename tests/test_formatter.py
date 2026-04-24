import pytest
from aside.punctuation.formatter import format_text


class TestCapitalization:
    def test_sentence_case_after_period(self):
        result = format_text("hello. world", capitalization="sentence")
        assert result == "Hello. World"

    def test_sentence_case_after_question(self):
        result = format_text("what? really", capitalization="sentence")
        assert result == "What? Really"

    def test_sentence_case_start_of_text(self):
        result = format_text("hello world", capitalization="sentence")
        assert result == "Hello world"

    def test_sentence_case_after_newline(self):
        result = format_text("first line\nsecond line", capitalization="sentence")
        assert result == "First line\nSecond line"

    def test_as_spoken_preserves_original(self):
        result = format_text("hELLo WoRLd", capitalization="as-spoken")
        assert result == "hELLo WoRLd"

    def test_off_lowercases(self):
        result = format_text("Hello World", capitalization="off")
        assert result == "hello world"


class TestSmartQuotes:
    def test_smart_quotes_off(self):
        result = format_text('she said "hello"', smart_quotes=False)
        assert '"' in result

    def test_smart_quotes_on(self):
        result = format_text('she said "hello"', smart_quotes=True)
        assert "\u201c" in result  # left double quote
        assert "\u201d" in result  # right double quote

    def test_single_smart_quotes(self):
        result = format_text("it's fine", smart_quotes=True)
        assert "\u2019" in result  # right single quote (apostrophe)


class TestTrailingSpace:
    def test_trailing_space_on(self):
        result = format_text("hello.world", trailing_space=True, capitalization="off")
        assert result == "hello. world"

    def test_trailing_space_off(self):
        result = format_text("hello.world", trailing_space=False, capitalization="off")
        assert result == "hello.world"

    def test_no_double_space(self):
        result = format_text("hello. world", trailing_space=True)
        assert "  " not in result


class TestCombined:
    def test_all_defaults(self):
        result = format_text("hello. world")
        # Default: sentence case, no smart quotes, trailing space
        assert result == "Hello. World"

    def test_empty_text(self):
        assert format_text("") == ""

    def test_whitespace_only(self):
        assert format_text("   ") == "   "
