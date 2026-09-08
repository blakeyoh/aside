# Aside

**Private voice dictation for Mac.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-13%2B%20Apple%20Silicon-lightgrey.svg)](https://www.apple.com/macos/)

Aside is a local-first voice dictation app for macOS. It uses OpenAI's Whisper model running entirely on your machine — no subscriptions, no cloud APIs, no audio ever leaving your computer. Hold a hotkey to dictate, release to transcribe, and your words appear wherever your cursor is.

## Privacy

Your audio never leaves your Mac. Aside makes zero network calls during normal operation — it works identically whether or not you're connected to the internet. No telemetry, no analytics, no crash reporting. See [PRIVACY.md](PRIVACY.md) for the full breakdown, including how to verify it yourself.

## Features

- **Push-to-talk and toggle modes** — hold a hotkey to dictate, or toggle recording on/off
- **Voice commands** — 12 built-in commands for punctuation, line breaks, undo, copy, and more
- **Custom dictionary** — add up to 50 domain-specific terms and correction rules
- **Multi-language support** — 20 languages via Whisper's multilingual model
- **Auto-punctuation** — Whisper infers punctuation from speech patterns
- **Menubar app** — lives in your menubar, out of your way

## Download

The latest published release is the legacy v1.2.1 app. The native SwiftUI 1.3.0 candidate is still being qualified and must not be published until its Developer ID, notarization, installed-app permission identity, and release gates pass. Track that work in the [SwiftUI release audit](docs/swiftui-release-audit-2026-09-08.md).

The intended native release artifact is `Aside-SwiftUI-x.x.x.dmg` for macOS 13 or later on Apple Silicon. It bundles the base Whisper model, so normal use requires no Terminal, Homebrew, global Python, model download, cloud API, or telemetry.

---

## Developer Setup

**Requirements:** macOS 13+ on Apple Silicon, Homebrew, and Xcode Command Line Tools. Python 3.13 is installed automatically if missing.

```bash
git clone https://github.com/blakeyoh/aside.git
cd aside
./setup.sh
```

`setup.sh` installs all dependencies, downloads the Whisper `base` model (~140 MB, one-time), and prepares the local Python environment. This takes a few minutes on first run.

### Grant permissions (required)

Aside needs three permissions in **System Settings → Privacy & Security**. Add whichever terminal app you ran `setup.sh` from (Terminal, iTerm2, Warp, etc.) to each list. If you launch via Finder, add `Aside.app` as well.

| Permission | Why |
|---|---|
| **Microphone** | Capture your voice |
| **Accessibility** | Type text into other apps |
| **Input Monitoring** | Detect hotkey while another app is focused |

macOS will prompt for most of these on first use — click **Allow**.

### Launch

```bash
source .venv/bin/activate && python -m aside
```

First launch shows the permissions onboarding window. After permissions are complete, terminal and app launches open Settings so startup is visible and easy to validate. A microphone icon appears in your menu bar when Aside is running. It turns amber while recording and blue while transcribing. **Default hotkey:** hold `⌃ ⌥ Space` to record, release to transcribe.

To smoke-test the SwiftUI shell from a source checkout:

```bash
source .venv/bin/activate
scripts/smoke_swiftui_launch.sh
scripts/run_swiftui_spike.sh
```

To build the current native candidate locally with the reviewed model revision:

```bash
source .venv/bin/activate
MODEL_REVISION=ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66 \
  scripts/build_swiftui_app.sh release
scripts/smoke_swiftui_launch.sh --app dist-swiftui/Aside.app
```

This produces an unsigned developer candidate, not a distributable release.
Developer ID signing, DMG packaging, notarization, stapling, and Gatekeeper
validation are fail-closed and documented in
[`docs/release-signing.md`](docs/release-signing.md). The source launcher and
legacy customtkinter bundle remain available for compatibility testing, but
only the native scripts define the release artifact.

## Aside vs. Wispr Flow

| Feature | Aside | Wispr Flow |
|---------|-------|------------|
| Privacy | 100% local | Cloud-based |
| Price | Free (Apache 2.0) | $8-20/mo |
| Voice commands | 12 commands | Yes |
| Custom dictionary | 50 terms | Yes |
| Multi-language | 20 languages | Yes |
| Speed | 1-2s (local) | <1s (cloud) |
| Accuracy | Good (Whisper) | Best (proprietary) |
| Offline | Yes | No |
| Open source | Yes | No |

Wispr Flow is faster and more accurate — if privacy isn't a concern, it's a great product. Aside is for people who want transcription that stays on their machine, full stop.

## Voice Commands

Aside recognizes 12 voice commands for formatting and editing. Say them naturally as part of your dictation — Aside strips them from the output and applies the action inline. Spoken punctuation commands take priority at their location, while Whisper punctuation elsewhere is preserved.

See [docs/voice-commands.md](docs/voice-commands.md) for the full reference.

## Documentation

- [Architecture](docs/architecture.md)
- [Custom dictionary](docs/custom-dictionary.md)
- [Manual smoke test plan](docs/smoke-test-plan.md)
- [SwiftUI release audit and implementation order](docs/swiftui-release-audit-2026-09-08.md)
- [Developer ID signing and notarization](docs/release-signing.md)
- [Historical py2app packaging status](docs/packaging-status.md)
- [Launch conflict resolution](docs/launch-conflict-resolution-2026-04-29.md)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding style, and the PR process.

## License

Apache 2.0. See [LICENSE](LICENSE).
