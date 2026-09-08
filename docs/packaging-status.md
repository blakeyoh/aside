# Packaging Status Board

> Historical status for the legacy customtkinter/py2app artifact. It does not
> certify the native app or define the current release path. See
> [the SwiftUI release audit](swiftui-release-audit-2026-09-08.md).

## Current Status
- **Phase:** 3 (launch visibility + smoke-test recovery)
- **In-flight:** `stabilize-launch-icon-install` keeps the `pyinstaller-and-more` packaging/runtime hardening and ports the launch-visibility intent from `fix-dock-icon-and-settings-launch-15421400996173080794` without taking the stale conflict resolution wholesale. First run now shows onboarding; later launches show Settings. Build smoke now verifies the bundled menu-bar icon resource and `LSUIElement=false`.
- **Branch:** `stabilize-launch-icon-install`
- **Last updated:** 2026-04-29

## 2026-04-29 — Launch conflict resolution route

The stable route is to start from `origin/pyinstaller-and-more`, not from the later launch branch, because `pyinstaller-and-more` already contains the clean install work: py2app scaffolding, release/build-smoke workflows, Python/Tk allow-listing, onboarding, AppKit/Quartz runtime fallbacks, and DMG packaging. The launch branch contains the right product decision, visible startup and Dock-enabled app behavior, but its `menubar.py` and `app.py` are older than the packaging branch and would drop the newer onboarding and graceful dependency handling if merged directly.

Applied decision:
- Keep `Info.plist` as a regular Dock-enabled app with `LSUIElement=false`.
- Keep the AppKit availability guard in `menubar.py` so tests and incomplete developer environments do not crash during import. `setup.sh` and `scripts/build_app.sh` still fail fast if AppKit is missing from an install/build environment.
- Replace quiet-launch behavior with a visible startup surface: onboarding until `first_run_complete=true`, then Settings on every launch.
- Add build-smoke checks for `dist/Aside.app/Contents/Resources/aside-logo.png` and `LSUIElement=false` so a future build cannot silently ship without the menu-bar image resource or Dock-enabled bundle mode.
- Raise py2app/modulegraph recursion headroom for full release builds and explicitly exclude unused optional ML stacks that can exist in stale developer venvs.
- Install `create-dmg` in `setup.sh` so local DMG packaging is not a hidden extra prerequisite.

### Verification on 2026-04-29
- `./setup.sh` completed after installing `create-dmg`.
- `scripts/build_app.sh dev` completed and produced `dist/Aside.app`.
- `scripts/build_app.sh release` completed with pinned model revision `ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66`.
- `scripts/package_dmg.sh` completed with escalation for `hdiutil` and produced `dist/Aside-1.1.0.dmg`.
- `codesign --verify --deep --strict --verbose=2 dist/Aside.app` passed.
- Bundle checks: `LSUIElement=false`, version `1.1.0`, `aside-logo.png` present, bundled `faster-whisper-base/model.bin` present, app size 399 MB, DMG size 224 MB.

## Failed Smoke (2026-04-27) — Postmortem
First attempt to install on a clean Apple Silicon machine in developer mode failed at five points. Each is now addressed:

| # | Failure | Root cause | Fix |
|---|---|---|---|
| 1 | `pip install -e .` aborted: `No matching distribution found for pyobjc-framework-IOKit>=10.3` | `pyobjc-framework-IOKit` is **not** a real PyPI package. The dependency was added speculatively for `IOHIDCheckAccess` and never validated against PyPI. | Removed the dep from `pyproject.toml`. `permissions.check_input_monitoring` now links `IOKit.framework` directly via `ctypes` (parallel to the existing `AXIsProcessTrusted` ctypes fallback). |
| 2 | `python3` resolved to anaconda 3.12, not the venv. py2app's `setup_requires` egg got built for 3.12 and exploded under 3.13 (`No module named 'modulegraph'`). | `setup_py2app.py` used the deprecated `setup_requires=["py2app>=0.28"]` `fetch_build_eggs` path. `build_app.sh` did not verify the active Python was the venv. | Removed `setup_requires` from `setup_py2app.py`. `build_app.sh` now refuses to run if `python` does not resolve to `<repo>/.venv/bin/python` and pre-checks that `huggingface_hub` and `py2app` are importable. |
| 3 | `configuration error: project.license must be valid exactly by one definition` | `pyproject.toml` used the SPDX string form `license = "Apache-2.0"`, which requires `setuptools>=77`. Older setuptools rejected it. | Reverted to `license = { text = "Apache-2.0" }` table form, accepted by all setuptools versions in our supported range. |
| 4 | `error: error in setup script: command 'py2app' has no such option 'codesign_entitlements'` | py2app 0.28 (the latest released version) does not support the `codesign_entitlements` option. | Removed the option from `setup_py2app.py`. The entitlements are still applied via `codesign --entitlements entitlements.plist …` in `package_dmg.sh` and the release workflow. |
| 5 | `running py2app … error: install_requires is no longer supported` | setuptools 80+ removed the legacy `install_requires` keyword in `setup()`, which py2app 0.28 internally relies on. | Pinned `setuptools<70` in both `setup.sh` and the release workflow. Also pinned `py2app==0.28.10` (the exact tested version) and pre-installed `huggingface_hub` so users are not asked to do dependency surgery. |

