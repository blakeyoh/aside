# Aside release work

The native SwiftUI shell with its supervised local Python helper is the release
product. The source-run customtkinter UI and standalone py2app bundle remain for
compatibility and regression checks, but they do not define release readiness.

Current scope and acceptance evidence are governed by
[`docs/swiftui-release-audit-2026-09-08.md`](docs/swiftui-release-audit-2026-09-08.md).
Complete work packages in order. A green protocol smoke or legacy workflow is
never sufficient to call a native candidate release-ready.

## R1: consolidate branches and release authority

- [x] Merge `2026-may-dev` into a branch based on current `main`.
- [x] Preserve main's `splitlines()` dictionary sanitization and development's
  restrictive file/directory permissions.
- [x] Preserve parser optimization, cached dictionary invalidation, hotkey
  fixes, expanded tests, native bundle verification, and native workflows.
- [x] Keep `parse_commands` removed.
- [x] Preserve the June suggestion audit from PR #79.
- [x] Make the native SwiftUI DMG the sole publish path; label legacy py2app
  workflows and documents as compatibility history.
- [x] Align documentation and bundle metadata on Apple Silicon and macOS 13+.
- [ ] Merge the reviewed R1 integration PR into `main` after required CI passes.

## R2: installed identity and distribution

- [ ] Build one candidate from the consolidated baseline and record its commit,
  artifact SHA-256, macOS version, architecture, Python/Swift toolchains, and
  model revision.
- [ ] Configure Developer ID signing, hardened runtime, nested signing order,
  and per-executable entitlements.
- [ ] Submit a supported archive or DMG for notarization, staple it, and verify
  Gatekeeper acceptance without bypassing quarantine.
- [ ] Install the DMG copy into `/Applications` on another Mac and verify app,
  helper, Dock, and permission identities plus update persistence.

## R3: helper lifecycle and permission recovery

- [ ] Add an asynchronous graceful-shutdown deadline with escalation and
  serialize restarts until the prior helper's confirmed exit.
- [ ] Reject stale stdout, stderr, timeout, and termination callbacks using a
  process generation; reset framing and transient state between helpers.
- [ ] Add a bounded protocol handshake and incompatible-helper recovery.
- [ ] Enforce shared single-engine ownership across native and legacy entry
  points.
- [ ] Track process, model, permissions, and capture state separately; refresh
  permissions after returning from System Settings.
- [ ] Surface actionable audio/device failures and guarantee stream teardown
  even when `stop()` fails.
- [ ] Add Swift supervisor tests for protocol framing, malformed events,
  handshake timeout, exit/restart races, stale callbacks, and shutdown states.

## R4: trustworthy dictation and persistence

- [ ] Report text-injection outcomes honestly and keep one bounded undelivered
  result in memory for deliberate recovery.
- [ ] Capture destination identity, pause delivery after uncertain focus
  changes, and scope destructive commands to a valid insertion context.
- [ ] Restrict runtime model loading to verified local assets; reject missing or
  migrated unavailable models without network fallback.
- [ ] Serialize model changes or discard stale load completions.
- [ ] Validate, atomically save, then apply settings; never acknowledge a failed
  persistence operation as saved.
- [ ] Make dictionary edits lossless and conflict-aware, preserving comments,
  unknown lines, and entries beyond the 50-term active cap.

## R5: native interaction quality

- [ ] Complete onboarding only after a verified first successful dictation in
  the Practice target.
- [ ] Derive readiness and recovery copy from real helper/model/permission/device
  state; keep raw diagnostics behind disclosure.
- [ ] Provide intentional recovery for the last undelivered in-memory result.
- [ ] Add a privacy-safe local health check.
- [ ] Add accessible recording/transcribing/error feedback, cancel/discard, and
  a measured bounded-recording policy.
- [ ] Verify keyboard traversal, hotkey capture/cancel, focus return, contrast,
  VoiceOver labels, reduced motion, and minimum-window layout.

## R6: qualify and control the release

- [ ] Run Python 3.13 logic/protocol checks and Swift supervisor tests.
- [ ] Run a no-network bundled-model audio fixture independent of user caches.
- [ ] Verify every nested Mach-O dependency, architecture, loader path, symlink,
  model manifest, version, helper, and icon.
- [ ] Verify Developer ID signature, notarization, staple, quarantine, DMG
  install/copy, and launch of the installed app.
- [ ] Manually verify real microphone dictation and command behavior in TextEdit
  and representative browser/native editors.
- [ ] Exercise permission, microphone/device, sleep/wake, helper crash/restart,
  duplicate launch, quit, focus switch, corrupt/read-only persistence, and
  unavailable-model recovery.
- [ ] Verify fresh install and v1.2.1 upgrade, UI states, accessibility, and
  screenshots against one frozen candidate digest.
- [ ] Run a bounded beta and rerun affected gates after every candidate fix.

## Deferred until after the native release

- Homebrew and additional distribution channels
- New or custom command tiers
- Cloud or LLM features
- Persistent/searchable transcript history
- Separate tutorial website
- Native transcription-engine rewrite
