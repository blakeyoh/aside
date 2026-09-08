# Aside — One-Double-Click Install for Non-Technical Users

> Historical plan for the legacy customtkinter/py2app artifact. It is retained
> as compatibility history, not current release authority. Follow
> [the SwiftUI release audit](swiftui-release-audit-2026-09-08.md) and the native
> `build_swiftui_app.sh` / `package_swiftui_dmg.sh` path for 1.3.0 and later.

## Context
Today, installing Aside requires opening Terminal, running `./setup.sh`, waiting for Homebrew to install Python 3.13, then double-clicking Aside.app (a thin shell launcher that sources a `.venv` from `~/.aside/install_path.txt`). A non-technical user is locked out at step 1.

The research conclusion is to use **py2app** for v1.1.0 packaging because it is macOS-native and suitable for menu-bar Python apps; SwiftUI is deferred to v2+.

## Locked decisions
- Codesigning: ad-hoc only for v1.1.0. README documents right-click → Open for first launch.
- Whisper model: bundle the base model inside the `.app` (~400 MB total). No first-launch download UI.
- Architecture: arm64-only. Intel Macs are explicitly unsupported.

## Phase 0 — Project management infrastructure
### 0.1 Commit the plan
- Keep this file (`docs/packaging-plan.md`) as the canonical in-repo plan reference for all future sessions.

### 0.2 Create `docs/packaging-status.md`
Single source of truth for:
- Current status (phase / issue in flight)
- Decisions log
- Phase index with issue links
- Per-issue handoff blocks
- Agent prompt template
- Risk register and session-close checklist

### 0.3 File GitHub issues (one per logical unit)
Each issue body should use this template:

```md
## Phase
<Phase 1 / 2 / 3 / 4>

## Scope
<one paragraph: what changes, what doesn't>

## Files to touch
<bulleted list with file:line where applicable>

## Acceptance criteria
<bulleted, verifiable>

## Gotchas
<links to relevant sections of docs/packaging-plan.md>

## Handoff prompt
<paste-ready prompt for the next agent — see docs/packaging-status.md template>
```

Planned issue breakdown:
1. Add `src/aside/resources.py` + refactor `ICON_PATH`
2. `setup_py2app.py` bootstrap + first green build
3. Pre-fetch Whisper model + load bundled model path in transcriber
4. `scripts/build_app.sh` + clean-Mac smoke build
5. `src/aside/permissions.py` detection helpers
6. `src/aside/ui/onboarding.py` permission window + polling
7. First-run gate + `first_run_complete` config + `Permissions…` menu item
8. Fix silent mic-denial in `audio.py` with onboarding callback
9. Local `.dmg` via `create-dmg` + README first-launch instructions
10. GH Actions release workflow scaffold for signing/notarization (deferred-ready)

Phase 4 (Check for Updates) is deferred and will be filed later.

### 0.4 Update `CLAUDE.md` deferred-work pointer
Replace moving packaging bullets with a pointer to:
- `docs/packaging-plan.md`
- `docs/packaging-status.md`

## Phase 1 — Self-contained `.app` via py2app
### Files to create
- `setup_py2app.py`
- `scripts/build_app.sh`
- `src/aside/resources.py`
- `entitlements.plist`

### Files to modify
- `src/aside/ui/app.py` (`ICON_PATH` via `resource_path(...)`)
- `src/aside/engine/transcriber.py` (bundled model path)
- Remove committed `Aside.app/` launcher from repo
- Keep `setup.sh` for contributors; README points end users to `.dmg`

### `resource_path` helper
```py
import sys
from pathlib import Path

def resource_path(name: str) -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent.parent / "Resources" / name
    return Path(__file__).resolve().parent.parent.parent / name
```

### Known risk: native dylib closure
Validate with:
```bash
otool -L dist/Aside.app/Contents/Resources/lib/python3.13/ctranslate2/_ext*.so
```
If missing, patch bundle with `dylibbundler` and repeat for ctranslate2 / sounddevice / tokenizers.

## Phase 2 — Onboarding + permission preflight
### Files to create
- `src/aside/permissions.py`
- `src/aside/ui/onboarding.py`

### Files to modify
- `src/aside/config.py` (add `first_run_complete`)
- `src/aside/ui/app.py` (first-run gate)
- `src/aside/engine/audio.py` (mic-denied callback)
- `src/aside/ui/menubar.py` (`Permissions…` item)
- `pyproject.toml` (AVFoundation + IOKit pyobjc deps)

### UX behavior
- First launch blocks into onboarding until all required permissions are granted.
- Permissions window can be reopened from menu.
- Status rows poll while window is visible.

## Phase 3 — Distribution (deferred until Apple enrollment)
- Build local `.dmg` and publish as release asset.
- README includes right-click → Open first-launch instructions.
- After enrollment, implement signing + notarization in GH Actions.

## Phase 4 — Auto-update (deferred)
- Add menu item to check latest GitHub release and open release page if newer version exists.

## Verification gates
### Phase 1 gate
- Fresh macOS tester installs without Terminal.
- App launches from Applications and appears in menu bar.
- Dictation works end-to-end.

### Phase 2 gate
- Onboarding appears before normal app flow.
- Mic prompt appears and reflects status quickly.
- Accessibility/Input Monitoring deep links work.
- Tester reaches working dictation without reading docs.

### Phase 3 gate
- Tag build produces signed/notarized installer.
- No unverified developer friction.
