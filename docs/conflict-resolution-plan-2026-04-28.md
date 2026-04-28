# Conflict-resolution plan: launch behavior (April 28, 2026)

## Context
Two commits landed close together and changed launch behavior in overlapping ways:

1. `56efde4` — **fix: enable dock icon and show settings on launch**
2. `bf4253c` — **fix: update docs and changelog for launch behavior and revert unnecessary try/except imports**

The current branch intent is to **defer silent/quiet startup** and keep startup explicit so functionality can be validated first.

## What each commit changed

### Commit `56efde4` (behavior + packaging)
- `src/aside/ui/app.py`
  - Removed env-guarded launch behavior and always calls `self.after(300, self._show_settings)`.
- `src/aside/ui/menubar.py`
  - Activation policy changed from accessory to regular app policy.
- `Aside.app/Contents/Info.plist`
  - `LSUIElement` changed from `true` (agent/no Dock icon) to `false` (regular Dock app).

### Commit `bf4253c` (docs alignment)
- `CHANGELOG.md`
  - Quiet-launch marked as deferred and launch-on-start clarified.
- `docs/smoke-test-plan.md`
  - Gate was updated to expect launch visibility.

## Dueling issues to resolve

1. **Documentation contradiction in terminal launch test**
   - In `docs/smoke-test-plan.md` T1.2, one line still says "NO window appears" while the gate says the opposite.
2. **Launch-mode expectation mismatch**
   - T1.3a still expects "no Dock running dot" and "menu-bar agent app," but app packaging/code now indicate regular app behavior.
3. **Potential future merge conflict area**
   - Any branch that reintroduces env-gated startup (`ASIDE_SHOW_SETTINGS_ON_LAUNCH`) will conflict directly with current unconditional show-on-launch behavior.

## Recommended merge strategy

### Phase 1 (now): stabilize launch for functional validation
1. Keep behavior from `56efde4` (regular app + settings shown on launch).
2. Treat any silent-startup changes as out of scope for this branch.
3. Update smoke-test expectations to be fully consistent with non-silent startup.

### Phase 2 (after functionality is validated): reintroduce quiet-startup behind a flag
1. Add a dedicated config/feature flag for startup mode (default to visible launch until confidence is high).
2. Keep docs/test matrix dual-path (visible launch default, quiet launch experimental).
3. Only flip default after passing smoke + regression suite.

## Concrete conflict-resolution checklist

1. **Code decisions (preserve in this branch):**
   - Keep `app.py` unconditional `self._show_settings` on launch.
   - Keep regular activation policy in `menubar.py`.
   - Keep `LSUIElement=false` in app bundle plist.
2. **Docs fixes (required before merge):**
   - T1.2 expected result must explicitly say window appears on launch.
   - T1.3a must match Dock-enabled behavior (remove "agent app/no Dock dot" expectation).
3. **Verification gates:**
   - `.venv/bin/python3 -m aside` shows settings window automatically.
   - Menu bar icon exists while app is running.
   - Finder/Dock launch path behaves the same as terminal launch.
   - Closing window withdraws (does not quit) unless Quit is selected.
4. **Future-safe note for next PR:**
   - Any quiet-startup work must be submitted separately with a feature flag and explicit rollback path.

## Suggested PR sequencing

1. **PR A (this branch):** conflict cleanup + docs consistency for visible startup.
2. **PR B (later):** quiet-startup feature-flag implementation and dedicated test cases.

This sequencing avoids reintroducing ambiguous startup behavior while core dictation functionality is still being validated.
