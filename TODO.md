# Aside — TODO

## v1 Completed (2026-03-22)
- ~~Extract and restructure Hushed Hippo into src/aside/ package~~
- ~~8-stage transcription pipeline~~
- ~~12 voice commands with boundary detection~~
- ~~Custom dictionary (hotwords + context priming + replacements)~~
- ~~Number dictation mode~~
- ~~Punctuation formatter~~
- ~~Config migration chain~~
- ~~Settings panel with dictionary UI~~
- ~~77 unit tests at v1 baseline~~
- ~~Privacy/architecture/voice-command docs~~
- ~~Apache 2.0 license, pushed to github.com/blakeyoh/aside~~

## v1.0.1 Completed (2026-04-24)
- ~~Voice-command sequencing and punctuation reliability~~
- ~~Push-to-talk modifier-release stop handling~~
- ~~Hotkey conflict rejection and capture cancel buttons~~
- ~~Finder/Dock launch visibility and stale install-path fallback~~
- ~~Transcribing menu-bar state~~
- ~~97 passing unit tests~~

## Next: Manual Smoke Test
- [ ] Run through `docs/smoke-test-plan.md` (6-phase Boeing FAI-style plan)
- [ ] Fix any bugs discovered during smoke testing
- [ ] Verify setup.sh works on a clean checkout on another machine
- [ ] Verify v1.0.1 Finder/Dock launch on a clean checkout: Settings opens, menu-bar icon appears, hotkey permissions prompt as expected

## Short-term
- ~~**Aside-branded menu bar icon**~~ — done 2026-03-29 (aside-logo.png → AppIcon.icns)
- [ ] **Homebrew formula** — `Formula/aside.rb` for `brew tap blakeyoh/aside && brew install aside`
- ~~**Transcribing state in menu bar icon**~~ — done 2026-04-24 (blue processing badge while Whisper runs)
- ~~**Hotkey capture cancel button**~~ — done 2026-04-24 (abort capture without pressing a combo)
- ~~**Reliability pass**~~ — done 2026-04-24 (inline command rendering, punctuation dedupe, modifier-release stop, hotkey conflict rejection)

## Medium-term
- [ ] **PyInstaller standalone .app** — 1-2 day prototype, 3-5 day reliable unsigned app; use `--onedir --windowed`, custom spec, icon, `Info.plist`, bundled assets, and manual smoke tests
- [ ] **Code signing / Gatekeeper notarization** — requires Apple Developer account ($99/yr)
- [ ] **Interactive tutorial webpage** — "training range" for practicing voice commands with feedback
- [ ] **Transcription history log** — last N results with timestamps, searchable
- [ ] **SwiftUI native frontend** — replace customtkinter; engine/ is already framework-agnostic

## Long-term
- [ ] Tier 2 voice commands: cap, all caps, tab, sleep/wake
- [ ] Tier 3 voice commands: cursor movement, word selection, formatting
- [ ] System tray notifications for transcription complete/errors
