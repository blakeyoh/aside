# Aside Privacy Policy

**TL;DR: Your audio never leaves your Mac. Period.**

## How Aside Works

Aside runs a local speech-to-text model (Whisper) entirely on your machine. There are no cloud APIs, no telemetry, no data collection of any kind.

## Trust Questions

### Does audio leave my machine?
No. Audio is captured into a RAM buffer, processed by the local Whisper model, and discarded immediately after transcription. It is never written to disk.

### Is anything sent to the cloud?
No. Aside makes zero network calls during normal operation. It is fully air-gappable — disconnect from the internet and it works identically.

### Does it collect telemetry?
No. No analytics, no crash reporting, no usage tracking, no phone-home behavior.

### Where is my data stored?
- Config: `~/.aside/config.json` (your preferences)
- Dictionary: `~/.aside/dictionary.txt` (your custom terms)
- That's it. No audio files, no transcription logs, no history.

### Can I verify this?
Yes. Run this in the project directory:
```bash
grep -r "urllib\|requests\|httpx\|aiohttp\|socket" src/aside/
```
It returns nothing. There is no networking code in the application.

### What about model downloads?
The `faster-whisper` library downloads Whisper models from Hugging Face on first run. After that initial download, Aside never contacts the network again. Models are cached locally at `~/.cache/huggingface/`.

## Data Flow

```
Microphone → RAM buffer → Whisper (local) → Text → Cursor
                ↑                               ↑
           Never saved                    Never transmitted
```

## Open Source Guarantee

Aside is open source under the Apache 2.0 license. Every line of code is auditable. If you find any privacy concern, please open an issue.
