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
- ~~77 unit tests~~
- ~~Privacy/architecture/voice-command docs~~
- ~~Apache 2.0 license, pushed to github.com/blakeyoh/aside~~

## Next: Manual Smoke Test
- [ ] Run through `docs/smoke-test-plan.md` (6-phase Boeing FAI-style plan)
- [ ] Fix any bugs discovered during smoke testing
- [ ] Verify setup.sh works on a clean checkout

## Short-term
- [ ] **Aside-branded menu bar icon** — replace hippo placeholder with Aside icon
- [ ] **Homebrew formula** — `Formula/aside.rb` for `brew tap blakeyoh/aside && brew install aside`
- [ ] **Transcribing state in menu bar icon** — distinct visual while Whisper processes (not just recording)
- [ ] **Hotkey capture cancel button** — abort without pressing a combo

## Medium-term
- [ ] **PyInstaller standalone .app** — bundles Python + venv + app; true zero-setup sharing
- [ ] **Code signing / Gatekeeper notarization** — requires Apple Developer account ($99/yr)
- [ ] **Interactive tutorial webpage** — "training range" for practicing voice commands with feedback
- [ ] **Transcription history log** — last N results with timestamps, searchable
- [ ] **SwiftUI native frontend** — replace customtkinter; engine/ is already framework-agnostic

## Long-term
- [ ] Tier 2 voice commands: cap, all caps, tab, sleep/wake
- [ ] Tier 3 voice commands: cursor movement, word selection, formatting
- [ ] System tray notifications for transcription complete/errors
