# Aside — Product Design Spec

**Date:** 2026-03-21
**Status:** Approved
**Author:** Kai + Claude

## Vision

Aside is an open-source, privacy-first voice dictation app for macOS — a local alternative to Wispr Flow for professionals who work with confidential information. Audio never leaves the machine. No cloud APIs, no telemetry, no data collection.

**Target user:** Privacy-conscious professionals and developers — the kind who use Signal, run local LLMs, and prefer self-hosted tools. Early adopters who'll audit the code, file issues, and spread the word.

**Product positioning:** 80% of Wispr Flow's capability with 100% privacy. The "restaurant name" approach — *Aside* evokes a theatrical whisper meant for one person only.

## Scope: v1

### Features (in scope)

- **Push-to-talk dictation** — hold hotkey, speak, release, text types at cursor (proven, extracted from Hushed Hippo)
- **Toggle/hands-free mode** — press once to start, press again to stop (proven)
- **Model selection** — tiny through large-v3 (proven)
- **Voice commands:**
  - "new line" / "new paragraph"
  - "period" / "comma" / "question mark" / "exclamation point"
  - "delete that"
  - "undo"
  - "select all"
  - "copy that"
  - Number dictation mode ("one two three" → "123")
- **Custom dictionary** (50-term cap):
  - Hotwords — bias Whisper's decoder toward domain terms
  - Context priming — rolling context from last 3 transcriptions fed as initial_prompt
  - Post-processing replacements — regex find/replace for terms Whisper consistently misrecognizes
  - In-app Add fields (hotword + replacement) for easy path
  - "Edit Dictionary" button opens `~/.aside/dictionary.txt` for power users
  - "Reload" button re-parses file without restart
- **Multi-language support** — language dropdown in settings, passed to `transcribe(language=...)`
- **Auto-punctuation tuning** — three settings: capitalization style (sentence case / as-spoken / off), smart quotes (on/off), trailing space after punctuation (on/off)
- **Privacy documentation** — PRIVACY.md, architecture data flow doc, README trust section
- **Open-source repo** — Apache 2.0, clean git history, contributor guide
- **Homebrew distribution** — `brew tap blakeyoh/aside && brew install aside`

### Features (deferred to roadmap)

- Interactive tutorial webpage ("training range" for voice commands)
- Transcription history/log
- System tray notifications
- SwiftUI native frontend (v2-v3)
- PyInstaller standalone .dmg
- Code signing / notarization
- Tier 2 voice commands (cap, all caps, tab, sleep/wake)
- Tier 3 voice commands (cursor movement, word selection, formatting)

## Architecture

### Approach: Extract & Restructure

Start a fresh repo (`github.com/blakeyoh/aside`), extract the proven engine core from Hushed Hippo, restructure into a proper Python package layout. Same engine code, better architecture, clean git history.

### Package Layout

