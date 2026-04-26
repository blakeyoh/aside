# Packaging GitHub Issue Drafts

Use these drafts to create repository issues in order. Issue numbers should then be backfilled into `docs/packaging-status.md`.

## 1) Phase 1 — Add resources helper + refactor ICON_PATH
## Phase
Phase 1

## Scope
Create `src/aside/resources.py` with `resource_path(name)` and switch `src/aside/ui/app.py` icon path logic to use it. Keep source mode behavior equivalent to current repo-root lookup.

## Out of scope
- Whisper model loading changes
- py2app config

## Files to touch
- `src/aside/resources.py`
- `src/aside/ui/app.py`

## Acceptance criteria
- App icon resolves in source mode using `resource_path("aside-logo.png")`
- No hardcoded `Path(__file__).resolve()...` remains for icon path
- Existing tests pass

## Risks / fallback
- Timebox: 2 hours
- Fallback: keep old path logic behind temporary compatibility wrapper

## Gotchas
- `docs/packaging-plan.md` (Phase 1 resource path section)

## Handoff prompt
Use branch `ai/plan-macos-packaging-mojG0`. Read `docs/packaging-plan.md` and `docs/packaging-status.md` first. Continue this issue only and update status board before stopping.

---

## 2) Phase 1 — Add setup_py2app.py + first launchable bundle
## Phase
Phase 1

## Scope
Add `setup_py2app.py` with initial py2app config and produce first launchable `dist/Aside.app`.

## Out of scope
- Native dylib fixups
- model bundling

## Files to touch
- `setup_py2app.py`
- `Info.plist` (if moved/normalized)

## Acceptance criteria
- `python setup_py2app.py py2app` builds `dist/Aside.app`
- app launches to visible menu-bar behavior in local dev test

## Risks / fallback
- Timebox: 4 hours
- Fallback: start with alias mode `-A` until full bundle issues are isolated

## Gotchas
- `docs/packaging-plan.md` Phase 1 py2app section

## Handoff prompt
Use branch `ai/plan-macos-packaging-mojG0`. Read `docs/packaging-plan.md` and `docs/packaging-status.md` first. Continue this issue only and update status board before stopping.

---

## 3) Phase 1 — Pre-fetch base model + bundled transcriber path
## Phase
Phase 1

## Scope
Pre-fetch `Systran/faster-whisper-base` into build inputs and change transcriber to load bundled resource path in packaged mode.

## Out of scope
- Permission UI

## Files to touch
- `src/aside/engine/transcriber.py`
- `scripts/build_app.sh` or equivalent build flow

## Acceptance criteria
- Model path resolves from packaged resources
- No first-launch model download required for packaged app

## Risks / fallback
- Timebox: 4 hours
- Fallback: temporary local-dir override with explicit TODO

## Gotchas
- `docs/packaging-plan.md` model prefetch section

## Handoff prompt
Use branch `ai/plan-macos-packaging-mojG0`. Read `docs/packaging-plan.md` and `docs/packaging-status.md` first. Continue this issue only and update status board before stopping.

---

## 4) Phase 1 — Native dylib closure verification + fixups
## Phase
Phase 1

## Scope
Audit and repair dylib closure for ctranslate2/tokenizers/sounddevice in packaged app.

## Out of scope
- Onboarding UX

## Files to touch
- build/packaging scripts as needed

## Acceptance criteria
- `otool -L` on sensitive extension modules resolves to in-bundle libs
- Packaged app runs transcription without missing dylib errors

## Risks / fallback
- Timebox: 2 days
- Fallback: scripted `dylibbundler` pass with documented known limitations

## Gotchas
- `docs/packaging-plan.md` native dylib pitfall section

## Handoff prompt
Use branch `ai/plan-macos-packaging-mojG0`. Read `docs/packaging-plan.md` and `docs/packaging-status.md` first. Continue this issue only and update status board before stopping.

---

## 5) Phase 1 — scripts/build_app.sh + clean-Mac smoke path
## Phase
Phase 1

## Scope
Create `scripts/build_app.sh` for clean builds, model prefetch orchestration, and smoke-run checks.

## Out of scope
- DMG packaging

## Files to touch
- `scripts/build_app.sh`
- docs/readme snippets if needed

## Acceptance criteria
- Script cleans prior outputs and performs reproducible local build flow
- Basic smoke steps documented and executable

## Risks / fallback
- Timebox: 4 hours
- Fallback: split script into dev/release subcommands

## Gotchas
- `docs/packaging-plan.md` build flow section

## Handoff prompt
Use branch `ai/plan-macos-packaging-mojG0`. Read `docs/packaging-plan.md` and `docs/packaging-status.md` first. Continue this issue only and update status board before stopping.

---

## 6) Phase 2 — Add permission detection helpers
## 7) Phase 2 — Add onboarding window + polling
## 8) Phase 2 — First-run gate + config + Permissions menu
## 9) Phase 2 — Mic-denied callback wiring
## 10) Phase 3 — DMG packaging + README + deferred-ready release workflow

(Use same template from `docs/packaging-status.md` for these five issues.)
