import pytest
from aside.commands.parser import parse_commands, Command


class TestParseCommands:
    def test_no_commands(self):
        cmds, text = parse_commands("hello world")
        assert cmds == []
        assert text == "hello world"

    def test_new_line_at_end(self):
        cmds, text = parse_commands("hello new line")
        assert len(cmds) == 1
        assert cmds[0] == Command.NEW_LINE
        assert text == "hello"

    def test_new_paragraph(self):
        cmds, text = parse_commands("first paragraph new paragraph")
        assert Command.NEW_PARAGRAPH in cmds
        assert text == "first paragraph"

    def test_period_at_end(self):
        cmds, text = parse_commands("end of sentence period")
        assert Command.PERIOD in cmds
        assert text == "end of sentence"

    def test_comma_at_end(self):
        cmds, text = parse_commands("first comma")
        assert Command.COMMA in cmds
        assert text == "first"

    def test_question_mark(self):
        cmds, text = parse_commands("is this right question mark")
        assert Command.QUESTION_MARK in cmds
        assert text == "is this right"

    def test_exclamation_point(self):
        cmds, text = parse_commands("wow exclamation point")
        assert Command.EXCLAMATION in cmds

    def test_delete_that(self):
        cmds, text = parse_commands("delete that")
        assert Command.DELETE_THAT in cmds
        assert text == ""

    def test_undo(self):
        cmds, text = parse_commands("undo")
        assert Command.UNDO in cmds
        assert text == ""

    def test_select_all(self):
        cmds, text = parse_commands("select all")
        assert Command.SELECT_ALL in cmds
        assert text == ""

    def test_copy_that(self):
        cmds, text = parse_commands("copy that")
        assert Command.COPY in cmds

    def test_copy_all_alias(self):
        cmds, text = parse_commands("copy all")
        assert Command.COPY in cmds

    def test_full_stop_alias(self):
        cmds, text = parse_commands("hello full stop")
        assert Command.PERIOD in cmds
        assert text == "hello"

    def test_exclamation_mark_alias(self):
        cmds, text = parse_commands("wow exclamation mark")
        assert Command.EXCLAMATION in cmds

    def test_newline_no_space(self):
        cmds, text = parse_commands("hello newline")
        assert Command.NEW_LINE in cmds

    def test_embedded_command_not_triggered(self):
        """'delete that' mid-sentence should NOT trigger."""
        cmds, text = parse_commands("I will delete that section later")
        assert cmds == []
        assert text == "I will delete that section later"

    def test_command_after_punctuation(self):
        cmds, text = parse_commands("end. delete that")
        assert Command.DELETE_THAT in cmds
        assert text == "end."

    def test_multiple_commands(self):
        cmds, text = parse_commands("thanks comma I'll review it period new line")
        assert Command.COMMA in cmds
        assert Command.PERIOD in cmds
        assert Command.NEW_LINE in cmds

    def test_case_insensitive(self):
        cmds, text = parse_commands("Hello New Line")
        assert Command.NEW_LINE in cmds
        assert text == "Hello"

    def test_numbers_mode_toggle(self):
        cmds, text = parse_commands("numbers mode")
        assert Command.NUMBERS_MODE in cmds
        assert text == ""

    def test_words_mode_toggle(self):
        cmds, text = parse_commands("words mode")
        assert Command.WORDS_MODE in cmds