```
aside/                           # repo root
├── LICENSE                      # Apache 2.0
├── README.md                    # GTM-crafted intro + install
├── PRIVACY.md                   # data flow documentation
├── CONTRIBUTING.md              # contributor guide
├── pyproject.toml               # modern Python packaging
├── Formula/aside.rb             # Homebrew formula
├── setup.sh                     # one-command install wizard
│
├── src/aside/                   # main package
│   ├── __init__.py
│   ├── __main__.py              # entry point (python -m aside)
│   │
│   ├── engine/                  # core transcription pipeline
│   │   ├── transcriber.py       # Whisper model management + transcription
│   │   ├── audio.py             # sounddevice capture + chunking
│   │   ├── hotkeys.py           # Quartz event tap + GIL-safe callback
│   │   └── injector.py          # Quartz keyboard event text injection
│   │
│   ├── commands/                # voice command processing
│   │   ├── parser.py            # detect commands in transcribed text
│   │   ├── actions.py           # execute commands (new line, delete, etc.)
│   │   └── numbers.py           # number dictation mode
│   │
│   ├── dictionary/              # custom vocabulary system
│   │   ├── hotwords.py          # load user dictionary → Whisper hotwords
│   │   ├── replacements.py      # post-processing find/replace
│   │   └── context.py           # rolling context (last N transcriptions)
│   │
│   ├── punctuation/             # auto-punctuation tuning
│   │   └── formatter.py         # capitalization, punctuation style, cleanup
│   │
│   ├── ui/                      # all presentation
│   │   ├── app.py               # customtkinter window + layout
│   │   ├── menubar.py           # AppKit menu bar + status icon
│   │   ├── settings.py          # settings panel (model, hotkey, dictionary, language)
│   │   └── theme.py             # colors, fonts, dark mode constants
│   │
│   └── config.py                # load/save/migrate JSON config
│
├── tests/
│   ├── test_transcriber.py
│   ├── test_commands.py
│   ├── test_numbers.py
│   ├── test_dictionary.py
│   ├── test_replacements.py
│   ├── test_formatter.py
│   └── test_config.py
│
├── assets/
│   ├── aside-menu-bar-icon.png
│   ├── aside-app-icon.png
│   ├── AppIcon.icns
│   └── sounds/
│
├── docs/
│   ├── architecture.md          # thread model, data flow diagram
│   ├── voice-commands.md        # full command reference
│   └── custom-dictionary.md     # setup guide
│
└── Aside.app/                   # dev convenience bundle (NOT distributable — must stay in repo dir)
    └── Contents/
        ├── MacOS/Aside
        ├── Info.plist
        └── Resources/AppIcon.icns
```

### Module Responsibilities

| Module | Responsibility | Interface |
|--------|---------------|-----------|
| `engine/` | Transcription pipeline — audio capture, Whisper inference, hotkey detection, text injection. Framework-agnostic, no UI imports. | Callbacks: `on_status(state)`, `on_transcription(text)` |
| `commands/` | Voice command detection and execution. Sits between transcription output and text injection. Pure function parser + thin action wrappers. | `parse(text) → (commands, cleaned_text)` |
| `dictionary/` | Custom vocabulary — loads hotwords, builds initial_prompt, runs post-processing replacements. | `get_whisper_params() → (hotwords, initial_prompt)`, `apply_replacements(text) → text` |
| `punctuation/` | Auto-punctuation formatting — capitalization, spacing, cleanup. | `format(text, config) → text` |
| `ui/` | Thin shell — renders state, calls engine methods. Swappable to Swift/SwiftUI in future without touching core. Must schedule `engine.poll()` via `after(10ms)` to drain event queue. | Drives engine via public API, polls via `after(10, engine.poll)` |
| `config.py` | JSON config at `~/.aside/config.json`. Load, save, migrate from Hushed Hippo/WhisperDictation paths. | `load() → Config`, `save(config)` |

### Key Design Principle

`engine/` is framework-agnostic. It communicates via callbacks and could be driven by a CLI, a test harness, or a different UI framework. This is the core that must never break, and the reason a future SwiftUI frontend is feasible without rewriting the pipeline.

## Transcription Pipeline

8-stage linear pipeline. No branching, no async fan-out.

```
1. Hotkey Detection     → engine/hotkeys.py      [PROVEN]
2. Audio Capture        → engine/audio.py         [PROVEN]
3. Dictionary Pre-Proc  → dictionary/hotwords.py  [NEW]
     + context.py
4. Whisper Transcription → engine/transcriber.py  [PROVEN, enhanced]
5. Voice Command Detect → commands/parser.py      [NEW]
     + actions.py + numbers.py
6. Post-Processing      → dictionary/replacements [NEW]
     + punctuation/formatter.py
7. Text Injection       → engine/injector.py      [PROVEN]
8. Context Update       → dictionary/context.py   [NEW]
```

### Stage Details

**Stage 1 — Hotkey Detection:**
Quartz CGEventTap (active mode, option=0) monitors all keyboard events. The callback does two things: (1) reads hotkey attributes (`_hotkey_mod_mask`, `_hotkey_keycode`, `_toggle_mod_mask`, `_toggle_keycode`) for keystroke suppression — these are plain attribute reads that rely on CPython GIL atomicity, no locks acquired; (2) pushes raw key codes to a thread-safe queue via `queue.put_nowait()`. Main thread polls every 10ms. **Critical constraint:** the callback must NEVER acquire a `threading.Lock` — the GIL atomicity of individual attribute reads is sufficient for suppression logic, and lock contention would cause `kCGEventTapDisabledByTimeout` cycles.

