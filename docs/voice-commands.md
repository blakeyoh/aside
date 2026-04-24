# Voice Commands

Aside recognizes 12 built-in voice commands. Speak them naturally as part of your dictation — Aside detects them, strips them from the transcript, and applies the corresponding action.

## Command Reference

| Command | Aliases | What It Does | Example |
|---------|---------|-------------|---------|
| new line | newline | Insert newline (`\n`) | "send email new line thanks" |
| new paragraph | — | Insert double newline (`\n\n`) | "first point new paragraph second point" |
| period | full stop | Insert `.` | "end of sentence period" |
| comma | — | Insert `,` | "hello comma world" |
| question mark | — | Insert `?` | "are you sure question mark" |
| exclamation point | exclamation mark | Insert `!` | "wow exclamation point" |
| delete that | — | Remove the last transcription chunk | "delete that" |
| undo | — | Send Cmd+Z | "undo" |
| select all | — | Send Cmd+A | "select all" |
| copy that | copy all | Send Cmd+C | "copy that" |
| numbers mode | — | Switch to digit input mode | "numbers mode" → "one two three" → 123 |
| words mode | — | Switch back to words mode | "words mode" |

## Numbers Mode

When you say "numbers mode", Aside enters a digit-input mode where spoken numbers are converted to digits rather than words:

- "one two three" → `123`
- "forty-five" → `45`
- "one thousand" → `1000`

Say "words mode" to return to normal transcription.

## Boundary Detection

Aside uses boundary detection to distinguish commands from similar-sounding words in context. A command is only recognized when it appears as a complete utterance segment — not when it's part of a compound word or a proper noun.

For example:
- "new line" at a natural pause → detected as command
- "online" or "pipeline" → not detected as command (no word boundary)

The parser tokenizes the transcript and matches command phrases against a known-command list before passing the remaining tokens to the text injector.

## Punctuation Commands vs. Auto-Punctuation

Aside's Whisper model infers punctuation automatically from speech patterns. When you speak an explicit punctuation command, the command is authoritative for that spot: Aside removes nearby duplicate inferred punctuation and renders the spoken command in that exact position. Whisper punctuation elsewhere in the transcript is preserved as secondary punctuation.
