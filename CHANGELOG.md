# Aside — CHANGELOG

## 2026-04-26 — v1.1.0: One-double-click install for non-technical users

- Self-contained `Aside.app` built with py2app — no Terminal, Homebrew, or `setup.sh` required for end users.
- Whisper `base` model bundled inside the `.app` (~140 MB) so first launch needs no network access; bundled model revision pinned to a Hugging Face commit SHA in CI for reproducible release artifacts.
- First-launch onboarding window walks the user through Microphone, Accessibility, and Input Monitoring permissions with green/red status dots, polling every 1.5 s, and "Open Settings" deep-links into the matching Privacy pane. Onboarding requires all three permissions before letting the user dismiss it; dismissing the window without granting them re-opens it on the next launch.
- `Permissions…` menu bar item re-opens the onboarding window on demand.
- Mic-denied path now surfaces the onboarding window instead of failing silently.
- Local DMG packaging (`scripts/package_dmg.sh`) with ad-hoc codesigning that preserves any upstream Developer ID signature.
- GitHub Actions release workflow (`.github/workflows/release.yml`) builds, ad-hoc signs, packages a DMG, and attaches it to a tag-triggered GitHub Release. Notarization steps stubbed in for after Apple Developer enrollment.
- README adds a Download section and right-click → Open first-launch instructions.
- Removed the committed `Aside.app/` shell launcher; end users get the `.dmg` from Releases, contributors continue to use `setup.sh`.
- `LSMinimumSystemVersion` set to 11.0; arm64-only target.

## 2026-04-24 — v1.0.1: Reliability fixes

- Fixed voice-command sequencing: punctuation and line-break commands now render inline with the dictated text instead of being injected before the transcript.
- Made spoken punctuation commands primary while preserving Whisper punctuation elsewhere; duplicate nearby punctuation such as `period.` or `. period` collapses to one mark.
- Fixed push-to-talk getting stuck when modifier keys are released before the trigger key by handling `kCGEventFlagsChanged`.
- Rejected identical push-to-talk and toggle hotkeys so hands-free mode cannot be silently shadowed by push-to-talk.
- Improved hotkey capture UX with Cancel buttons and visible error status when hotkey polling fails.
- Improved `.app` launch reliability: Finder/Dock launch opens Settings on startup, logs resolved project/venv paths, validates stale install paths, and falls back to the bundle-relative checkout.
- Added a distinct transcribing menu-bar state and kept the idle menu bar item icon-only when the icon loads.
- Added parser/transcriber/hotkey regression coverage; unit test count is now 97.

## 2026-03-29 — Cross-machine install hardening + UI fixes

- Fixed "shows as Python" in Dock/Cmd+Tab: changed `NSApplicationActivationPolicyRegular` → `NSApplicationActivationPolicyAccessory` in `menubar.py`
- Settings window now scrollable via `CTkScrollableFrame`; fixed window geometry to 480×680
- Replaced hippo placeholder with Aside-branded menu bar icon and header icon (`aside-logo.png` → `AppIcon.icns`)
- `setup.sh`: auto-installs Python 3.13 via Homebrew if missing; adds `chmod +x` on launcher, `xattr -cr` to clear Gatekeeper quarantine, writes `~/.aside/install_path.txt`
- `.app` launcher now reads `~/.aside/install_path.txt` first — allows `Aside.app` to live in `/Applications`
- Fixed `.gitignore`: bare `app.py` pattern was silently excluding `src/aside/ui/app.py` from the repo; anchored to `/app.py`
- Added `generate-icon.sh` to regenerate `AppIcon.icns` from `aside-logo.png`
- Updated README Quick Start with accurate clone URL, permissions table, and Gatekeeper note
- Files: `menubar.py`, `app.py`, `setup.sh`, `Aside.app/Contents/MacOS/Aside`, `AppIcon.icns`, `.gitignore`, `README.md`, `generate-icon.sh`

## 2026-03-22 — Aside v1: Full extract, restructure, and rebrand