**Stage 2 — Audio Capture:**
`sounddevice.InputStream` at 16kHz float32. Callback appends numpy frames to chunk list. On hotkey release, chunks concatenated to single 1D array. `stream.stop()` called on background thread (never main thread — it blocks).

**Stage 3 — Dictionary Pre-Processing (NEW):**
Before calling Whisper, two inputs are prepared:
- `hotwords`: all plain terms from `~/.aside/dictionary.txt`, joined as space-separated string
- `initial_prompt`: glossary priming sentence ("Terms: HIPAA, PHI, Acme Corp") + last 3 transcriptions (~500 tokens max)

**Important constraint:** In faster-whisper, `hotwords` has no effect if `prefix` is set. The Aside pipeline must NEVER set `prefix` when using hotwords. Additionally, `hotwords` and `initial_prompt` both influence the decoder prompt — implementation must include a validation step confirming they compose correctly (no token limit overflow, no one overriding the other). If interaction issues are found, fall back to packing all terms into `initial_prompt` only.

**Stage 4 — Whisper Transcription [PROVEN, ENHANCED]:**
Background thread calls `model.transcribe(audio, language=lang, hotwords=hotwords, initial_prompt=prompt, vad_filter=True)`. Segments joined to produce raw text. Model loaded async on startup, swappable via settings. The `language` parameter is NEW (default: `None` for auto-detect). The `vad_filter=True` enables Silero VAD to reduce hallucinations on silent segments.

**Stage 5 — Voice Command Detection (NEW):**
Parser scans transcribed text for command phrases using normalized lowercase matching with word boundary detection. Boundary detection algorithm: a command triggers if it appears (a) at the very start or end of the transcription, (b) immediately after punctuation (`. , ? !`), or (c) as the entire transcription. Embedded phrases (e.g., "I'll delete that section") do not trigger because "delete that" is mid-sentence with no preceding boundary. Parser returns `(commands_list, cleaned_text)`. Actions module executes each command via Quartz keystroke injection.

**"Delete that" state tracking:** The engine maintains `_last_injection_length` — the character count of the most recent text injection. When "delete that" fires, `actions.py` emits that many backspace keystrokes. If the user has manually edited the text between dictations, the backspaces may be imprecise — this is an acceptable limitation for v1 (Wispr has the same constraint).

**Number mode state:** Owned by `commands/numbers.py` as module-level state. Persists across transcriptions until explicitly toggled off with "words mode". Resets on app restart. The engine passes the numbers module to each parse call.

Command set:
| Phrase | Action |
|--------|--------|
| "new line" / "newline" | Inject `\n` |
| "new paragraph" | Inject `\n\n` |
| "period" / "full stop" | Inject `.` |
| "comma" | Inject `,` |
| "question mark" | Inject `?` |
| "exclamation point" / "exclamation mark" | Inject `!` |
| "delete that" | Backspace over last transcription (requires `_last_injection_length` tracked by engine) |
| "undo" | Cmd+Z |
| "select all" | Cmd+A |
| "copy that" / "copy all" | Cmd+C |
| "numbers mode" | Toggle ON: subsequent number words → digits (persists across transcriptions until toggled off) |
| "words mode" | Toggle OFF number mode |

**Stage 6 — Post-Processing (NEW):**
Two passes on cleaned text:
1. Dictionary replacements — regex find/replace from `→` lines in dictionary.txt. Case-insensitive word boundary matching.
2. Punctuation formatting — three configurable settings:
   - **Capitalization style:** sentence case (capitalize after `.?!`), as-spoken (preserve Whisper output), or off (all lowercase). Default: sentence case.
   - **Smart quotes:** convert straight quotes to curly quotes. Default: off.
   - **Trailing space:** auto-add space after punctuation marks. Default: on.

