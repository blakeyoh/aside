# Packaging Status Board

## Current Status
- **Phase:** 3
- **In-flight:** Phase 3 complete — DMG packaging script, GH Actions release scaffold, README Download section
- **Branch:** `pyinstaller-and-more`
- **Last updated:** 2026-04-26

## Decisions Log
- 2026-04-26 — Use py2app for v1.1.0 packaging — Native macOS fit for menu-bar Python app; minimizes path refactor surface.
- 2026-04-26 — Codesign ad-hoc only for v1.1.0 — Defers paid Apple enrollment while still unblocking non-technical install path.
- 2026-04-26 — Bundle faster-whisper base model in `.app` — Avoids first-launch download UX and support complexity.
- 2026-04-26 — Target arm64-only — Intel is intentionally unsupported for v1.1.0.
- 2026-04-26 — Use create-dmg for DMG production — Standard drag-to-install UX, Homebrew-installable, CI-friendly.

## Phase Index
| Phase | Issue | Title | Status | Depends on |
|---|---:|---|---|---|
| 0 | draft | Commit packaging plan to repo | done | - |
| 0 | draft | Create status board + handoff protocol | done | - |
| 0 | draft | Update CLAUDE deferred-work pointer | done | - |
| 1 | TBD | Add `resources.py` + refactor `ICON_PATH` | done | - |
| 1 | TBD | Add `setup_py2app.py` + launchable first app bundle | done | previous |
| 1 | TBD | Bundle model + transcriber resource path | done | py2app bootstrap |
| 1 | TBD | Native dylib closure verification and fixups | done | py2app bootstrap |
| 1 | TBD | Add `scripts/build_app.sh` + clean-Mac smoke flow | done | model + dylib closure |
| 2 | TBD | Add permission detection helpers | done | phase 1 complete |
| 2 | TBD | Add onboarding window + polling | done | permissions helper |
| 2 | TBD | First-run gate + config + Permissions menu | done | onboarding window |
| 2 | TBD | Audio mic-denied callback → onboarding focus | done | first-run gate |
| 3 | TBD | Local DMG packaging + README first-launch guidance | done | phase 2 complete |
| 3 | TBD | Release workflow scaffold for signing/notarization | done | DMG packaging |

## Risk Register
| Risk | Impact | Trigger signal | Mitigation | Owner | Status |
|---|---|---|---|---|---|
| Missing native dylibs in py2app bundle | app fails at runtime | import/runtime errors in packaged app | `otool` audit + `dylibbundler` fixups | packaging assignee | open |
| Permission APIs differ across macOS point releases | onboarding misreports status | statuses never turn green despite grants | keep detection helpers isolated; test in clean macOS 14 VM | phase 2 assignee | open |
| Bundle size / release friction | slower downloads, install dropoff | complaints about large artifact | clearly document model-size tradeoff and expected download size | product owner | open |
| Unsigned first launch friction | users blocked by Gatekeeper | user cannot open app from Finder | README includes explicit right-click → Open flow | docs assignee | resolved |

## Per-Issue Handoff Blocks
### Phase 0 — Governance setup
- Last commit SHA touched: _to be filled after commit_
- Done: Added in-repo packaging plan, initialized status board, prepared issue sequence, and added issue drafts in `docs/packaging-issues.md`.
- Next: File GitHub issues from drafts and backfill real issue numbers in the phase index.
- Open questions: GitHub issue filing is pending environment/tooling (no `gh` CLI in this environment).

### Phase 1 — Issue 1 (`resources.py` + `ICON_PATH`)
- Last commit SHA touched: _to be filled after commit_
- Done: Added `src/aside/resources.py` and switched `src/aside/ui/app.py` to `resource_path("aside-logo.png")`.
- Next: Start Issue 2 (`setup_py2app.py` bootstrap + first launchable bundle).
- Open questions: None.

### Phase 1 — Issues 2-5 (packaging bootstrap)
- Last commit SHA touched: _to be filled after commit_
- Done: Added `setup_py2app.py`, copied `Info.plist` to repo root for build input, added `scripts/build_app.sh`, and updated transcriber model loading to prefer bundled resources.
- Next: Start Phase 2 Issue 6 (permission detection helpers).
- Open questions: Native dylib closure still requires validation on a clean macOS machine using built artifact and `otool`.