### Process gap that allowed all of this through
There was no "fresh machine" gate before handoff. The previous status entries marked Phase 1 / 2 / 3 as **done** without a clean-VM build ever running end to end.

**Mitigation added:** `.github/workflows/build-smoke.yml` runs on every push and PR. It does `rm -rf .venv ~/.aside; ./setup.sh; pytest; scripts/build_app.sh dev` on a fresh `macos-14` runner, then verifies the produced `.app` bundle and `otool`-audits the brittle native extensions. This is the gate that should have existed since Phase 1.

### 2026-04-27 (b) — build-smoke caught a 6th regression on first run
First green-field run of the new gate failed with `customtkinter (missing)` during the `setup.sh` verification step. Root cause: Homebrew's `python@3.13` formula does **not** ship `_tkinter`; Tk bindings live in the separate `python-tk@3.13` formula. Customtkinter imports `tkinter` at module load, so without it every UI module on a fresh Mac would fail to import — even though local dev machines that had Tk installed for other reasons appeared to work.

**Fix:** install `python-tk@3.13` in `setup.sh`, the build-smoke workflow, and the release workflow. `setup.sh` also performs an `import tkinter` smoke check immediately after venv activation so this fails with a clear actionable message instead of a vague "customtkinter missing" line many steps later.

### 2026-04-27 (c) — pytest gap + proactive guards to break the cascade pattern
Second build-smoke run failed at `python -m pytest tests/`: pytest was not installed in the venv. `setup.sh` only installed runtime deps; the smoke-test plan and the CI both assume pytest is present. Fix: install `pytest>=8` alongside the build toolchain in `setup.sh`.

To stop the discover-fix-cycle pattern from repeating, four proactive guards were added in the same commit:

1. **`scripts/build_app.sh` import preflight** — before invoking py2app, the script imports every package listed in `setup_py2app.py`'s `packages` and `includes`. If any fails, output is one diagnostic block listing every broken module + which Homebrew/pip package supplies it. This converts "py2app exits with a 200-line traceback after 30 seconds" into "build_app.sh exits in 1 second telling you exactly what to install."
2. **`setup_py2app.py` cleanup** — removed the speculative `_sounddevice` from `includes` (CFFI loads it as a dlopen dylib, not a Python module — listing it would have been the next failure under release mode).
3. **`build-smoke.yml` diagnostics** — added `pip list`, bundle layout dump, and `otool` audit steps that all run with `if: always()` so even when the workflow fails, the next debug pass has the data it needs.
4. **Resilient diagnostic step** — the `pip list` diagnostic checks for `.venv/` existence first so a missed venv doesn't cause a meta-failure that hides the real one.

**Known unknowns still in CI's lap (not predictable from a Linux sandbox):**
- Does py2app 0.28.10 + Python 3.13 + setuptools<70 actually complete a `dev` (alias) build to produce `dist/Aside.app`? (The combination is now pinned and should work, but no one has run it yet.)
- Does py2app handle `customtkinter`'s assets folder (theme JSONs, icons) without explicit `iconfile`/`include_files` directives?
- Does the alias bundle's `dist/Aside.app/Contents/MacOS/Aside` exist as expected? py2app's alias mode produces a stub launcher — the verify-bundle step will tell us.

If any of these surface in the next CI run, the diagnostics above should make the fix one-shot rather than a chain.

## Supported Python policy

Aside is currently validated against **exactly one** Python minor version, declared in `setup.sh` as `SUPPORTED_PYTHONS=("3.13")`. The script:
- Refuses to silently use any other version. If only an unsupported Python (e.g. 3.14) is installed, it auto-installs `python@${DEFAULT_PYTHON_VERSION}` via Homebrew rather than picking the unsupported one and failing later.
- Derives the Tk formula (`python-tk@X.Y`) from the chosen interpreter at runtime, so a future bump never produces the silently-mismatched-Tk failure mode the reviewer caught.

**Why an allow-list, not "any 3.X+":** the brittle dependencies in this stack (`faster-whisper`, `ctranslate2`, `tokenizers`, `py2app`) ship pre-built C/C++ wheels per Python minor version. New CPython releases routinely take weeks to months before all upstream wheels exist. Accepting any future Python version means a contributor on a 3.14-only Mac would discover a missing wheel halfway through `pip install -e .` instead of getting one clear "this Python is unsupported" line at the top of `setup.sh`.