**Stage 7 — Text Injection:**
Quartz `CGEventCreateKeyboardEvent` — key down/up pairs for each character, posted to `kCGHIDEventTap`. Unicode-aware. Works in any text field system-wide.

**Stage 8 — Context Update (NEW):**
Append final transcribed text to rolling context buffer (FIFO, max 3 entries, ~500 tokens). Feeds back into Stage 3 for the next dictation, giving Whisper conversational context awareness.

### Performance Impact of New Stages

| Stage | Operation | Latency |
|-------|-----------|---------|
| 3. Dictionary Pre-Proc | Read text file, build strings | < 1ms |
| 5. Voice Commands | Regex scan on ~5-50 words | < 1ms |
| 6. Post-Processing | Regex replace + formatting | < 1ms |
| 8. Context Update | Append to list, trim | < 1ms |
| **Total new latency** | | **~2-4ms** |

For context: Whisper transcription (base model, 10s audio) takes 1,000-2,000ms. The four new stages add ~0.2% to total pipeline time. Imperceptible to the user.

The `hotwords` parameter may add ~50ms to beam search with a full 50-term dictionary. Negligible.

## Custom Dictionary

### File Format

Location: `~/.aside/dictionary.txt`

```
# Aside Custom Dictionary
# Max 50 terms
#
# HOTWORDS — terms Whisper should recognize
# One per line:
HIPAA
Kubernetes
kubectl
Dr. Ramirez
Acme Corp

# REPLACEMENTS — fix consistent misrecognitions
# Format: wrong → right
hip a → HIPAA
cube control → kubectl
doctor ramirez → Dr. Ramirez
a.w.s. → AWS
```

### Three Layers

1. **Hotwords** — plain terms passed to `transcribe(hotwords=...)`. Biases Whisper's beam search decoder toward these spellings.
2. **Context priming** — all hotword terms prepended to `initial_prompt` as a priming sentence, combined with rolling context from last 3 transcriptions.
3. **Replacements** — lines with `→` become case-insensitive regex find/replace rules applied after transcription. Runs in <1ms.

### File Parsing Rules

- Lines starting with `#` are comments (ignored)
- Blank lines and whitespace-only lines are ignored
- Lines containing `→` are replacements; the first `→` is the delimiter (allows `→` in replacement values)
- All other non-empty lines are hotwords
- File encoding: UTF-8 (supports international terms, accented characters)
- Total terms = hotwords + replacements. Cap of 50 applies to the sum.

### Error Handling

- **File missing:** graceful degradation — empty dictionary, no crash. Log warning. File created with template on next "Add" action.
- **File unreadable (permissions):** log error, show "Dictionary unavailable" in settings, continue without dictionary.
- **Malformed lines:** skip and log warning; don't fail the entire file parse.
- **Over 50 terms (external edit):** on Reload, parse first 50 terms, show warning "Dictionary has N terms, using first 50. Remove extras to add new terms."

### Settings UI

- Term count display: "14 / 50 terms"
- **Add Hotword:** text field + "Add" button → appends to dictionary.txt, auto-reloads
- **Add Replacement:** two text fields (wrong + right) + "Add" button → appends `wrong → right` line
- **"Edit Dictionary" button** → opens `~/.aside/dictionary.txt` in default text editor
- **"Reload" button** → re-parses file without restart
- **Validation:** over 50 terms → "Dictionary full" + disabled Add button. Duplicate → "Already in dictionary" flash. Empty field → Add button disabled.

### Design Rationale

Casual users add terms via the UI (one click, no file editing). Power users manage the full list via text file (bulk edit, git-track, share with teammates, script from internal glossaries). Both paths write to the same file — single source of truth.

## Privacy & Trust

### PRIVACY.md

Root-level document answering:
- **What data does Aside collect?** → None.
- **Where does audio go?** → RAM only. Captured → transcribed → deleted. Never written to disk.
- **Does Aside phone home?** → No network calls. No telemetry. No analytics. No crash reporting.
- **What about the Whisper model?** → Downloaded once during setup, runs locally. No API calls.
- **What about the dictionary?** → Local file at `~/.aside/dictionary.txt`. Never transmitted.
- **How can I verify?** → Code is open source. Grep for `urllib`, `requests`, `http`, `socket` — zero results.

