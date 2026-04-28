# Aside — CLAUDE.md

Open-source privacy-first voice dictation for macOS. Push-to-talk and toggle hotkeys capture audio, transcribe locally with faster-whisper, and type text at the cursor via Quartz keyboard events. No clipboard, no cloud, no telemetry.

**Repo:** https://github.com/blakeyoh/aside
**License:** Apache 2.0

## Stack

| Layer | What |
|---|---|
| Transcription | `faster-whisper` + `ctranslate2` (NOT openai-whisper/torch) |
| Audio capture | `sounddevice` → numpy float32 |
| Keyboard monitor | Quartz `CGEventTapCreate` (active tap, option=`0`) |
| Text injection | Quartz `CGEventCreateKeyboardEvent` |
| UI | `customtkinter` + `pyobjc` (AppKit, menu bar) |
| Header icon | `pillow` (CTkImage requires PIL) |
| Python | Homebrew Python 3.13 (system Python 3.9 is NOT supported) |
| Packaging | `pyproject.toml` + `setuptools.build_meta` |

## Setup & Launch

```bash
./setup.sh                          # one-time: creates .venv, installs deps, downloads base model, clears Gatekeeper quarantine
.venv/bin/python3 -m aside          # launch via Terminal
# OR: double-click Aside.app (can be moved to /Applications after setup.sh runs)
```

`setup.sh` auto-installs Python 3.13 via Homebrew if missing. It writes `~/.aside/install_path.txt` so `Aside.app` can find the venv from `/Applications` or anywhere.

Config: `~/.aside/config.json`. Dictionary: `~/.aside/dictionary.txt`. Auto-migrated from HushedHippo and WhisperDictation paths on first launch.

## Package Structure

```
src/aside/
├── __init__.py              # __version__ = "1.1.0"
├── __main__.py              # entry point
├── config.py                # load/save/migrate config, DEFAULT_CONFIG
├── engine/
│   ├── audio.py             # AudioCapture: sounddevice + chunk management
│   ├── hotkeys.py           # HotkeyManager: GIL-safe event tap + capture mode
│   ├── injector.py          # inject_text(), inject_keystroke() via Quartz
│   └── transcriber.py       # Transcriber: orchestrates stages 3-8 of pipeline
├── commands/
│   ├── parser.py            # parse_transcript(): ordered commands + rendered text
│   ├── actions.py           # execute_commands(): map Command enum to keystrokes
│   └── numbers.py           # NumberMode: word-to-digit with _join_tokens
├── dictionary/
│   ├── hotwords.py          # parse_dictionary(): 50-term cap, dedup, DictionaryData
│   ├── replacements.py      # apply_replacements(): regex with lookaround boundaries
│   └── context.py           # ContextBuffer: rolling 3-entry FIFO for initial_prompt
├── punctuation/
│   └── formatter.py         # format_text(): capitalization, smart quotes, trailing space
└── ui/
    ├── app.py               # App(ctk.CTk): main shell, wiring, state machines
    ├── menubar.py           # MenuBar: NSStatusBar + NSMenu + hotkey_display()
    ├── settings.py          # build_settings(): all settings panel widgets
    └── theme.py             # colors, fonts, MODELS, LANGUAGES, STATUS_MAP
```

## 8-Stage Transcription Pipeline

```
1. Hotkey Detection     → engine/hotkeys.py       [Quartz event tap]
2. Audio Capture        → engine/audio.py          [sounddevice]
3. Dictionary Pre-Proc  → dictionary/hotwords.py   [hotwords + initial_prompt]
     + context.py
4. Whisper Transcription → engine/transcriber.py   [faster-whisper]
5. Voice Command Detect → commands/parser.py       [ordered command rendering]
     + actions.py + numbers.py
6. Post-Processing      → dictionary/replacements  [regex replace]
     + punctuation/formatter.py
7. Text Injection       → engine/injector.py       [Quartz keystrokes]
8. Context Update       → dictionary/context.py    [FIFO append]
```

## Thread Model

```
Main thread (Tk):
  after_idle → engine startup (model load on background thread)
  after(10ms) → poll HotkeyManager (drain event queue)
  Settings UI, state machine, Apply handler

Background thread "event-tap":
  CFRunLoopRun() → CGEventTap callback → queue.put_nowait(raw ints)
  NEVER touches Python objects beyond the queue put
  Reads hotkey attrs without lock (GIL-atomic individual reads)

Background thread "model-load" / "transcribe":
  Load Whisper model, run transcription
  Access model under threading.Lock
  stream.stop() runs HERE (never main thread — blocks)
```

## Voice Commands (12 total)

| Trigger | Boundary | Action |
|---------|----------|--------|
| period / full stop | Word | Inject `.` |
| comma | Word | Inject `,` |
| question mark | Word | Inject `?` |
| exclamation point/mark | Word | Inject `!` |
| new line / newline | Word | Inject `\n` |
| new paragraph | Word | Inject `\n\n` |
| delete that | Sentence | Backspace last injection |
| undo | Sentence | Cmd+Z |
| select all | Sentence | Cmd+A |
| copy that / copy all | Sentence | Cmd+C |
| numbers mode | Sentence | Toggle digit conversion on |
| words mode | Sentence | Toggle digit conversion off |