### Phase 1 — Code review fixes + remaining deliverables
- Last commit SHA touched: _to be filled after commit_
- Done: Fixed `setup_py2app.py` (removed `site_packages`, invalid `arch`, moved model dir to `resources`, added `name="Aside"`); pinned model revision in `build_app.sh`; fixed `Info.plist` `LSMinimumSystemVersion` to `11.0`; updated `transcriber._resolve_model_source` to match new bundle path; added `entitlements.plist`; removed committed `Aside.app/` shell launcher.
- Next: Start Phase 2 Issue 6 (permission detection helpers).
- Open questions: `MODEL_REVISION` in `build_app.sh` is set to `"main"` — replace with a pinned commit SHA before tagging a release (`git ls-remote https://huggingface.co/Systran/faster-whisper-base main`). Native dylib closure still requires validation on a clean macOS machine.

### Phase 2 — Onboarding + permission preflight
- Last commit SHA touched: 83df944
- Done: Added `src/aside/permissions.py` (check_microphone/accessibility/input_monitoring via AVFoundation, AXIsProcessTrusted, IOHIDCheckAccess); added `src/aside/ui/onboarding.py` (CTkToplevel, 1.5 s polling, green/red dots, Open Settings deep-links, Get Started button); added `first_run_complete` to DEFAULT_CONFIG; wired `on_mic_denied` callback into AudioCapture; added Permissions… menu item to MenuBar; added first-run gate and `_show_onboarding` / `_on_mic_denied` / `_on_onboarding_complete` to App; updated `_on_accessibility_error` to use onboarding window; added pyobjc-framework-AVFoundation + IOKit deps.
- Next: Start Phase 3 (DMG packaging + release workflow).
- Open questions: Permission API behaviour across macOS 11–15 not yet validated in VM.

### Phase 3 — DMG distribution + release workflow scaffold
- Last commit SHA touched: _to be filled after commit_
- Done: Added `scripts/package_dmg.sh` (ad-hoc codesign + create-dmg, version read from `__init__.py`); added `.github/workflows/release.yml` (macos-14 runner, full build → sign → package → upload pipeline, notarization fully commented and documented); updated README with Download section, right-click → Open first-launch note, macOS 11+ badge, "Developer Setup" heading.
- Next: Smoke-test the full build on a clean arm64 Mac, bump version to 1.1.0, pin MODEL_REVISION SHA, tag v1.1.0 to trigger the release workflow.
- Open questions: `MODEL_REVISION` in `build_app.sh` still set to `"main"` — must be replaced with a specific commit SHA before tagging. Native dylib closure still requires `otool` validation on a clean macOS machine.

## GitHub Issue Template (copy/paste)
```md
## Phase
<Phase 1 / 2 / 3 / 4>

## Scope
<one paragraph: what changes, what doesn't>

## Out of scope
<bulleted list>

## Files to touch
<bulleted list with file:line where applicable>

## Acceptance criteria
<bulleted, verifiable>

## Risks / fallback
<timebox + fallback path>

## Gotchas
<links to relevant sections of docs/packaging-plan.md>

## Handoff prompt
Use branch `pyinstaller-and-more`.
Read `docs/packaging-plan.md` and `docs/packaging-status.md` first.
Continue issue #<N>; update status board before stopping.
```

## Proposed GitHub Issues (ready to file)
1. **Phase 1:** Add `src/aside/resources.py` and refactor `src/aside/ui/app.py` `ICON_PATH` to `resource_path(...)`
2. **Phase 1:** Add `setup_py2app.py` and produce first launchable `dist/Aside.app`
3. **Phase 1:** Pre-fetch base Whisper model and load bundled model path in transcriber
4. **Phase 1:** Verify/fix native dylib closure for ctranslate2/tokenizers/sounddevice in py2app bundle
5. **Phase 1:** Add `scripts/build_app.sh` for clean build + smoke path
6. **Phase 2:** Add `src/aside/permissions.py` detection helpers (mic/accessibility/input monitoring)
7. **Phase 2:** Add `src/aside/ui/onboarding.py` with status polling and deep-link actions
8. **Phase 2:** Add first-run gate, `first_run_complete` config, and `Permissions…` menu item
9. **Phase 2:** Replace silent mic-denial return in audio path with onboarding callback
10. **Phase 3:** Build local DMG + README right-click instructions + deferred-ready release workflow scaffold

## Agent Prompt Template
```md
Continue Aside packaging work on branch `ai/plan-macos-packaging-mojG0`.
First read `docs/packaging-plan.md` and `docs/packaging-status.md`.
Work issue #<N> only. Keep scope tight to acceptance criteria.
Before stopping, update:
1) Current Status
2) Phase Index row for issue #<N>
3) Handoff block with last commit SHA, done/next/open questions.
```

## Session Close Checklist
- [ ] Current Status updated
- [ ] Phase Index updated
- [ ] Decision log updated (if any new decision)
- [ ] Handoff block updated with commit SHA
- [ ] Open risks updated
