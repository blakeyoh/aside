"""Execute voice commands via Quartz keystroke injection.

Each action is a thin wrapper that calls the injector module.
"""
from aside.commands.parser import Command


# Maps commands to the text/keystroke they inject
_PUNCTUATION_MAP = {
    Command.PERIOD: ".",
    Command.COMMA: ",",
    Command.QUESTION_MARK: "?",
    Command.EXCLAMATION: "!",
    Command.NEW_LINE: "\n",
    Command.NEW_PARAGRAPH: "\n\n",
}


def execute_commands(
    commands: list[Command],
    inject_text_fn,
    inject_keystroke_fn,
    last_injection_length: int = 0,
) -> None:
    """Execute a list of voice commands.

    Args:
        commands: List of Command enums to execute.
        inject_text_fn: Callable(str) to inject text at cursor.
        inject_keystroke_fn: Callable(key, modifiers) to inject keystrokes.
        last_injection_length: Character count of last text injection (for delete_that).
    """
    for cmd in commands:
        if cmd in _PUNCTUATION_MAP:
            inject_text_fn(_PUNCTUATION_MAP[cmd])

        elif cmd == Command.DELETE_THAT:
            # Emit backspaces to remove last transcription
            for _ in range(last_injection_length):
                inject_keystroke_fn("backspace", [])

        elif cmd == Command.UNDO:
            inject_keystroke_fn("z", ["cmd"])

        elif cmd == Command.SELECT_ALL:
            inject_keystroke_fn("a", ["cmd"])

        elif cmd == Command.COPY:
            inject_keystroke_fn("c", ["cmd"])

        # NUMBERS_MODE and WORDS_MODE are handled by the pipeline,
        # not as keystroke actions