### Architecture Documentation

`docs/architecture.md` includes a technical data flow diagram with explicit "no network" annotations at every stage. Target audience: security teams evaluating the tool for enterprise use.

### README Trust Section

Prominent "Privacy" section near the top of README (not buried):
> *Aside runs entirely on your machine. Your voice never leaves your Mac — no cloud APIs, no telemetry, no data collection. [Full privacy documentation →](PRIVACY.md)*

### Verifiable Claims

- `pyproject.toml` declares no network dependencies
- Homebrew formula notes: only network call is initial model download during install
- After install, Aside is fully air-gappable

## Distribution

### Repository

- Fresh repo at `github.com/blakeyoh/aside`
- Clean first commit (no Hushed Hippo git history)
- Apache 2.0 license from commit #1
- GitHub topics: `dictation`, `speech-to-text`, `whisper`, `privacy`, `macos`, `open-source`, `local-first`
- Issue templates for bug reports and feature requests

### Homebrew

- Tap repo at `blakeyoh/homebrew-aside`
- Install: `brew tap blakeyoh/aside && brew install aside`
- Formula handles: Python 3.13, venv, pip install, base model download
- Post-install caveats: Microphone + Accessibility + Input Monitoring permissions

### Config Migration

- First launch checks for config in this order: `~/.aside/config.json` (already migrated) → `~/Library/Application Support/HushedHippo/config.json` → `~/Library/Application Support/WhisperDictation/config.json` (original name)
- Migrates the first one found to `~/.aside/config.json`, adds new fields (`language`, `punctuation`) with defaults
- Creates `~/.aside/dictionary.txt` with commented template if it doesn't exist

### Config Schema

```json
{
  "model_size": "base",
  "language": null,
  "hotkey": {
    "modifiers": ["ctrl", "alt"],
    "trigger": "space"
  },
  "toggle_hotkey": null,
  "punctuation": {
    "capitalization": "sentence",
    "smart_quotes": false,
    "trailing_space": true
  }
}
```

- `language`: ISO 639-1 code (e.g., `"en"`, `"es"`, `"ja"`) or `null` for auto-detect. Default: `null`.
- `punctuation.capitalization`: `"sentence"` | `"as-spoken"` | `"off"`. Default: `"sentence"`.

### Launch Methods

- Terminal: `aside` (entry point via pyproject.toml console_scripts)
- .app bundle: `Aside.app` (must stay in repo directory for venv resolution)
- Dock: drag `Aside.app` to Dock, click to launch

## UI

### v1: customtkinter

The existing customtkinter UI carries forward with enhancements:
- New dictionary section (Add Hotword, Add Replacement, Edit Dictionary, Reload)
- Language dropdown
- Auto-punctuation preferences
- Rebrand (name, icon, colors)

### Future: SwiftUI (v2-v3)

Because `ui/` is a thin shell that calls engine methods and renders state, it can be replaced with a native SwiftUI frontend without touching engine/, commands/, dictionary/, or punctuation/. The interface between UI and engine is callbacks — `on_status(state)` and `on_transcription(text)`.

The settings window is open ~2% of the time. The invisible experience (hold hotkey → speak → text appears) is all engine-layer. UI polish is a v2-v3 investment once product-market fit is validated.

## Thread Model

Unchanged from Hushed Hippo — proven and stable.

```
Main Thread (customtkinter / Tk event loop)
  • after_idle() → start engine
  • after(10ms) → poll engine (drain event queue)
  • after(0) → update UI
  • Handles hotkey capture state machine

Background Thread "event-tap" (Quartz CFRunLoop)
  • CGEventTap (active mode, option=0)
  • Callback: read hotkey attributes (GIL-atomic) → suppress if match → put_nowait(ints) → return
  • Reads _hotkey_mod_mask, _hotkey_keycode, _toggle_mod_mask, _toggle_keycode without locks
  • Relies on CPython GIL atomicity for individual attribute reads
  • NEVER acquires threading.Lock (would cause tap-timeout cycles)

Background Threads "model-load" / "transcribe"
  • Load Whisper model async
  • Transcribe audio chunks
  • Access model under threading.Lock
  • stream.stop() runs here (never main thread)
```

