# Aside Architecture

Aside is a macOS voice dictation app with a Python engine, a customtkinter settings/onboarding UI, and AppKit menu-bar integration. The app supports two install paths:

- **User mode:** a py2app-built `Aside.app` distributed in a DMG with the base Whisper model bundled under `Aside.app/Contents/Resources/`.
- **Developer mode:** a source checkout with `.venv`, launched with `.venv/bin/python3 -m aside` or built locally with `scripts/build_app.sh dev`.

## Transcription Pipeline

Audio flows through eight stages:

```
1. Hotkey detection      src/aside/engine/hotkeys.py
        |
        v
2. Audio capture         src/aside/engine/audio.py
        |
        v
3. Dictionary context    src/aside/dictionary/hotwords.py
                         src/aside/dictionary/context.py
        |
        v
4. Whisper transcription src/aside/engine/transcriber.py
        |
        v
5. Voice command parse   src/aside/commands/parser.py
                         src/aside/commands/actions.py
                         src/aside/commands/numbers.py
        |
        v
6. Post-processing       src/aside/dictionary/replacements.py
                         src/aside/punctuation/formatter.py
        |
        v
7. Text injection        src/aside/engine/injector.py
        |
        v
8. UI/menu feedback      src/aside/ui/app.py
                         src/aside/ui/menubar.py
```

## Thread Model

```
Main thread (Tk)
  - Renders Settings and onboarding windows
  - Owns AppKit menu callbacks by scheduling work back onto Tk with after()
  - Polls HotkeyManager every 10 ms
  - Never blocks on Whisper model loading or stream.stop()

Event-tap thread (CFRunLoop)
  - Receives Quartz key events
  - Pushes raw event ints into a queue
  - Does not acquire Python locks
  - Re-enables the event tap after timeout

Worker threads
  - model-load: loads faster-whisper
  - transcribe: stops audio, runs the pipeline, injects text
  - audio warmup: initializes PortAudio away from the UI thread
```

This structure avoids the two failure modes that previously caused crashes: running the Quartz event tap on Tk's main loop, and doing blocking audio work on the UI thread.

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `src/aside/__main__.py` | Console and `python -m aside` entry point |
| `src/aside/config.py` | `~/.aside/config.json`, defaults, migration, dictionary template |
| `src/aside/resources.py` | Resource lookup for source checkout vs py2app bundle |
| `src/aside/permissions.py` | Microphone, Accessibility, Input Monitoring checks plus native permission requests and System Settings links |
| `src/aside/engine/hotkeys.py` | Quartz event tap, hotkey capture, graceful no-Quartz degradation |
| `src/aside/engine/audio.py` | `sounddevice` input stream and RAM buffer management |
| `src/aside/engine/transcriber.py` | faster-whisper model loading and stages 3-8 of the pipeline |
| `src/aside/engine/injector.py` | Quartz keystroke/text injection |
| `src/aside/ui/app.py` | Main app shell, lifecycle, startup visibility, state machine |
| `src/aside/ui/menubar.py` | AppKit status item, visible app icon, and menu actions |
| `src/aside/ui/onboarding.py` | First-run permissions gate |
| `src/aside/ui/settings.py` | Settings panel widgets and dictionary controls |

## Packaging Flow

```
setup.sh
  -> installs Homebrew Python 3.13 + python-tk@3.13 + portaudio
  -> creates .venv
  -> pip install -e .
  -> installs py2app, huggingface_hub, pytest
  -> downloads faster-whisper base into the developer cache

scripts/build_app.sh dev
  -> verifies packaging inputs and importable modules
  -> downloads vendor/models/faster-whisper-base
  -> runs python setup_py2app.py py2app -A
  -> produces dist/Aside.app for local app-mode testing

scripts/build_app.sh release
  -> requires MODEL_REVISION to be a pinned 40-char Hugging Face SHA
  -> bundles the pinned model into dist/Aside.app
  -> produces the release app for scripts/package_dmg.sh
```

`Info.plist` sets `LSUIElement=false`, so Aside is a regular Dock-enabled app. It still creates a menu-bar status item for day-to-day control.

## Launch Lifecycle

Startup always shows something visible:

- If `first_run_complete` is false or missing, Aside opens onboarding.
- When onboarding completes, Aside persists `first_run_complete=true` and opens Settings.
- On later launches, Aside opens Settings automatically.
- Closing Settings withdraws the window. The app continues running until `Quit Aside` is selected from the menu bar.

## Package Structure

```
.
├── Info.plist
├── AppIcon.icns
├── aside-logo.png
├── setup.sh
├── setup_py2app.py
├── scripts/
│   ├── build_app.sh
│   └── package_dmg.sh
├── src/aside/
│   ├── __main__.py
│   ├── config.py
│   ├── permissions.py
│   ├── resources.py
│   ├── commands/
│   ├── dictionary/
│   ├── engine/
│   ├── punctuation/
│   └── ui/
├── tests/
└── docs/
```