- Extracted Hushed Hippo into `src/aside/` package (23 modules, 5 subpackages: engine/, commands/, dictionary/, punctuation/, ui/)
- 8-stage transcription pipeline: hotkey → audio → dictionary pre-proc → whisper → voice commands → post-processing → text injection → context update
- 12 voice commands with boundary detection (dictation at word boundary, action at sentence boundary)
- Custom dictionary: 3 layers (hotwords, context priming, regex replacements), 50-term cap, `~/.aside/dictionary.txt`
- Number dictation mode with `_join_tokens` concatenation ("one two three" → "123")
- Punctuation formatter: sentence/as-spoken/off capitalization, smart quotes, trailing space
- Config migration chain: WhisperDictation → HushedHippo → Aside
- Settings panel: model, language, hotkey, toggle hotkey, dictionary UI, punctuation preferences
- 77 unit tests, Apache 2.0 license, privacy/architecture/voice-command docs
- Boeing FAI-style manual smoke test plan at `docs/smoke-test-plan.md`
- Pushed to dedicated repo: github.com/blakeyoh/aside

## Pre-Aside History (Hushed Hippo era)

## 2026-03-14 — Hushed Hippo rebrand + customtkinter UI upgrade
- Full rebrand: "Whisper Dictation" → "Hushed Hippo"; bundle, config path, logs, lock file all renamed
- UI migrated from vanilla tkinter → customtkinter (dark theme, #00E5FF Sterile Cyan accent, corner radii, CTk widgets throughout)
- Quiet launch: app starts hidden, window appears only via Settings... in menu bar or Dock click; WM_DELETE_WINDOW → withdraw (not quit)
- Menu bar: PNG template icon (hippo silhouette, auto dark/light inversion via setTemplate_); About dialog added; emoji status icons removed
- Recording state: amber circle composited behind hippo icon in menu bar while recording; idle hippo restored on transcription complete
- Header: hippo logo (CTkImage via Pillow) + tagline added; all body fonts bumped +1pt
- Dependency: added `pillow>=10.0.0` (required for CTkImage in header)
- Bug fix: `stream.stop()` moved from main thread to background `_transcribe()` thread — eliminates UI freeze on toggle hotkey stop
- Bug fix: NSStatusBarButton handles template image scaling; removed broken `lockFocus`/`drawInRect_` resize approach
- PortAudio warmup: after model loads, briefly open/close stream to pre-initialize audio device; eliminates ~200ms first-recording latency
- Config auto-migrated from WhisperDictation/ to HushedHippo/ on first launch; AppIcon.icns rebuilt from hushed-hippo-app-icon.png

## 2026-03-13 — Backend swap, toggle mode, space-key suppression, UX fixes
- Replaced `openai-whisper` + `torch` with `faster-whisper` + `ctranslate2` — eliminates Python 3.13 semaphore leak crashes; 2-4x faster, no multiprocessing
- Added toggle (hands-free) hotkey: second configurable hotkey starts recording on press, stops+transcribes on second press
- Active event tap (`kCGEventTapOptionDefault = 0`) suppresses trigger keydowns — space no longer types while held
- Accessibility UX: "Grant Access in System Settings" button appears automatically when tap returns None
- Config moved to `~/Library/Application Support/WhisperDictation/config.json` (survives git updates)

## 2026-03-06 — macOS 26 crash fix: Quartz event tap + GIL isolation
- Replaced pynput keyboard listener with Quartz `CGEventTapCreate` on a dedicated background thread
- Fixed GIL corruption crash: event tap on own CFRunLoop, events via queue, drained by `poll()` in Tk `after()` loop
- Fixed silent transcription failures: `finally: _on_status("ready")` was overwriting errors

## 2026-03-06 — Initial build
- Created local Whisper dictation app for macOS: push-to-talk hotkey, transcribes via local Whisper model, types text at cursor
- Text injection uses Quartz `CGEventCreateKeyboardEvent` — clipboard is never modified
- Proper `.app` bundle with `Info.plist`
