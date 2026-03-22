# Aside

**Private voice dictation for Mac.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-14%2B-lightgrey.svg)](https://www.apple.com/macos/)

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

## Quick Start

### Option 1: Homebrew (coming soon)

```bash
brew tap aside-app/aside
brew install aside
```

### Option 2: Manual install

```bash
# Prerequisites: macOS 14+, Python 3.13+, Homebrew
brew install portaudio

git clone https://github.com/aside-app/aside.git
cd aside
./setup.sh

# Launch
open Aside.app
# or
./run.sh
```

On first launch, Aside downloads the Whisper model (~150MB for `base`, ~290MB for `small`). This is a one-time download; after that, no network access occurs.

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

Aside recognizes 12 voice commands for formatting and editing. Say them naturally as part of your dictation — Aside strips them from the output and applies the action.

See [docs/voice-commands.md](docs/voice-commands.md) for the full reference.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding style, and the PR process.

## License

Apache 2.0. See [LICENSE](LICENSE).
