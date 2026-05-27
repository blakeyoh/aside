from aside.commands.numbers import NumberMode


class TestNumberMode:
    def test_default_off(self):
        nm = NumberMode()
        assert nm.active is False

    def test_toggle_on_off(self):
        nm = NumberMode()
        nm.activate()
        assert nm.active is True
        nm.deactivate()
        assert nm.active is False

    def test_no_conversion_when_off(self):
        nm = NumberMode()
        assert nm.process("one two three") == "one two three"

    def test_basic_conversion(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("one two three") == "123"

    def test_mixed_text_and_numbers(self):
        nm = NumberMode()
        nm.activate()
        assert (
            nm.process("call me at five five five one two three four")
            == "call me at 5551234"
        )

    def test_teen_numbers(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("thirteen") == "13"
        assert nm.process("twenty") == "20"

    def test_compound_numbers(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("twenty one") == "21"
        assert nm.process("forty five") == "45"

    def test_hundred(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("one hundred") == "100"
        assert nm.process("three hundred twenty one") == "321"

    def test_zero(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("zero") == "0"

    def test_non_number_words_pass_through(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("hello world") == "hello world"

    def test_reset(self):
        nm = NumberMode()
        nm.activate()
        nm.reset()
        assert nm.active is False

    def test_number_run_between_words_keeps_spacing(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("call one two now") == "call 12 now"

    def test_text_between_number_runs_is_spaced(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("one apple two") == "1 apple 2"

    def test_bare_hundred_passes_through(self):
        nm = NumberMode()
        nm.activate()
        assert nm.process("hundred dollars") == "hundred dollars"
