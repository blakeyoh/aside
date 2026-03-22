# Hushed Hippo — CLAUDE.md

Local macOS dictation app. Push-to-talk and toggle hotkeys capture audio, transcribe with Whisper, and type text at the cursor via Quartz keyboard events. No clipboard, no cloud.

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

## Setup & Launch

```bash
./setup.sh          # one-time: creates .venv, installs deps, downloads base model
./run.sh            # launch via Terminal
# OR: double-click HushedHippo.app / click Dock icon
```

Logs always go to `~/Library/Logs/HushedHippo/hushed-hippo.log`. Check there first when debugging.

## Key Files

| File | Role |
|---|---|
| `engine.py` | DictationEngine: event tap, recording, transcription, text injection |
| `app.py` | App (ctk.CTk): settings UI, status display, engine lifecycle |
| `setup.sh` | Venv creation, pip install, model download, dep verification |
| `run.sh` | Terminal launcher (activates venv, runs app.py) |
| `test_engine.py` | Smoke tests — run with `.venv/bin/python3 test_engine.py` |
| `requirements.txt` | Pinned minimum versions |
| `HushedHippo.app/` | .app bundle — launcher at `Contents/MacOS/HushedHippo` |

**Config lives at** `~/Library/Application Support/HushedHippo/config.json`. Auto-migrated from `WhisperDictation/` on first launch.

## Thread Model

```
Main thread (Tk):
  after_idle → _start_engine → DictationEngine.__init__
  after(10ms) → _poll_engine → engine.poll() → _process_event()
  after(0) → _update() [status updates, UI changes]

Background thread "event-tap":
  CFRunLoopRun() → CGEventTap callback → queue.put_nowait(raw ints)
  NEVER touches Python objects beyond the queue put

Background thread "model-load" / "transcribe":
  _load_model() / _transcribe() → self._lock for model access
  calls self._on_status() → which calls self.after(0, _update)
```

## UI Architecture

```
App (ctk.CTk)  ← starts withdrawn (quiet launch)
  ├── Header section  (title, status dot, status label, Grant Access btn)
  ├── Divider (tk.Frame, 1px)
  ├── Preview section  (last transcription)
  ├── Divider
  ├── Instructions section  (numbered steps, optional toggle step)
  ├── Divider
  └── Settings section  (model dropdown, hotkey rows, Apply Model btn)

Menu bar (NSStatusBar):
  Icon: hushed-hippo-menu-bar-icon.png (RGBA, setTemplate_=True)
  Recording: amber circle composited over hippo (NSBezierPath + NSColor)
  Menu: About | --- | Settings… | --- | Quit Hushed Hippo
```

## Critical Gotchas

### Quiet launch
The app starts withdrawn (`self.withdraw()` immediately after `super().__init__()`).
The window only appears when the user clicks "Settings…" in the menu bar or the Dock icon.
`WM_DELETE_WINDOW` → `self.withdraw()` (not quit). Engine keeps running in background.

### customtkinter init order
`ctk.set_appearance_mode()` and `ctk.set_default_color_theme()` MUST be called BEFORE
`super().__init__()`. Calling them after is a silent failure.

### Widget API differences from tkinter
- `.config(fg=...)` does NOT work on ctk widgets — use `.configure(text_color=...)`
- `.config(bg=...)` → `.configure(fg_color=...)`
- CTkFrame padx/pady go to `.pack()`, not the constructor
- CTkButton has no `relief`, `padx`, `pady` — use `corner_radius`, `width`, `height`

### Quartz callback — keep it minimal
The CGEventTap callback runs on the background CFRunLoop thread. **Never acquire a Python `threading.Lock()` inside it.** The GIL contention will cause `kCGEventTapDisabledByTimeout` cycles. The callback must only: read event fields, `queue.put_nowait(raw ints)`, check plain attribute reads, return.

See instinct: `quartz-eventtap-gil-isolation`

### `kCGEventTapOptionDefault` is not exported by pyobjc
Use the integer `0` directly. pyobjc exports `kCGEventTapOptionListenOnly = 1` but not the default value 0.

```python
# WRONG:
kCGEventTapOptionDefault,   # NameError at runtime

# CORRECT:
0,   # kCGEventTapOptionDefault — pyobjc doesn't export this constant
```

### `.app` bundle must stay in the project directory
`HushedHippo.app/Contents/MacOS/HushedHippo` resolves `.venv` by walking `../../..` from the bundle. Dragging the `.app` to `/Applications` breaks it. Dock it from `~/claude-code/whisper-dictation/`.

### `_toggle_recording` must be reset on error paths
If `sd.PortAudioError` fires in `_start_recording`, reset BOTH `self._recording = False` AND `self._toggle_recording = False`. Otherwise the toggle state gets stuck and the next press skips directly to stop.

### `sounddevice.InputStream.stop()` blocks the calling thread
`stop()` waits for the PortAudio audio callback to drain before returning. **Never call it on the main thread** (Tk/CTk event loop). In `_stop_and_transcribe()` the stream reference is passed to the background `_transcribe()` thread, which calls `stop()/close()` there.

### `NSImage.lockFocus()` is unreliable in a hybrid Tk/AppKit app
`lockFocus()` requires an NSGraphicsContext that may not exist when `after_idle()` fires (Tk hasn't set one up for AppKit). Creating a new NSImage with `initWithSize_` + `lockFocus` + `drawInRect_` produces a blank/transparent image. **Workaround**: hand the raw PNG NSImage directly to `NSStatusBarButton.setImage_()` — the button scales template images automatically.

## Testing

```bash
.venv/bin/python3 test_engine.py    # 8 unit tests: parse_hotkey + faster-whisper import
```

Manual test checklist:
1. `./run.sh` → no window appears; menu bar hippo icon visible
2. Click "Settings…" → window appears centered
3. Close window (X) → window hides, app keeps running (check menu bar)
4. Hold hotkey → speak → release → text typed at cursor; menu bar icon shows amber circle while recording
5. Set toggle hotkey → press once → "Recording…" → press again → text typed
6. Apply Model → "Loading model…" → "Ready"
7. Change hotkey → new combo works
8. Launch second instance → single-instance alert
9. Revoke Accessibility → relaunch → "Grant Access" button appears, opens System Settings
10. Switch macOS light/dark mode → menu bar hippo icon inverts correctly

## Deferred Work

See `TODO.md`. Key open items:
- PyInstaller standalone `.app` (true zero-setup sharing)
- Code signing / Gatekeeper notarization
- Hotkey capture cancel button
- Transcribing state indicator in menu bar icon (distinct from recording)
