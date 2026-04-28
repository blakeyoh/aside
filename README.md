# Aside

**Private voice dictation for Mac.**

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/)
[![macOS](https://img.shields.io/badge/macOS-11%2B%20arm64-lightgrey.svg)](https://www.apple.com/macos/)

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

Download the latest `Aside-x.x.x.dmg` from the [Releases page](https://github.com/blakeyoh/aside/releases). Open the DMG, drag Aside to Applications, then double-click to launch.

> **First launch:** macOS may show "Apple could not verify…" because Aside is ad-hoc signed, not notarized. **Right-click Aside.app → Open → Open** to bypass this once. After that it opens normally.

Aside will walk you through granting the three required permissions (Microphone, Accessibility, Input Monitoring) on first launch.

---

## Developer Setup

**Requirements:** macOS 11+ (Apple Silicon), Homebrew. Python 3.13 is installed automatically if missing.

```bash
git clone https://github.com/blakeyoh/aside.git
cd aside
./setup.sh
```

`setup.sh` installs all dependencies, downloads the Whisper `base` model (~140 MB, one-time), and prepares `Aside.app`. This takes a few minutes on first run.

### Grant permissions (required)

Aside needs three permissions in **System Settings → Privacy & Security**. Add whichever terminal app you ran `setup.sh` from (Terminal, iTerm2, Warp, etc.) to each list. If you launch via Finder, add `Aside.app` as well.

| Permission | Why |
|---|---|
| **Microphone** | Capture your voice |
| **Accessibility** | Type text into other apps |
| **Input Monitoring** | Detect hotkey while another app is focused |

macOS will prompt for most of these on first use — click **Allow**.

### Launch

Double-click `Aside.app` in the project folder, or drag it to your Dock first. You can also move it to `/Applications` after running `setup.sh`. Finder/Dock launch opens Settings once so you can confirm Aside started; terminal launch starts hidden and is controlled from the menu bar.

```bash
# Terminal alternative
source .venv/bin/activate && python -m aside
```

A microphone icon appears in your menu bar when Aside is running. It turns amber while recording and blue while transcribing. **Default hotkey:** hold `⌃ ⌥ Space` to record, release to transcribe.

On first launch, Aside downloads the Whisper model (~140 MB for `base`). This is a one-time download — after that, no network access occurs.

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

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions, coding style, and the PR process.

## License

Apache 2.0. See [LICENSE](LICENSE).
