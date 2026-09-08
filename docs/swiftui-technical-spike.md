# SwiftUI Technical Spike

This spike proves the proposed native SwiftUI shell plus supervised local Python
helper architecture without replacing the current customtkinter app.

## Historical Decision

Status: the source-checkout spike passed at the time recorded below. It is
evidence for the architecture, not proof that the current installed, signed
candidate passes permissions, distribution, recovery, or end-to-end dictation.

Use the [current release audit](swiftui-release-audit-2026-09-08.md) for active
scope, sequencing, and release gates.

## Architecture

- `native/AsideShell/` is a SwiftPM macOS SwiftUI executable.
- `src/aside/helper.py` is a Python stdio helper using newline-delimited JSON.
- IPC is stdio only. There is no localhost HTTP, WebSocket, or network-style
  transport.
- The SwiftUI shell owns window/menu-bar presentation, helper launch/restart,
  status rendering, permission rows, and manual smoke controls.
- The Python helper still owns Whisper model loading, audio capture, hotkey
  handling, recording/transcribing state transitions, text injection,
  dictionary/replacements/voice commands, and config compatibility.

The helper emits these shell-facing events:

- `hello`
- `permissions`
- `status` with `loading`, `ready`, `recording`, `transcribing`, or `error`
- `transcription`
- `config`
- `error`
- `exit`

The shell sends these commands:

- `startRecording`
- `stopRecording`
- `getPermissions`
- `requestPermission`
- `reloadConfig`
- `shutdown`

## Build And Run

From the repo root:

```bash
./setup.sh
scripts/run_swiftui_spike.sh
```

For a bounded non-dictation launch check:

```bash
scripts/smoke_swiftui_launch.sh
```

Equivalent explicit commands:

```bash
swift build --package-path native/AsideShell
ASIDE_REPO_ROOT="$PWD" ASIDE_PYTHON="$PWD/.venv/bin/python3" \
  native/AsideShell/.build/debug/AsideShell
```

The shell prefers `ASIDE_PYTHON`, then `$ASIDE_REPO_ROOT/.venv/bin/python3`,
then `/usr/bin/python3`. The run script rejects missing venv Python so the
verified path does not depend on a global interpreter.

Automated subprocess protocol checks may set `ASIDE_HELPER_PROTOCOL_SMOKE=1`.
That mode is intentionally narrow: it proves the real helper entry point,
stdio protocol, permission snapshot event, and shutdown behavior without
loading Whisper, opening an event tap, or touching the microphone. It is not a
replacement for the manual dictation smoke gate below.

## Packaging Direction

The credible packaging path is a native macOS app bundle that embeds:

- the compiled SwiftUI shell as the main executable
- the existing Python helper environment in the standard
  `Contents/Helpers/AsideHelper.app` nested-code location
- the bundled faster-whisper model resources already used by the py2app path
- narrowly scoped helper runtime/audio entitlements, with Accessibility and
  Input Monitoring grants attributed to the installed app identity

The native release workflow now builds the SwiftUI shell with an embedded
py2app helper. The standalone customtkinter bundle is compatibility-only.
Installed-app permission identity, Developer ID signing, and notarization still
require fresh evidence for the final candidate.

## Technical Spike Gate Checklist

Pass/fail this list before Phase 2:

1. SwiftUI shell launches the Python helper and shows a running helper state.
2. Helper reports `loading`, `ready`, `recording`, `transcribing`, and `error`
   states in the shell event log.
3. Existing push-to-talk hotkey starts recording and release stops recording.
4. Existing toggle hotkey starts/stops recording if configured.
5. Manual Start Recording / Stop and Transcribe controls capture microphone
   audio.
6. Transcription uses the existing Python `Transcriber` pipeline.
7. Text injection inserts dictated text into another focused app.
8. Microphone, Accessibility, and Input Monitoring prompts/statuses appear under
   an acceptable app identity.
9. Quitting the SwiftUI app shuts down the helper without leaving an active
   event tap or recording stream.
10. Build/run steps work from a clean checkout after `./setup.sh`.

Stop and do not continue to visual migration if any item fails, or if the
permission prompts identify an unacceptable helper process.

## Verification So Far

Automated checks run:

```bash
.venv/bin/python3 -m pytest tests/test_swiftui_helper.py -v
.venv/bin/python3 -m pytest tests/test_swiftui_helper_subprocess.py -v
swift build --package-path native/AsideShell
scripts/smoke_swiftui_launch.sh
```