**To extend support to a new minor (e.g., 3.14):**
1. Add `"3.14"` BEFORE the existing entries in `setup.sh`'s `SUPPORTED_PYTHONS` array.
2. Update `python@3.13` / `python-tk@3.13` references in `.github/workflows/{build-smoke,release}.yml` to match (or run a parallel job to validate both).
3. Push and let `build-smoke.yml` exercise the full install + py2app build on `macos-14`.
4. Update `README.md` and the relevant smoke-test plan steps.

### 2026-04-27 (e) — Tk formula tied to chosen Python (reviewer fix)
PR review on the recovery branch flagged: `setup.sh` accepted any `python3` with minor ≥ 13 but hard-coded `python-tk@3.13`. On a 3.14-only machine the venv would be created with 3.14 and the `import tkinter` smoke check would then fail because the 3.13 Tk formula doesn't ship a binding for the 3.14 interpreter.

**Fix:**
1. Replaced the loose `MINOR -ge 13` check with an explicit `SUPPORTED_PYTHONS=("3.13")` allow-list and a `find_python()` helper.
2. Tracked the chosen interpreter's `X.Y` in a `PYTHON_MINOR_VERSION` variable and used it to derive `TK_FORMULA="python-tk@${PYTHON_MINOR_VERSION}"`.
3. Made the auto-install branch use the same default version, and made the `import tkinter` failure message cite the derived formula instead of the hard-coded one.
4. Added cross-reference comments to `build-smoke.yml` and `release.yml` reminding maintainers to keep their `python@X.Y` / `python-tk@X.Y` in lockstep with `SUPPORTED_PYTHONS`.

### 2026-04-27 (d) — `install_requires is no longer supported`, root-caused
Third build-smoke run got past the import preflight, downloaded the model, and then died inside py2app with `error: install_requires is no longer supported`. This was the same error the original local smoke run hit, and my first guess (setuptools ≥80 removed `install_requires`) was wrong — the wheel deprecation warning in the new log proves setuptools is < 70.1 in the venv.

**Real root cause** (confirmed by reading py2app 0.28.10 source on GitHub): py2app's `build_app.py` raises `DistutilsOptionError("install_requires is no longer supported")` if **any** `install_requires` attribute exists on the distribution. We do not set it directly. But modern setuptools auto-loads `pyproject.toml` from the cwd and populates `install_requires` from `[project] dependencies`. py2app sees that auto-populated value and aborts.

**Fix:** subclass py2app's command class in `setup_py2app.py`. The override clears `install_requires` (plus `setup_requires` / `tests_require` for safety) on the distribution before calling `super().finalize_options()`. The runtime install is unaffected — `pip install -e .` already happened in `setup.sh`, so the deps are present in the venv. We're only hiding the metadata from py2app's check.

This is a permanent fix for as long as py2app 0.28 is the latest release.

### Still requires human-on-Mac validation
- `scripts/build_app.sh release` (full bundle, not alias) actually produces a launchable `dist/Aside.app` on a clean machine and the build-smoke CI passes.
- The packaged app finds the bundled Whisper model from `Aside.app/Contents/Resources/faster-whisper-base/` (resource path bundling).
- Onboarding window appears on first launch from `/Applications` and the three permission rows turn green after grants.

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
- Next: Smoke-test the full build on a clean arm64 Mac, then tag v1.1.0 to trigger the release workflow.
- Open questions: Native dylib closure still requires `otool` validation on a clean macOS machine.

### Smoke-test preparation
- Last commit SHA touched: _to be filled after commit_
- Done: Bumped version to 1.1.0 in `__init__.py`, `pyproject.toml`, `Info.plist`, smoke-test plan, and CLAUDE.md. Added v1.1.0 entry to CHANGELOG. Fixed onboarding so `first_run_complete` is only persisted when all three permissions are granted (Get Started button is disabled until then; closing the window without grants reopens onboarding next launch). Refactored `build_app.sh` to read `MODEL_REVISION` from the environment with default `"main"`, and to reject release builds whose revision is not a 40-char hex SHA. Added `MODEL_REVISION` env wiring to the release workflow with documentation pointing at GitHub Actions repo variables. Updated PF-4 expected test count from 77 → 97 in the smoke-test plan.
- Next: On a clean arm64 Mac, set the `MODEL_REVISION` Actions variable to the current Hugging Face SHA (`git ls-remote https://huggingface.co/Systran/faster-whisper-base main`), run `scripts/build_app.sh release` + `scripts/package_dmg.sh`, walk a non-technical tester through Phase 1–6 of the smoke-test plan, then tag `v1.1.0`.
- Open questions: None.

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
