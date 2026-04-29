# Contributing to Aside

Thank you for your interest in contributing. This guide covers everything you need to get a dev environment running and submit a pull request.

## Prerequisites

- macOS 11 or later on Apple Silicon
- Homebrew

## Dev Setup

```bash
# 1. Clone the repo
git clone https://github.com/blakeyoh/aside.git
cd aside

# 2. Run setup (installs Homebrew deps, creates .venv, installs Python deps)
./setup.sh

# 3. Activate the virtual environment
source .venv/bin/activate

# 4. Launch in dev mode
python -m aside

# 5. Optional: build a local app bundle
scripts/build_app.sh dev
```

`setup.sh` currently supports Homebrew Python 3.13 and installs the matching `python-tk@3.13` formula so `customtkinter` can import cleanly. If setup chooses or installs a different Python minor in the future, keep the Tk formula in lockstep.

## Running Tests

```bash
.venv/bin/python3 -m pytest tests/ -v
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
3. Ensure `.venv/bin/python3 -m pytest tests/ -v` passes
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
