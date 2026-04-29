import pytest
from aside.dictionary.context import ContextBuffer


class TestContextBuffer:
    def test_empty_buffer(self):
        buf = ContextBuffer()
        assert buf.build_initial_prompt([]) == ""

    def test_glossary_only(self):
        buf = ContextBuffer()
        prompt = buf.build_initial_prompt(["HIPAA", "PHI"])
        assert prompt == "Terms: HIPAA, PHI."

    def test_context_only(self):
        buf = ContextBuffer()
        buf.append("First transcription")
        prompt = buf.build_initial_prompt([])
        assert "First transcription" in prompt

    def test_glossary_plus_context(self):
        buf = ContextBuffer()
        buf.append("Reviewing the HIPAA policy")
        prompt = buf.build_initial_prompt(["HIPAA", "PHI"])
        assert prompt.startswith("Terms: HIPAA, PHI.")
        assert "Reviewing the HIPAA policy" in prompt

    def test_fifo_max_3(self):
        buf = ContextBuffer(max_entries=3)
        buf.append("one")
        buf.append("two")
        buf.append("three")
        buf.append("four")
        prompt = buf.build_initial_prompt([])
        assert "one" not in prompt
        assert "four" in prompt

    def test_token_truncation(self):
        buf = ContextBuffer(max_tokens=20)
        buf.append("a " * 100)  # way over limit
        prompt = buf.build_initial_prompt([])
        words = prompt.split()
        assert len(words) <= 25  # some tolerance
