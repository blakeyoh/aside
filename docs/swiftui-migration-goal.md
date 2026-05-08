Migrate Aside to a native SwiftUI UI shell with a supervised local
  Python helper, then deliver the visual/UX makeover from the attached design
  board.

  Goal:
  Create a native-feeling SwiftUI macOS shell for Aside while preserving the
  existing Python dictation/transcription engine. This goal has two phases:

  1. Technical spike: prove the SwiftUI shell + Python helper architecture is
  viable.
  2. Visual migration: if the spike passes, implement the attached design
  direction across the main app surfaces.

  Do not continue into the visual migration if the technical spike fails the
  smoke test or creates unacceptable permission/packaging risk.

  Context:
  Aside currently uses Python customtkinter for windows and PyObjC/AppKit for
  menu bar integration. The engine is already working and should remain
  behaviorally stable.

  Current UI files:
  - src/aside/ui/app.py
  - src/aside/ui/settings.py
  - src/aside/ui/onboarding.py
  - src/aside/ui/menubar.py
  - src/aside/ui/theme.py

  Current engine/config/permissions files:
  - src/aside/engine/
  - src/aside/config.py
  - src/aside/permissions.py

  Current packaging:
  - setup_py2app.py
  - scripts/build_app.sh
  - scripts/package_dmg.sh

  Visual references:
  - attached design board
  - assets/NEW-aside-swiftUI-system.png
  - assets/NEW-aside-logo.png

  Architecture direction:
  Build a native SwiftUI macOS app shell that supervises a local Python helper.
  Prefer stdio or Unix domain socket IPC. Avoid localhost HTTP/WebSocket unless
  there is a strong reason and the privacy implications are documented.

  The SwiftUI shell should own:
  - app/window lifecycle
  - settings window
  - onboarding/permissions UI
  - menu bar UI
  - visual state presentation
  - launching/stopping/restarting the Python helper
  - displaying helper status/errors
  - editing/sending config changes where appropriate

  The Python helper should initially own:
  - Whisper model loading
  - audio capture
  - hotkey handling
  - recording/transcribing state machine
  - transcription pipeline
  - text injection
  - dictionary/replacements/voice commands
  - existing config compatibility unless deliberately moved

  Hard constraints:
  - Preserve existing dictation/transcription behavior.
  - Preserve push-to-talk and toggle hotkey behavior.
  - Preserve required permissions:
    - Microphone
    - Accessibility
    - Input Monitoring
  - Do not add telemetry, analytics, accounts, subscriptions, cloud APIs, or
  cloud language.
  - Do not add network calls.
  - Do not silently remove existing tests.
  - Prefer small, reviewable steps.
  - Keep copy minimal, clear, and privacy-forward.

  Phase 1: Technical spike
  Before the visual migration, implement the smallest viable SwiftUI shell +
  Python helper proof.

  The spike must prove:
  1. A SwiftUI macOS app can launch and supervise the Python helper.
  2. The helper can report status back to SwiftUI:
     - loading
     - ready
     - recording
     - transcribing
     - error
  3. The existing hotkey path still works or has a clear equivalent path.
  4. Microphone capture still works.
  5. Transcription still runs through the existing Python pipeline.
  6. Text injection still works into another focused app.
  7. Permissions are requested/shown under an acceptable app identity.
  8. The helper can shut down cleanly when the SwiftUI app quits.
  9. Packaging/build direction is credible and documented.

  Quality smoke test gate:
  After the spike, stop and evaluate before continuing. Kill the goal or pause
  for user decision if any of these are true:
  - Microphone, Accessibility, or Input Monitoring permissions appear under a
  confusing or unacceptable helper identity.
  - Hotkey detection cannot work reliably from the helper.
  - Text injection cannot work reliably from the helper.
  - The helper requires localhost/network-style communication.
  - Packaging requires brittle global Python assumptions.
  - Existing dictation behavior regresses.
  - The architecture requires a larger engine rewrite than expected.
  - Build/run steps become too complex for a normal contributor.
  - The spike cannot be verified locally with clear instructions.

  If the spike fails:
  - Do not continue into visual migration.
  - Leave the repo in a clean, reviewable state.
  - Summarize what failed, why, and recommend the next architecture option.

  If the spike passes:
  Continue to Phase 2.

  Phase 2: Visual/UX migration
  Use the attached board as a design-system reference, not a pixel-perfect spec.
  Build a polished native macOS utility experience.

  Implement/refine these SwiftUI surfaces:
  1. Main settings window
     - app identity/header
     - dictation mode controls
     - push-to-talk and toggle hotkey settings
     - local model status
     - dictionary access/status
     - voice commands access/status if applicable
     - privacy/local-only status
     - clear grouped native macOS layout

  2. First-run permissions onboarding
     - explain each required permission
     - show live granted/missing state
     - provide System Settings actions/deep links
     - continue only when required permissions are granted
     - use privacy copy aligned with:
       - “Audio stays on this Mac”
       - “No cloud. No telemetry.”
       - “Works offline.”

  3. Menu bar UI
     - idle state
     - recording state
     - transcribing state
     - loading/error states
     - settings action
     - permissions action
     - quit action
     - local/privacy reassurance
     - native MenuBarExtra or NSStatusItem behavior as appropriate

  4. App/menu bar assets
     - use existing assets as reference:
       - assets/NEW-aside-logo.png
       - assets/NEW-aside-swiftUI-system.png
     - update app/menu bar icon assets only if supported by the new packaging
  path
     - document follow-up asset work if production icon generation is out of
  scope

  Design system:
  Create reusable SwiftUI design constants/tokens for:
  - graphite/dark app icon surface
  - off-white settings surface
  - slate text
  - blue active/transcribing
  - amber recording
  - green ready/local/privacy
  - red/error/missing permission
  - spacing scale
  - corner radii
  - typography hierarchy
  - status badges
  - permission rows
  - hotkey keycaps

  Verification:
  Run relevant checks, including:
  - .venv/bin/python3 -m pytest tests/ -v
  - Swift build/test command introduced by the migration
  - local app launch smoke test
  - permission/onboarding smoke test
  - recording/transcribing/text injection smoke test
  - packaging/build smoke test if packaging is changed

  Done when:
  - The technical spike passes the quality smoke test gate.
  - The SwiftUI shell builds and launches the Python helper.
  - Existing dictation/transcription behavior is unchanged.
  - The visual migration clearly matches the attached design direction.
  - Idle, loading, recording, transcribing, error, and permission states are
  visually distinct.
  - Privacy/local-only messaging is clearer than before.
  - Existing Python tests pass.
  - New Swift build checks pass.
  - Final response includes:
    - whether the spike passed
    - changed files
    - architecture decisions
    - build/test results
    - smoke test results
    - screenshots or exact local UI review instructions
    - follow-up recommendations for packaging, signing, notarization, or future
  native engine migration