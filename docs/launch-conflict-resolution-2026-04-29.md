# Launch Conflict Resolution

## Branches Reviewed

- Base target: `origin/pyinstaller-and-more`
- Source branch: `origin/fix-dock-icon-and-settings-launch-15421400996173080794`
- New integration branch: `stabilize-launch-icon-install`

## Why This Branch Starts From `pyinstaller-and-more`

`pyinstaller-and-more` contains the install work that matters for stability:

- py2app build config and DMG packaging
- release and build-smoke GitHub Actions
- Homebrew Python 3.13 and matching `python-tk@3.13` setup
- first-run permissions onboarding
- menu-bar `Permissions...` item
- AppKit/Quartz/faster-whisper fallback paths for tests and incomplete developer environments

The launch branch contains the right behavioral intent, but its conflict-resolution commit is based on older `app.py` and `menubar.py` shapes. Taking it wholesale would risk dropping onboarding and runtime guards that were added later.

## Decisions Applied

1. **Visible launch is the default.**
   First run opens onboarding. Once permissions are complete, later launches open Settings automatically. This keeps the app visibly alive without skipping the permissions gate.

2. **Dock-enabled app mode stays.**
   `Info.plist` keeps `LSUIElement=false`, matching a regular app with a Dock indicator. Aside still creates a menu-bar status item for daily control.

3. **AppKit guard stays.**
   The launch branch removed the `try/except` wrapper around AppKit imports. This branch keeps the guard because the test suite and non-GUI import paths should not crash. Install/build correctness is enforced in `setup.sh`, `scripts/build_app.sh`, and CI import preflights instead.

4. **Menu-bar icon bundling is now gated.**
   Build smoke verifies `dist/Aside.app/Contents/Resources/aside-logo.png`, and `scripts/build_app.sh` fails early if `aside-logo.png`, `AppIcon.icns`, `Info.plist`, or `entitlements-helper.plist` are missing.

## Conflicts Avoided

Directly merging the launch branch conflicts in:

- `src/aside/ui/app.py`
- `src/aside/ui/menubar.py`
- `Info.plist` path history
- `CHANGELOG.md`
- `docs/smoke-test-plan.md`

This branch bypasses those conflicts by preserving the newer packaging branch files and applying only the current launch behavior and documentation intent.

## Verification Targets

- `.venv/bin/python3 -m pytest tests/ -v`
- `bash -n setup.sh scripts/build_app.sh scripts/package_dmg.sh generate-icon.sh run.sh`
- `source .venv/bin/activate && scripts/build_app.sh dev`
- Manual smoke path in `docs/smoke-test-plan.md`
