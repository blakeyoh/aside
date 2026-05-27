from unittest.mock import Mock
from aside.commands.actions import execute_commands
from aside.commands.parser import Command

def test_execute_punctuation():
    inject_text = Mock()
    inject_keystroke = Mock()

    commands = [
        Command.PERIOD,
        Command.COMMA,
        Command.QUESTION_MARK,
        Command.EXCLAMATION,
        Command.NEW_LINE,
        Command.NEW_PARAGRAPH
    ]
    execute_commands(commands, inject_text, inject_keystroke)

    assert inject_text.call_count == 6
    inject_text.assert_any_call(".")
    inject_text.assert_any_call(",")
    inject_text.assert_any_call("?")
    inject_text.assert_any_call("!")
    inject_text.assert_any_call("\n")
    inject_text.assert_any_call("\n\n")
    assert inject_keystroke.call_count == 0

def test_execute_delete_that():
    inject_text = Mock()
    inject_keystroke = Mock()

    execute_commands([Command.DELETE_THAT], inject_text, inject_keystroke, last_injection_length=5)

    assert inject_keystroke.call_count == 5
    inject_keystroke.assert_called_with("backspace", [])
    assert inject_text.call_count == 0

def test_execute_action_commands():
    inject_text = Mock()
    inject_keystroke = Mock()

    commands = [Command.UNDO, Command.SELECT_ALL, Command.COPY]
    execute_commands(commands, inject_text, inject_keystroke)

    assert inject_keystroke.call_count == 3
    inject_keystroke.assert_any_call("z", ["cmd"])
    inject_keystroke.assert_any_call("a", ["cmd"])
    inject_keystroke.assert_any_call("c", ["cmd"])
    assert inject_text.call_count == 0

def test_execute_multiple_commands():
    inject_text = Mock()
    inject_keystroke = Mock()

    commands = [Command.PERIOD, Command.UNDO]
    execute_commands(commands, inject_text, inject_keystroke)

    inject_text.assert_called_once_with(".")
    inject_keystroke.assert_called_once_with("z", ["cmd"])

def test_execute_ignored_commands():
    inject_text = Mock()
    inject_keystroke = Mock()

    commands = [Command.NUMBERS_MODE, Command.WORDS_MODE]
    execute_commands(commands, inject_text, inject_keystroke)

    assert inject_text.call_count == 0
    assert inject_keystroke.call_count == 0
