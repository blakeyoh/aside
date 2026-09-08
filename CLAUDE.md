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
| Release UI | SwiftUI shell in `native/AsideShell` |
| Engine bridge | Newline-delimited JSON over stdio via `aside.helper` |
| Legacy UI | `customtkinter` + `pyobjc`, retained for source compatibility |
| Python | Homebrew Python 3.13 (system Python 3.9 is NOT supported) |
| Packaging | Native Swift executable with an embedded py2app helper and base model |

## Setup & Launch

```bash
./setup.sh                          # one-time: creates .venv, installs deps, downloads base model
source .venv/bin/activate
scripts/run_swiftui_spike.sh         # launch the native shell from source
scripts/smoke_swiftui_launch.sh      # bounded shell/helper protocol smoke
.venv/bin/python3 -m aside           # legacy source UI compatibility path
```

`setup.sh` auto-installs Homebrew Python 3.13 if missing and installs the matching `python-tk@3.13` formula. The release artifact is `dist-swiftui/Aside.app`, built by `scripts/build_swiftui_app.sh release` and packaged by `scripts/package_swiftui_dmg.sh`. The standalone `dist/Aside.app` py2app bundle is legacy compatibility evidence only.

Config: `~/.aside/config.json`. Dictionary: `~/.aside/dictionary.txt`. Auto-migrated from HushedHippo and WhisperDictation paths on first launch.

## Package Structure

```
native/AsideShell/
├── Package.swift             # macOS 13+ Swift executable
└── Sources/AsideShell/
    ├── AsideShellApp.swift   # windows, menu bar, settings, onboarding, Practice
    └── HelperSupervisor.swift # helper process and framed stdio protocol

src/aside/
├── __init__.py              # __version__ = "1.3.0"
├── __main__.py              # entry point
├── helper.py                # engine owner for the SwiftUI shell
├── config.py                # load/save/migrate config, DEFAULT_CONFIG
├── permissions.py           # mic/accessibility/input-monitoring checks + Settings links
├── resources.py             # source vs py2app resource path lookup
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
    ├── onboarding.py        # first-run permissions window
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

## Process And Thread Model

```
Main app process:
  SwiftUI owns windows, menu bar, state presentation, and helper supervision
  HelperSupervisor launches the embedded/source Python helper over stdio

Python helper process:
  Main loop drains commands and hotkey events
  model-load / transcribe threads own Whisper and blocking audio teardown

Background thread "event-tap":
  CFRunLoopRun() → CGEventTap callback → queue.put_nowait(raw ints)
  NEVER touches Python objects beyond the queue put
  Reads hotkey attrs without lock (GIL-atomic individual reads)

Legacy source UI:
  customtkinter remains supported for regression/source compatibility only
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
.venv/bin/python3 -m pytest tests/ -v
swift build --package-path native/AsideShell
scripts/smoke_swiftui_launch.sh
```

`tests/conftest.py` stubs the macOS-only GUI/audio libraries when they're
absent, so the runnable subset works on Linux too (for cloud agents). Tests
needing the real native stack (e.g. the helper subprocess) skip off macOS and
are covered by the macOS CI workflow.

Protocol smoke uses fake audio/hotkeys/transcription and does not prove working dictation. Native release approval additionally requires the installed-artifact and manual gates in `docs/swiftui-release-audit-2026-09-08.md`.

## Critical Gotchas

### Release authority

`main` is the canonical integration base. The native SwiftUI DMG is the only publish path. Never infer native release readiness from the legacy py2app workflow, a protocol-smoke `ready` event, or historical technical-spike evidence. Read `docs/swiftui-release-audit-2026-09-08.md` before release work and stay within the assigned R-number.

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

### py2app resource lookup
Use `aside.resources.resource_path(...)` for files that must work in both source checkouts and bundled apps. Source mode resolves from the repo root. py2app mode resolves from `Aside.app/Contents/Resources`.

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
Startup must always show a visible surface. First run shows onboarding until all three permissions are granted. Later launches show Settings automatically. `WM_DELETE_WINDOW` → `withdraw()` (not quit).

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

Follow `docs/swiftui-release-audit-2026-09-08.md` and `TODO.md`. The older `docs/packaging-plan.md` and `docs/packaging-status.md` describe the legacy py2app effort and are historical only.