**Critical invariant:** Event tap callback reads hotkey config attributes (relying on CPython GIL atomicity for individual reads) and writes raw Python ints via `queue.put_nowait()`. No lock acquisition ever. The `update_hotkey()` method writes config attributes under `threading.Lock` from the main thread — this asymmetry (locked writes, lockless reads) is safe because individual attribute reads are atomic under CPython's GIL. This prevents GIL deadlocks and `kCGEventTapDisabledByTimeout` cycles.

## Testing Strategy

### Unit Tests

| Module | Test File | Coverage Target |
|--------|-----------|----------------|
| `engine/transcriber.py` | `test_transcriber.py` | Model load, transcribe params, hotword/prompt injection |
| `commands/parser.py` | `test_commands.py` | All 10 commands + edge cases (embedded phrases, multiple commands) |
| `commands/numbers.py` | `test_numbers.py` | Number mode toggle, word→digit mapping, mixed input |
| `dictionary/hotwords.py` | `test_dictionary.py` | File parsing, hotword extraction, 50-term cap, validation |
| `dictionary/replacements.py` | `test_replacements.py` | Regex replacement, case insensitivity, boundary matching |
| `punctuation/formatter.py` | `test_formatter.py` | Capitalization styles, spacing cleanup |
| `config.py` | `test_config.py` | Load, save, migrate, defaults |

### Manual Test Checklist

1. Hold hotkey → speak → release → text typed at cursor
2. Toggle mode → press once → speak → press again → text typed
3. Say "new line" → newline injected
4. Say "delete that" → previous transcription removed
5. Say "numbers mode one two three words mode hello" → "123 hello"
6. Add hotword "HIPAA" → say "hipaa" → correctly capitalized
7. Add replacement "hip a → HIPAA" → say something misrecognized → corrected
8. Switch language → transcribe in that language → correct output
9. Fill dictionary to 50 terms → Add button disables
10. Edit dictionary externally → click Reload → changes reflected

### Target: 80%+ code coverage on new modules (commands/, dictionary/, punctuation/)

## Dependencies

| Package | Purpose | Version |
|---------|---------|---------|
| `faster-whisper` | Local Whisper inference (CTranslate2) | ≥1.0.0 |
| `sounddevice` | Audio capture (PortAudio) | ≥0.4.7 |
| `numpy` | Audio array processing | ≥1.26 |
| `pyobjc-framework-Quartz` | Event tap + text injection | ≥10.3 |
| `pyobjc-framework-Cocoa` | AppKit menu bar + notifications | ≥10.3 |
| `customtkinter` | Settings UI | ≥5.2.0 |
| `pillow` | Icon/image processing | ≥10.0.0 |

**System requirements:**
- macOS (Quartz framework)
- Homebrew Python 3.13
- portaudio (`brew install portaudio`)
- Microphone, Accessibility, and Input Monitoring permissions

**No new dependencies added.** All new features (voice commands, dictionary, punctuation) are pure Python string processing.

## Roadmap (Post-v1)

| Feature | Priority | Notes |
|---------|----------|-------|
| Interactive tutorial webpage | High | Practice voice commands with feedback — "training range" UX |
| Transcription history/log | Medium | Local searchable log of past dictations |
| System tray notifications | Low | Native macOS notifications for transcription complete/errors |
| SwiftUI frontend | Medium | Native Mac UI, replaces customtkinter |
| PyInstaller .dmg | Medium | Standalone distribution, no Python/venv required |
| Code signing + notarization | Medium | Requires Apple Developer account ($99/yr) |
| Tier 2 voice commands | Low | cap, all caps, tab, sleep/wake |
| Tier 3 voice commands | Low | Cursor movement, word selection, formatting |
