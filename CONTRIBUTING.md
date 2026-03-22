# Contributing to Aside

Thank you for your interest in contributing. This guide covers everything you need to get a dev environment running and submit a pull request.

## Prerequisites

- macOS 14 or later
- Python 3.13+
- Homebrew

## Dev Setup

```bash
# 1. Clone the repo
git clone https://github.com/aside-app/aside.git
cd aside

# 2. Install system dependency
brew install portaudio

# 3. Run setup (creates venv, installs deps)
./setup.sh

# 4. Activate the virtual environment
source venv/bin/activate

# 5. Launch in dev mode
python app.py
```

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests cover the transcription engine, voice command parser, custom dictionary loader, and hotkey manager. All tests run offline — no audio hardware required (audio capture is mocked).

## Code Style

- **Python 3.13** with type hints throughout
- **Immutable patterns** — create new objects, never mutate in place
- **Small functions** — aim for under 50 lines per function
- **Explicit error handling** — use `try/except` with specific exception types; avoid bare `except`
- **No hardcoded values** — config belongs in `~/.aside/config.json` or module-level constants

Run the formatter before committing:

```bash
black src/ tests/
```

## Pull Request Process

1. Fork the repository and create a branch from `main`
2. Make your changes with tests
3. Ensure `python -m pytest tests/ -v` passes
4. Open a pull request with a clear description of what changed and why
5. Link any related issues

For significant changes (new features, architectural changes), open an issue first to discuss the approach before writing code.

## Reporting Bugs

Open a GitHub issue with:
- macOS version
- Python version (`python3 --version`)
- Steps to reproduce
- What you expected vs. what happened
- Relevant lines from `~/Library/Logs/Aside/aside.log`