**Boundary rules:** Dictation commands (punctuation, newlines) trigger at any word boundary and render inline in source order. Spoken punctuation commands are primary at their exact location, but Whisper punctuation elsewhere is preserved as secondary punctuation. Action commands (delete, undo, select, copy, mode toggles) require sentence boundary — prevents "I'll delete that section" from triggering.

## Custom Dictionary (3 layers)

1. **Hotwords** → `transcribe(hotwords=...)` biases Whisper decoder
2. **Context priming** → hotword terms + last 3 transcriptions fed as `initial_prompt`
3. **Replacements** → `wrong → right` lines become post-processing regex rules

File: `~/.aside/dictionary.txt`. 50-term cap (hotwords + replacements combined). Uses `(?<!\w)` / `(?!\w)` lookarounds (NOT `\b`) for correct boundary matching on patterns ending with non-word chars like "a.w.s."

## Testing

```bash
.venv/bin/python3 -m pytest tests/ -v    # 97 unit tests
```

Manual smoke test plan: `docs/smoke-test-plan.md` (Boeing FAI-style, 6 phases, go/no-go gates)

## Critical Gotchas

### Push-to-talk must stop on modifier release
Push-to-talk hotkeys cannot rely on `kCGEventKeyUp` alone. On macOS, releasing `Ctrl` or `Alt` before the trigger key often strips the modifier flag from the later key-up event. Preserve `kCGEventFlagsChanged` handling so recording stops when the modifier is released, otherwise push-to-talk can remain stuck recording until the shortcut is pressed again.

### Push-to-talk and toggle hotkeys must be distinct
Reject configurations where the push-to-talk hotkey and toggle hotkey are identical. The push-to-talk branch wins first in the event handler, which makes toggle recording unreachable and silently breaks hands-free mode.

### Quartz callback — keep it minimal
The CGEventTap callback runs on the background CFRunLoop thread. **Never acquire a Python `threading.Lock()` inside it.** GIL contention causes `kCGEventTapDisabledByTimeout` cycles. The callback must only: read event fields, `queue.put_nowait(raw ints)`, check plain attribute reads, return.

### `kCGEventTapOptionDefault` is not exported by pyobjc
Use the integer `0` directly.

### `sounddevice.InputStream.stop()` blocks the calling thread
**Never call it on the main thread.** The Transcriber runs stop/close on its background thread.

### `.app` launch path resolution
`setup.sh` writes `~/.aside/install_path.txt` so `Aside.app` can find the project venv even when moved to `/Applications`. The launcher validates that path and falls back to walking `../../..` from the bundle for in-repo launches. Keep both paths working.

### customtkinter init order
`ctk.set_appearance_mode()` and `ctk.set_default_color_theme()` MUST be called BEFORE `super().__init__()`. Silent failure otherwise.

### Widget API differences from tkinter
- `.config(fg=...)` → `.configure(text_color=...)`
- `.config(bg=...)` → `.configure(fg_color=...)`
- CTkFrame padx/pady go to `.pack()`, not the constructor
- CTkButton has no `relief`, `padx`, `pady` — use `corner_radius`, `width`, `height`

### `NSImage.lockFocus()` is unreliable in hybrid Tk/AppKit
Hand the raw PNG NSImage directly to `NSStatusBarButton.setImage_()` — the button scales template images automatically.

### Launch visibility
Terminal launch starts withdrawn and is controlled from the menu-bar icon. Finder/Dock `.app` launch sets `ASIDE_SHOW_SETTINGS_ON_LAUNCH=1`, so Settings opens once to prove the app started. `WM_DELETE_WINDOW` → `withdraw()` (not quit).

### Single-instance lock
Lock file at `~/.aside/aside.lock` using `fcntl.flock()`. Second launch shows alert and exits.

## Design Decisions Worth Preserving

These were discovered during implementation and aren't obvious from the code alone:

- **Task 4 (replacements):** `\b` word boundaries fail for patterns ending with non-word chars like "a.w.s." — switched to `(?<!\w)` / `(?!\w)` negative lookarounds
- **Task 6 (parser):** Commands split into dictation (trigger at word boundary) vs action (require sentence boundary) to prevent mid-sentence false triggers
- **Task 7 (numbers):** `_join_tokens` helper concatenates consecutive digit tokens without spaces ("one two three" → "123" not "1 2 3")
- **Task 9 (formatter tests):** Trailing space tests must use `capitalization="off"` for proper isolation
- **Task 2 (config tests):** Base fixture patches `_MIGRATION_PATHS = []` because real HushedHippo config exists on dev machine
- **v1.0.1 parser:** Use `parse_transcript()` in the pipeline, not legacy `parse_commands()`, so punctuation/newline commands render inline instead of moving ahead of dictated text.
- **v1.0.1 punctuation policy:** Commands win only at their location. Do not strip Whisper punctuation globally; remove only nearby duplicate punctuation artifacts around spoken command words.

## Deferred Work

See `docs/packaging-plan.md` and `docs/packaging-status.md` for the active packaging effort and per-issue handoff context.
