# Packaging Status Board

## Current Status
- **Phase:** 1
- **In-flight:** Issue 1 complete — added resource helper + icon path refactor
- **Branch:** `ai/plan-macos-packaging-mojG0`
- **Last updated:** 2026-04-26

## Decisions Log
- 2026-04-26 — Use py2app for v1.1.0 packaging — Native macOS fit for menu-bar Python app; minimizes path refactor surface.
- 2026-04-26 — Codesign ad-hoc only for v1.1.0 — Defers paid Apple enrollment while still unblocking non-technical install path.
- 2026-04-26 — Bundle faster-whisper base model in `.app` — Avoids first-launch download UX and support complexity.
- 2026-04-26 — Target arm64-only — Intel is intentionally unsupported for v1.1.0.

## Phase Index
| Phase | Issue | Title | Status | Depends on |
|---|---:|---|---|---|
| 0 | draft | Commit packaging plan to repo | done | - |
| 0 | draft | Create status board + handoff protocol | done | - |
| 0 | draft | Update CLAUDE deferred-work pointer | done | - |
| 1 | TBD | Add `resources.py` + refactor `ICON_PATH` | done | - |
| 1 | TBD | Add `setup_py2app.py` + launchable first app bundle | todo | previous |
| 1 | TBD | Bundle model + transcriber resource path | todo | py2app bootstrap |
| 1 | TBD | Native dylib closure verification and fixups | todo | py2app bootstrap |
| 1 | TBD | Add `scripts/build_app.sh` + clean-Mac smoke flow | todo | model + dylib closure |
| 2 | TBD | Add permission detection helpers | todo | phase 1 complete |
| 2 | TBD | Add onboarding window + polling | todo | permissions helper |
| 2 | TBD | First-run gate + config + Permissions menu | todo | onboarding window |
| 2 | TBD | Audio mic-denied callback → onboarding focus | todo | first-run gate |
| 3 | TBD | Local DMG packaging + README first-launch guidance | todo | phase 2 complete |
| 3 | TBD | Release workflow scaffold for signing/notarization | todo | DMG packaging |

## Risk Register
| Risk | Impact | Trigger signal | Mitigation | Owner | Status |
|---|---|---|---|---|---|
| Missing native dylibs in py2app bundle | app fails at runtime | import/runtime errors in packaged app | `otool` audit + `dylibbundler` fixups | packaging assignee | open |
| Permission APIs differ across macOS point releases | onboarding misreports status | statuses never turn green despite grants | keep detection helpers isolated; test in clean macOS 14 VM | phase 2 assignee | open |
| Bundle size / release friction | slower downloads, install dropoff | complaints about large artifact | clearly document model-size tradeoff and expected download size | product owner | open |
| Unsigned first launch friction | users blocked by Gatekeeper | user cannot open app from Finder | README includes explicit right-click → Open flow | docs assignee | open |

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
Use branch `ai/plan-macos-packaging-mojG0`.
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
