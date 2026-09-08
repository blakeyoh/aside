from aside.commands.parser import parse_transcript, Command


class TestParseCommands:
    def test_no_commands(self):
        parsed = parse_transcript("hello world")
        assert parsed.commands == []
        assert parsed.cleaned_text == "hello world"

    def test_new_line_at_end(self):
        parsed = parse_transcript("hello new line")
        assert len(parsed.commands) == 1
        assert parsed.commands[0] == Command.NEW_LINE
        assert parsed.cleaned_text == "hello"

    def test_new_paragraph(self):
        parsed = parse_transcript("first paragraph new paragraph")
        assert Command.NEW_PARAGRAPH in parsed.commands
        assert parsed.cleaned_text == "first paragraph"

    def test_period_at_end(self):
        parsed = parse_transcript("end of sentence period")
        assert Command.PERIOD in parsed.commands
        assert parsed.cleaned_text == "end of sentence"

    def test_comma_at_end(self):
        parsed = parse_transcript("first comma")
        assert Command.COMMA in parsed.commands
        assert parsed.cleaned_text == "first"

    def test_question_mark(self):
        parsed = parse_transcript("is this right question mark")
        assert Command.QUESTION_MARK in parsed.commands
        assert parsed.cleaned_text == "is this right"

    def test_exclamation_point(self):
        parsed = parse_transcript("wow exclamation point")
        assert Command.EXCLAMATION in parsed.commands

    def test_delete_that(self):
        parsed = parse_transcript("delete that")
        assert Command.DELETE_THAT in parsed.commands
        assert parsed.cleaned_text == ""

    def test_undo(self):
        parsed = parse_transcript("undo")
        assert Command.UNDO in parsed.commands
        assert parsed.cleaned_text == ""

    def test_select_all(self):
        parsed = parse_transcript("select all")
        assert Command.SELECT_ALL in parsed.commands
        assert parsed.cleaned_text == ""

    def test_copy_that(self):
        parsed = parse_transcript("copy that")
        assert Command.COPY in parsed.commands

    def test_copy_all_alias(self):
        parsed = parse_transcript("copy all")
        assert Command.COPY in parsed.commands

    def test_full_stop_alias(self):
        parsed = parse_transcript("hello full stop")
        assert Command.PERIOD in parsed.commands
        assert parsed.cleaned_text == "hello"

    def test_exclamation_mark_alias(self):
        parsed = parse_transcript("wow exclamation mark")
        assert Command.EXCLAMATION in parsed.commands

    def test_newline_no_space(self):
        parsed = parse_transcript("hello newline")
        assert Command.NEW_LINE in parsed.commands

    def test_embedded_command_not_triggered(self):
        """'delete that' mid-sentence should NOT trigger."""
        parsed = parse_transcript("I will delete that section later")
        assert parsed.commands == []
        assert parsed.cleaned_text == "I will delete that section later"

    def test_command_after_punctuation(self):
        parsed = parse_transcript("end. delete that")
        assert Command.DELETE_THAT in parsed.commands
        assert parsed.cleaned_text == "end."

    def test_multiple_commands(self):
        parsed = parse_transcript("thanks comma I'll review it period new line")
        assert Command.COMMA in parsed.commands
        assert Command.PERIOD in parsed.commands
        assert Command.NEW_LINE in parsed.commands

    def test_case_insensitive(self):
        parsed = parse_transcript("Hello New Line")
        assert Command.NEW_LINE in parsed.commands
        assert parsed.cleaned_text == "Hello"

    def test_numbers_mode_toggle(self):
        parsed = parse_transcript("numbers mode")
        assert Command.NUMBERS_MODE in parsed.commands
        assert parsed.cleaned_text == ""

    def test_words_mode_toggle(self):
        parsed = parse_transcript("words mode")
        assert Command.WORDS_MODE in parsed.commands


class TestParseTranscript:
    def test_period_command_renders_inline(self):
        parsed = parse_transcript("I had a good day today period")
        assert parsed.rendered_text == "I had a good day today."
        assert parsed.cleaned_text == "I had a good day today"

    def test_period_command_wins_over_inferred_period_after(self):
        parsed = parse_transcript("I had a good day today period.")
        assert parsed.rendered_text == "I had a good day today."

    def test_period_command_wins_over_inferred_period_before(self):
        parsed = parse_transcript("I had a good day today. period")
        assert parsed.rendered_text == "I had a good day today."

    def test_comma_and_period_render_in_order(self):
        parsed = parse_transcript("Hello comma world period")
        assert parsed.rendered_text == "Hello, world."

    def test_inferred_punctuation_preserved_without_commands(self):
        parsed = parse_transcript("Hello, world. Are you there?")
        assert parsed.rendered_text == "Hello, world. Are you there?"

    def test_inferred_punctuation_preserved_around_commands(self):
        parsed = parse_transcript("Hello, I am here period are you there?")
        assert parsed.rendered_text == "Hello, I am here. are you there?"

    def test_new_line_renders_between_text_chunks(self):
        parsed = parse_transcript("First line new line second line")
        assert parsed.rendered_text == "First line\nsecond line"

    def test_new_line_preserves_inferred_sentence_punctuation_before_break(self):
        parsed = parse_transcript("First sentence. new line second sentence.")
        assert parsed.rendered_text == "First sentence.\nsecond sentence."

    def test_new_paragraph_renders_between_text_chunks(self):
        parsed = parse_transcript("First paragraph new paragraph second paragraph")
        assert parsed.rendered_text == "First paragraph\n\nsecond paragraph"

    def test_commands_are_not_moved_to_front(self):
        parsed = parse_transcript("Thanks comma I'll review it period new line")
        assert parsed.rendered_text == "Thanks, I'll review it.\n"

    def test_user_sample_artifacts_do_not_duplicate(self):
        parsed = parse_transcript(
            "You do not know until you press the hot key comma. "
            "so I would love to work on that period."
        )
        assert parsed.rendered_text == (
            "You do not know until you press the hot key, so I would love to work on that."
        )