The Swift build was verified with SwiftPM caches redirected in the agent
sandbox. A normal contributor should use `scripts/run_swiftui_spike.sh`.

Manual smoke evidence captured:

- SwiftUI app launched and displayed `Ready`.
- SwiftUI shell showed the helper running from the project venv.
- Microphone, Accessibility, and Input Monitoring displayed as `granted`.
- Manual recording reached `recording`, then `transcribing`, then `ready`.
- Faster Whisper processed captured audio and detected English.
- Helper emitted transcription text: `I think it works, exclamation mark.`
- Text injection entered dictated text into another focused app text box.
- Hotkey behavior was confirmed.
- Quit cleanup was confirmed.

Spike gate result: passed.

## Phase 2 Visual Migration Status

Implemented in `native/AsideShell/Sources/AsideShell/AsideShellApp.swift`:

- main settings shell with app identity/header, native sidebar navigation, and
  first-viewport Aside logo asset
- dictation controls with push-to-talk/toggle segmented mode and hotkey keycaps
- hotkey capture/cancel for push-to-talk and toggle shortcuts, plus clear toggle
- local model and language controls that update the existing Python config
- punctuation controls for capitalization, smart quotes, and trailing space
- dictionary access/status panel with add/remove hotwords, add/remove
  replacements, reload, and edit-file actions
- voice command status panel for the built-in parser commands
- privacy/local-only status strip
- first-run style permissions/onboarding panel with live granted/missing state
  System Settings actions, and a disabled/enabled Continue gate
- menu bar popover states for idle/ready, recording, transcribing, loading, and
  error, plus settings, permissions, helper restart, and quit actions
- reusable SwiftUI design tokens for graphite, off-white, slate, blue, amber,
  green, red, spacing, radius, badges, permission rows, hotkey keycaps, and
  panel surfaces

Asset note: the SwiftUI shell loads `assets/NEW-aside-logo.png` from the repo
when run locally. Production app/menu-bar icon generation should wait for the
new native packaging path so the generated `.icns`, menu-bar template asset,
signing, and notarization are handled together.

Follow-up packaging recommendation:

- embed the SwiftUI executable as the app bundle main process
- embed the Python helper environment and bundled model resources
- sign/notarize with the required microphone/accessibility/input-monitoring
  entitlements
- confirm permission prompts are attributed to the final signed app identity,
  not a confusing helper/interpreter identity

Functional restoration note: the old customtkinter app did not include custom
voice-command creation/removal. The SwiftUI voice-command panel is therefore
read-only for built-in parser commands until a real persisted command schema is
designed.

## Next SwiftUI Follow-ups

1. Menu-bar icon polish: idle state currently appears as a checkmark. Replace it
   with an Aside-specific menu-bar mark, such as an `A` in a circle or a compact
   template-style version of the app icon.
2. Copy reduction: decrease the amount of copy throughout the app. Keep the
   core privacy language, but remove redundant explanatory text from panels.
3. Content dedupe: General should summarize the app; dedicated tabs should own
   the detailed controls. Avoid showing the same cards in multiple places.
4. Dictionary upgrade: make the dictionary feel like a real editor rather than
   a `.txt` file wrapper. Users should be able to add and remove terms freely,
   and the UI should explain when to use a hotword versus a replacement.
5. Voice-command audit: double-check that every built-in command from
   `src/aside/commands/parser.py` is represented in the SwiftUI panel and docs.
   If custom commands are desired, design a persisted command schema first.
6. About tab: either remove it or expand it with concise README-like content:
   what Aside does, local/privacy guarantees, version/build info, and relevant
   docs links.
7. Tutorial tab: add a practice/testing ground for hotkeys and voice commands,
   including sample prompts users can read aloud and feedback on what was
   detected.
8. Alignment polish: make sure all left menu labels are left-aligned and that
   text, badges, fields, and buttons align consistently across panels.
9. Installed-app visual smoke: verify the new app icon appears in the Dock when
   launched from `/Applications`, not only from the source checkout.

Completed follow-up: native SwiftUI release packaging and CI smoke coverage now
exist via `scripts/build_swiftui_app.sh`, `scripts/package_swiftui_dmg.sh`,
`scripts/verify_swiftui_bundle.sh`, `scripts/smoke_swiftui_launch.sh`, build
smoke, release rehearsal, and tag release workflow gates.
