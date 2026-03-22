# Aside Architecture

## Transcription Pipeline

Audio flows through 8 stages from microphone capture to text output:

```
1. Hotkey capture        src/aside/hotkey.py
        |
        v
2. Audio capture         src/aside/audio.py
        |
        v
3. VAD (silence trim)    src/aside/vad.py
        |
        v
4. Whisper transcription src/aside/engine.py
        |
        v
5. Voice command parse   src/aside/commands.py
        |
        v
6. Dictionary apply      src/aside/dictionary.py
        |
        v
7. Text injection        src/aside/injector.py
        |
        v
8. UI feedback           src/aside/ui.py
```

## Thread Model

Aside uses three execution contexts to keep the UI responsive and avoid blocking the Quartz event tap:

```
Main thread (Tk)
  - Renders the menubar UI
  - Polls a queue for transcription results via after()
  - Never blocks on audio or Whisper

Event-tap background thread (CFRunLoop)
  - Intercepts global hotkey events via CGEventTap
  - Posts start/stop signals to an audio queue
  - Holds no Python locks (GIL isolation requirement)
  - Never calls Tk or PyObjC UI methods

Worker threads (ThreadPoolExecutor)
  - Audio capture runs in a dedicated thread
  - Whisper inference runs in a dedicated thread
  - Results posted to the main-thread queue
```

This structure avoids two known failure modes:
- Adding a CGEventTap to `CFRunLoopGetMain()` while Tk is running causes GIL corruption
- Acquiring Python locks inside the Quartz callback causes deadlocks

See instinct `quartz-eventtap-gil-isolation` for implementation details.

## Module Responsibilities

| Module | Responsibility |
|--------|---------------|
| `src/aside/app.py` | Entry point; wires all modules together, starts Tk mainloop |
| `src/aside/hotkey.py` | CGEventTap setup and hotkey detection |
| `src/aside/audio.py` | Microphone capture into RAM buffer via PyAudio |
| `src/aside/vad.py` | Voice activity detection; trims leading/trailing silence |
| `src/aside/engine.py` | Whisper model loading and transcription |
| `src/aside/commands.py` | Voice command tokenization and action dispatch |
| `src/aside/dictionary.py` | Loads `~/.aside/dictionary.txt`, applies hotwords and replacements |
| `src/aside/injector.py` | Types text at cursor via Quartz CGEventCreateKeyboardEvent |
| `src/aside/ui.py` | customtkinter menubar window and status indicators |
| `src/aside/config.py` | Reads/writes `~/.aside/config.json` |

## Package Structure

```
aside/
├── app.py                  # Legacy entry point (wraps src/)
├── run.sh                  # Shell launcher
├── setup.sh                # Venv + dep installer
├── requirements.txt
├── pyproject.toml
├── Aside.app/              # macOS app bundle
├── src/
│   └── aside/
│       ├── app.py          # Entry point
│       ├── hotkey.py       # CGEventTap hotkey handling
│       ├── audio.py        # Microphone capture
│       ├── vad.py          # Voice activity detection
│       ├── engine.py       # Whisper transcription
│       ├── commands.py     # Voice command parser
│       ├── dictionary.py   # Custom dictionary
│       ├── injector.py     # Quartz text injection
│       ├── ui.py           # customtkinter UI
│       └── config.py       # Config management
├── tests/
│   ├── test_engine.py
│   ├── test_commands.py
│   ├── test_dictionary.py
│   └── test_injector.py
└── docs/
    ├── architecture.md     # This file
    ├── voice-commands.md
    └── custom-dictionary.md
```
