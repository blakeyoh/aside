# Aside v1 — Manual Smoke Test Plan

## Philosophy

This plan borrows from Boeing's First Article Inspection (FAI) methodology. The first unit off the line gets exhaustive testing against every specification requirement — not spot checks, not "it seems to work." Each test has:

- **Known baseline state** (configuration management)
- **Explicit expected result** (zero ambiguity)
- **Go/No-Go gate** (don't proceed past a failed checkpoint)
- **Non-conformance documentation** (log what broke, not just that it broke)

The mentality: assume nothing works until proven otherwise. A unit test proving `parse_commands()` handles "period" correctly does NOT prove the user can say "period" and see a `.` appear in their document. Integration gaps live in the seams.

---

## Pre-Flight Checklist

Before running any test, establish the known baseline.

- [ ] **PF-1: Clean config state**
  - Back up existing config: `cp -r ~/.aside ~/.aside.bak` (if exists)
  - Remove Aside config: `rm -rf ~/.aside`
  - Verify removed: `ls ~/.aside` → "No such file or directory"
  - *Why:* Tests must verify first-run behavior. Stale config masks migration bugs.

- [ ] **PF-2: Verify Python version**
  - Run: `.venv/bin/python3 --version`
  - Expected: `Python 3.13.x`
  - **GATE:** If < 3.13, stop. Fix Python installation before proceeding.

- [ ] **PF-3: Verify package installation**
  - Run: `.venv/bin/python3 -c "import aside; print(aside.__version__)"`
  - Expected: `1.1.0`
  - **GATE:** If import fails, run `pip install -e .` and retry.

- [ ] **PF-4: Verify unit tests**
  - Run: `.venv/bin/python3 -m pytest tests/ -v`
  - Expected: `118 passed`
  - **GATE:** If any fail, fix before proceeding. Do not smoke test a broken build.

- [ ] **PF-5: Verify macOS permissions**
  - System Settings > Privacy & Security > Accessibility → Terminal (or iTerm) enabled
  - System Settings > Privacy & Security > Input Monitoring → Terminal enabled
  - System Settings > Privacy & Security > Microphone → Terminal enabled
  - *Why:* Missing permissions cause silent failures that look like code bugs.

- [ ] **PF-6: Prepare test surface**
  - Open TextEdit (or any text editor) and create a new blank document
  - Position it so you can see both the text editor and the menu bar
  - *Why:* Text injection targets the active cursor. Need a visible target.

---

## Phase 1: Launch & Lifecycle

These tests verify the app starts, stops, and manages its window correctly. No dictation yet — just the shell.

### T1.1: First Launch (setup.sh)

- [ ] Run: `./setup.sh`
- [ ] Expected: venv created, deps installed, `create-dmg` installed, base model downloaded
- [ ] Watch for: any pip errors, model download failures, permission prompts
- [ ] **Result:** ________________________________________
- [ ] **Non-conformance notes:** ________________________

### T1.2: Terminal Launch

- [ ] Run: `.venv/bin/python3 -m aside`
- [ ] Expected: Permissions onboarding appears because PF-1 removed `~/.aside`. Menu bar shows Aside microphone icon.
- [ ] Verify: menu bar icon is visible in top-right area
- [ ] **GATE:** If neither onboarding nor Settings appears, launch visibility is broken.
- [ ] **Result:** ________________________________________

### T1.3: First-Launch Onboarding (Permissions Gate)

- [ ] Ensure clean state: `rm -rf ~/.aside` and revoke Microphone, Accessibility, and Input Monitoring for Terminal in System Settings
- [ ] Launch: `.venv/bin/python3 -m aside`
- [ ] Expected: Welcome / Permissions window appears with three rows (Microphone, Accessibility, Input Monitoring), all dots red
- [ ] Expected: "Get Started" button is **disabled** while any permission is still red
- [ ] Click "Open Settings" on each row → System Settings deep-links into the matching Privacy pane
- [ ] Grant Microphone → row dot turns green within ~1.5 s
- [ ] Grant Input Monitoring → row dot turns green
- [ ] Grant Accessibility → row dot turns green; restart Aside if macOS requires it
- [ ] After all three are green, "Get Started" becomes enabled and turns green
- [ ] Click "Get Started" → onboarding closes and Settings opens
- [ ] Verify: `cat ~/.aside/config.json | grep first_run_complete` shows `true`
- [ ] If Accessibility or Input Monitoring still shows red even though System Settings shows Aside enabled, remove the old Aside entry from that privacy pane, add the rebuilt `dist/Aside.app` again, then quit and relaunch Aside. Local dev bundles are ad-hoc signed, so stale TCC entries can look enabled while the rebuilt app still reads denied.
- [ ] **Result:** ________________________________________

### T1.4: Settings Window

- [ ] Click menu bar icon → click "Settings..."
- [ ] Expected: Settings window appears, centered on screen
- [ ] Verify: Model dropdown shows "base", Language shows "Auto-detect"
- [ ] Verify: Hotkey shows "Ctrl + Alt + Space"
- [ ] Verify: Dictionary section shows "0 / 50 terms"
- [ ] **Result:** ________________________________________

### T1.5: Subsequent Terminal Launch

- [ ] Quit Aside from the menu bar
- [ ] Run: `.venv/bin/python3 -m aside`
- [ ] Expected: Settings opens automatically and menu bar shows Aside microphone icon
- [ ] **Result:** ________________________________________

### T1.6: Developer App Build and Finder/Dock Launch

- [ ] Quit Aside from the menu bar
- [ ] Run: `source .venv/bin/activate && scripts/build_app.sh dev`
- [ ] Verify: `dist/Aside.app/Contents/Resources/aside-logo.png` exists
- [ ] Verify: `/usr/libexec/PlistBuddy -c "Print :LSUIElement" dist/Aside.app/Contents/Info.plist` prints `false`
- [ ] Double-click `dist/Aside.app`
- [ ] Expected: Settings window appears automatically and menu bar shows Aside microphone icon
- [ ] Expected: Aside appears as a regular app (Dock icon/running indicator may be visible)
- [ ] **Result:** ________________________________________

### T1.7: Release DMG Build

- [ ] Set `MODEL_REVISION` to a pinned 40-character SHA from `git ls-remote https://huggingface.co/Systran/faster-whisper-base main`
- [ ] Run: `MODEL_REVISION=<sha> scripts/build_app.sh release`
- [ ] Run: `scripts/package_dmg.sh`
- [ ] Expected: `dist/Aside-1.1.0.dmg` exists and contains `Aside.app`
- [ ] Install from the DMG into `/Applications`
- [ ] Double-click `/Applications/Aside.app`
- [ ] Expected: Settings window appears automatically and menu bar shows Aside microphone icon
- [ ] Expected: Aside appears as a regular app (Dock icon/running indicator may be visible)
- [ ] **Result:** ________________________________________

### T1.8: Onboarding Dismissal Without Grants Re-prompts

- [ ] Reset state: `rm -rf ~/.aside` and revoke all three permissions
- [ ] Launch Aside
- [ ] Click the window's red "X" close button without granting anything
- [ ] Expected: window closes; `~/.aside/config.json` either does not exist or has `first_run_complete: false`
- [ ] Quit and relaunch Aside
- [ ] Expected: onboarding window reappears (does NOT silently skip into a broken state)
- [ ] **CRITICAL:** This protects users from leaving onboarding without working hotkeys/recording.
- [ ] **Result:** ________________________________________

### T1.9: Permissions Menu Item Re-Opens Onboarding

- [ ] After completing T1.3, click the menu bar icon → "Permissions…"
- [ ] Expected: Permissions window reappears with current statuses
- [ ] **Result:** ________________________________________

### T1.10: Window Hide (not Quit)

- [ ] Click the X (close) button on the Settings window
- [ ] Expected: Window disappears. App continues running (menu bar icon still visible).
- [ ] Verify: Click "Settings..." again → window reappears
- [ ] **CRITICAL:** If the app quits on close, the lifecycle is broken.
- [ ] **Result:** ________________________________________

### T1.11: Quit

- [ ] Click menu bar icon → "Quit Aside"
- [ ] Expected: App terminates cleanly. Menu bar icon disappears.
- [ ] Verify: no orphan processes: `ps aux | grep aside`
- [ ] **Result:** ________________________________________

### T1.12: Single Instance Guard

- [ ] Launch Aside: `.venv/bin/python3 -m aside`
- [ ] In a second terminal, launch again: `.venv/bin/python3 -m aside`
- [ ] Expected: Second instance shows alert dialog, then exits
- [ ] **Result:** ________________________________________

### T1.13: Config Migration (if applicable)

- [ ] If `~/Library/Application Support/HushedHippo/config.json` exists:
  - Remove `~/.aside` directory
  - Launch Aside
  - Expected: `~/.aside/config.json` created with migrated settings
  - Verify: hotkey and model_size match the old HushedHippo config
- [ ] **Result:** ________________________________________

**PHASE 1 GATE:** All T1.x tests pass → proceed to Phase 2. Any failure → stop and document.

---

## Phase 2: Core Dictation Pipeline

The critical path. If this doesn't work, nothing else matters.

### T2.1: Push-to-Talk (Happy Path)

- [ ] Click into TextEdit (ensure cursor is active)
- [ ] Hold Ctrl+Alt+Space
- [ ] Expected: Menu bar icon changes (recording indicator)
- [ ] Speak clearly: "Hello world"
- [ ] Release Ctrl+Alt+Space
- [ ] Expected: "Hello world" (or close) appears at cursor in TextEdit
- [ ] Timing: text should appear within 2-3 seconds of release
- [ ] **CRITICAL:** This is the primary use case. If this fails, everything else is academic.
- [ ] **Result:** ________________________________________

### T2.2: Push-to-Talk (Silence)

- [ ] Hold hotkey for 3 seconds without speaking
- [ ] Release
- [ ] Expected: No text injected. No crash. App returns to ready state.
- [ ] **Result:** ________________________________________

### T2.3: Push-to-Talk (Rapid Fire)

- [ ] Dictate 5 short phrases in quick succession (hold-speak-release, repeat)
- [ ] Expected: Each phrase appears correctly. No overlapping, no dropped dictations.
- [ ] Watch for: text from one dictation bleeding into the next
- [ ] **Result:** ________________________________________

### T2.4: Toggle Mode

- [ ] Open Settings → set a Toggle Hotkey (e.g., Cmd+Shift+D)
- [ ] Click Apply
- [ ] Press the toggle hotkey once
- [ ] Expected: Recording starts (menu bar indicator changes)
- [ ] Speak: "This is toggle mode testing"
- [ ] Press the toggle hotkey again
- [ ] Expected: Recording stops. Text appears at cursor.
- [ ] **Result:** ________________________________________

### T2.5: Long Dictation (Toggle Mode)

- [ ] Activate toggle mode
- [ ] Speak continuously for 15-20 seconds
- [ ] Deactivate toggle mode
- [ ] Expected: Full transcription appears. No truncation.
- [ ] **Result:** ________________________________________

**PHASE 2 GATE:** T2.1 must pass. T2.2-T2.5 should pass. If T2.1 fails, stop entirely — debug before continuing.

---

## Phase 3: Voice Commands

Test each of the 12 voice commands. For each: dictate a phrase that includes the command, verify the command executes.

### T3.1: Punctuation Commands

- [ ] Say: "Hello period"
  - Expected: `Hello.` (period injected, command phrase removed)
- [ ] Say: "How are you question mark"
  - Expected: `How are you?`
- [ ] Say: "Wow exclamation point"
  - Expected: `Wow!`
- [ ] Say: "First comma second"
  - Expected: `First, second`
- [ ] **Result:** ________________________________________

### T3.2: Line Commands

- [ ] Say: "First line new line second line"
  - Expected: text on two lines
- [ ] Say: "First paragraph new paragraph second paragraph"
  - Expected: text separated by a blank line
- [ ] **Result:** ________________________________________

### T3.3: Delete That

- [ ] Dictate: "Some unwanted text"
- [ ] Verify text appears
- [ ] Dictate: "Delete that"
- [ ] Expected: "Some unwanted text" is removed (backspaced)
- [ ] **Known limitation:** If you manually edit between dictations, delete count may be imprecise
- [ ] **Result:** ________________________________________

### T3.4: Undo

- [ ] Dictate: "Test undo functionality"
- [ ] Dictate: "Undo"
- [ ] Expected: Cmd+Z fires, undoing the last action
- [ ] **Result:** ________________________________________

### T3.5: Select All + Copy

- [ ] Dictate a few phrases into TextEdit
- [ ] Dictate: "Select all"
- [ ] Expected: All text selected (highlighted)
- [ ] Dictate: "Copy that"
- [ ] Expected: Cmd+C fires (text on clipboard — verify by pasting elsewhere)
- [ ] **Result:** ________________________________________

### T3.6: Number Mode

- [ ] Dictate: "Numbers mode"
- [ ] Dictate: "One two three four five"
- [ ] Expected: `12345` (digits concatenated, no spaces)
- [ ] Dictate: "Words mode"
- [ ] Dictate: "Back to normal"
- [ ] Expected: "Back to normal" (regular text, not digits)
- [ ] **Result:** ________________________________________

### T3.7: Embedded Command (Negative Test)

- [ ] Dictate: "I'll delete that section from the document"
- [ ] Expected: Full phrase appears as text. "delete that" does NOT trigger because it's mid-sentence.
- [ ] **Why this matters:** False triggers would make the app unusable. The boundary detection must work.
- [ ] **Result:** ________________________________________

**PHASE 3 GATE:** T3.1-T3.6 should pass. T3.7 is critical for usability.

---

## Phase 4: Custom Dictionary

### T4.1: Add Hotword via UI

- [ ] Open Settings
- [ ] In "Add Hotword" field, type: `HIPAA`
- [ ] Click "Add"
- [ ] Expected: Term count updates to "1 / 50 terms"
- [ ] Verify: `cat ~/.aside/dictionary.txt` shows `HIPAA`
- [ ] **Result:** ________________________________________

### T4.2: Add Replacement via UI

- [ ] In "Add Replacement" fields, type: `hip a` → `HIPAA`
- [ ] Click "Add"
- [ ] Expected: Term count updates to "2 / 50 terms"
- [ ] Verify: `cat ~/.aside/dictionary.txt` shows `hip a → HIPAA`
- [ ] **Result:** ________________________________________

### T4.3: Hotword Effect on Transcription

- [ ] With "HIPAA" as a hotword, dictate a sentence mentioning HIPAA
- [ ] Expected: Whisper is more likely to produce "HIPAA" (correct capitalization)
- [ ] *Note: This is probabilistic. Run 3-5 times if first attempt is ambiguous.*
- [ ] **Result:** ________________________________________

### T4.4: Replacement Effect on Transcription

- [ ] If Whisper produces "hip a" for HIPAA, the replacement should correct it
- [ ] **Result:** ________________________________________

### T4.5: Edit Dictionary Externally

- [ ] Click "Edit Dictionary" button
- [ ] Expected: `~/.aside/dictionary.txt` opens in default text editor
- [ ] Add a new term manually, save the file
- [ ] Click "Reload" in Settings
- [ ] Expected: Term count updates to reflect the new term
- [ ] **Result:** ________________________________________

### T4.6: 50-Term Cap

- [ ] Add 50 terms to dictionary (manual file edit is fastest)
- [ ] Click Reload
- [ ] Expected: "50 / 50 terms" shown
- [ ] Try adding another via UI
- [ ] Expected: Add button disabled or shows "Dictionary full"
- [ ] **Result:** ________________________________________

---

## Phase 5: Settings & Preferences

### T5.1: Change Model

- [ ] Open Settings → change Model dropdown to "tiny"
- [ ] Click Apply
- [ ] Expected: "Loading model..." status, then "Ready"
- [ ] Dictate something → verify it works (quality may be lower with tiny)
- [ ] **Result:** ________________________________________

### T5.2: Change Language

- [ ] Set Language to a language you can speak (e.g., Spanish)
- [ ] Click Apply
- [ ] Dictate in that language
- [ ] Expected: Transcription in the selected language
- [ ] Set back to "Auto-detect"
- [ ] **Result:** ________________________________________

### T5.3: Change Hotkey

- [ ] Open Settings → click "Change" next to Hotkey
- [ ] Press a new key combination (e.g., Cmd+Shift+Space)
- [ ] Expected: Hotkey label updates
- [ ] Click Apply
- [ ] Test: old hotkey should NOT trigger dictation
- [ ] Test: new hotkey SHOULD trigger dictation
- [ ] **Result:** ________________________________________

### T5.4: Punctuation Preferences

- [ ] Set Capitalization to "off" → Apply → dictate "hello world"
  - Expected: all lowercase
- [ ] Set Capitalization to "as-spoken" → Apply → dictate
  - Expected: Whisper's raw capitalization preserved
- [ ] Set Capitalization back to "sentence" → Apply → dictate "hello. world"
  - Expected: "Hello. World" (capitalized after period)
- [ ] **Result:** ________________________________________

### T5.5: Config Persistence

- [ ] Make several settings changes, click Apply
- [ ] Quit Aside completely
- [ ] Relaunch Aside
- [ ] Open Settings
- [ ] Expected: All settings preserved from previous session
- [ ] **Result:** ________________________________________

---

## Phase 6: Failure Modes

Boeing doesn't just test the happy path. What happens when things go wrong?

### T6.1: No Microphone Permission

- [ ] Revoke Microphone permission for Terminal
- [ ] Launch Aside, try to dictate
- [ ] Expected: Graceful error. No crash. User-visible feedback about missing permission.
- [ ] Restore permission after test.
- [ ] **Result:** ________________________________________

### T6.2: No Accessibility Permission

- [ ] Revoke Accessibility permission for Terminal
- [ ] Launch Aside
- [ ] Expected: "Grant Access" prompt or clear error message
- [ ] **Result:** ________________________________________

### T6.3: Corrupt Dictionary File

- [ ] Write garbage to `~/.aside/dictionary.txt`: `echo "{{{{" > ~/.aside/dictionary.txt`
- [ ] Click Reload in Settings (or relaunch)
- [ ] Expected: No crash. Dictionary shows 0 terms or logs warning.
- [ ] **Result:** ________________________________________

### T6.4: Missing Dictionary File

- [ ] Delete: `rm ~/.aside/dictionary.txt`
- [ ] Click Reload or relaunch
- [ ] Expected: No crash. File recreated with template on next "Add" action.
- [ ] **Result:** ________________________________________

### T6.5: Corrupt Config File

- [ ] Write garbage to `~/.aside/config.json`: `echo "not json" > ~/.aside/config.json`
- [ ] Relaunch Aside
- [ ] Expected: Falls back to defaults. No crash.
- [ ] **Result:** ________________________________________

---

## Post-Test

- [ ] Restore `~/.aside` from backup: `rm -rf ~/.aside && mv ~/.aside.bak ~/.aside`
- [ ] Kill any orphan processes: `pkill -f "python.*aside"` (if needed)
- [ ] Document all non-conformances in a single list
- [ ] Classify each: **Blocker** (can't ship), **Major** (degraded experience), **Minor** (cosmetic/edge case)

---

## Sign-Off

| Phase | Pass/Fail | Tester | Date | Notes |
|-------|-----------|--------|------|-------|
| Pre-Flight | | | | |
| 1: Launch & Lifecycle | | | | |
| 2: Core Dictation | | | | |
| 3: Voice Commands | | | | |
| 4: Custom Dictionary | | | | |
| 5: Settings | | | | |
| 6: Failure Modes | | | | |
