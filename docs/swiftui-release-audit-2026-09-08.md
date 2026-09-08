# Aside SwiftUI release audit

Reviewed September 7–8, 2026. This is an implementation recommendation, not certification of a release. No application code, remote branches, issues, or PR states were changed by this audit.

## Recommendation

Keep the native SwiftUI shell and Python engine. Consolidate the two integration branches, then spend the release effort on installation, permission recovery, process lifecycle, and trustworthy dictation outcomes. The visible backlog badly underrepresents those risks.

Recommended first-release scope: Apple Silicon, a verified minimum macOS version, bundled base model, existing voice commands, existing dictionary compatibility, SwiftUI settings/onboarding/menu bar/Practice. Preserve the no-cloud, no-telemetry, no-clipboard-injection constraints. Defer engine rewrites, custom commands, persistent transcript history, and additional distribution channels.

### Evidence and limits

- Inspected all 15 remote branches, metadata/descriptions for all 87 PRs, the three issues, open-PR review threads, integration-branch history/diffs, native shell/helper/engine code, packaging scripts, workflow definitions, and recent workflow results. Historical PR descriptions were used as context; the current code determines implementation status.
- `main`: `f280bc6a9c6f6debb991a537f4446b9e0427bd6c`.
- `2026-may-dev`: `353199d93818973c10ab5adb435b9068fcb15a34`.
- Divergence: 17 commits exclusive to development, two exclusive to main. Development is not a superset of main.
- Latest published release returned by GitHub: [v1.2.1](https://github.com/blakeyoh/aside/releases/tag/v1.2.1), published May 5, with the legacy `Aside-1.2.1.dmg`. Source version is 1.3.0.
- Development-head [Build smoke passed May 29](https://github.com/blakeyoh/aside/actions/runs/26609912004).
- [SwiftUI release rehearsal passed May 21](https://github.com/blakeyoh/aside/actions/runs/26203906129), at `c0e2f1f`, before subsequent development changes. This is useful historical evidence, not verification of today's candidate.
- Local development-branch Python suite: **154 passed, 3 skipped**, using an isolated Python 3.12 environment with pytest/numpy and the repository's native-library shims. The project requires Python 3.13; this run is a portable logic check, not the supported runtime gate.
- No Swift test target exists in `native/AsideShell/Package.swift`. This Linux environment cannot verify SwiftUI rendering, real macOS permissions, audio capture, text injection, signing, or a downloaded DMG installation.
- The technical-spike document records successful real dictation in a development setup. Repeat that proof with the final installed and signed bundle.

## Backlog disposition

### Integration branches

| Branch | What it contains | Recommendation |
|---|---|---|
| `main` | SwiftUI shell and packaging scaffold, plus broader dictionary separator sanitization from #74 | Keep as default; preserve its security fixes during consolidation. |
| `2026-may-dev` | Native release workflow, stricter bundle verification, helper callback changes, dictionary cache, parser optimization, config permissions, expanded tests | Create one reviewed integration PR bringing this into main. Resolve differences deliberately; do not replace main's tree. |

The first integration must preserve both `splitlines()`-based input normalization from main and development's restrictive directory/file permissions. Preserve the parser optimization and removal of `parse_commands`. Verify semantic changes in the helper, hotkeys, number handling, and config; the development diff spans 63 files and includes formatting alongside behavior changes.

### All 13 open PRs and their branches

| PR | Branch | Actual relevance | Recommended disposition after integration |
|---|---|---|---|
| [#75](https://github.com/blakeyoh/aside/pull/75) | `bolt-optimize-parser-concat-9972110984150984513` | Parser optimization repeats development's existing reverse scan; branch also carries other historical differences | Close as superseded. Do not transplant its entire tree. |
| [#79](https://github.com/blakeyoh/aside/pull/79) | `claude/fervent-noether-4yYu8` | Misleading reload-feedback title: the only unique commit relative to development adds the June 3 suggestion-audit document | Preserve that historical audit document, then close or retitle as documentation-only. |
| [#80](https://github.com/blakeyoh/aside/pull/80) | `palette-visual-ux-fixes-6300037163591914589` | Legacy Tkinter visual changes | Defer/close for native release. |
| [#81](https://github.com/blakeyoh/aside/pull/81) | `bolt-parser-optimization-16405223979198754006` | Duplicate parser optimization | Close as superseded. |
| [#82](https://github.com/blakeyoh/aside/pull/82) | `palette-ui-refinements-12056171178429965081` | Legacy dividers and hover colors | Defer/close for native release. |
| [#83](https://github.com/blakeyoh/aside/pull/83) | `sentinel-fix-privacy-pane-validation-17542581787948210672` | Safe privacy-pane lookup already exists on development | Close as superseded. |
| [#84](https://github.com/blakeyoh/aside/pull/84) | `bolt-parser-optimization-2991483136454933239` | Duplicate parser optimization | Close as superseded. |
| [#85](https://github.com/blakeyoh/aside/pull/85) | `palette/fix-hover-contrast-16245002350721654391` | Legacy hover colors | Defer/close for native release. |
| [#86](https://github.com/blakeyoh/aside/pull/86) | `bolt-optimize-parser-17910333742797729133` | Duplicate parser optimization | Close as superseded. |
| [#87](https://github.com/blakeyoh/aside/pull/87) | `palette/hover-colors-14384528639503139353` | Legacy hover colors | Defer/close for native release. |
| [#88](https://github.com/blakeyoh/aside/pull/88) | `sentinel-fix-system-uri-dictionary-lookup-1445434693146002327` | Same safe lookup as #83; development already guards it | Close as superseded. |
| [#89](https://github.com/blakeyoh/aside/pull/89) | `bolt-optimize-array-joining-18348922804606061735` | Duplicate parser optimization | Close as superseded. |
| [#90](https://github.com/blakeyoh/aside/pull/90) | `palette-elevate-visual-consistency-16627682878676705272` | Legacy dividers and hover colors | Defer/close for native release. |

All open PRs returned zero inline review threads. That does not imply approval. Parser proposals contain repeated complexity claims; scanning backward over empty fragments is not universally O(1). No release value justifies merging five versions of the same optimization.

Important merged work includes #53 (native shell), #57 (native CI/release checks), #60 (dictionary cache), #66 (wrapper removal), #67/#74 (dictionary sanitization on different branches), #68 (tests), and #72 (parser/theme changes). Merged into a development branch does not mean shipped. Older closed packaging alternatives and repeated cache/permission proposals should remain historical references, not be reopened as missing features.

### All three issues

| Issue | Decision | Revised scope |
|---|---|---|
| [#76](https://github.com/blakeyoh/aside/issues/76): permission fallback tests | Implement with permission-recovery work | Keep fallback coverage; add actual helper state/recovery tests. Mocked permission functions alone cannot prove installed app identity. |
| [#77](https://github.com/blakeyoh/aside/issues/77): audio teardown and menu-bar sound | Split | Audio teardown matters for native release. Ensure `close()` still runs if `stop()` throws; merely asserting that exceptions are swallowed would bless a resource leak. Legacy menu-bar sound coverage can wait. |
| [#78](https://github.com/blakeyoh/aside/issues/78): migration, scroll clamp, engine error | Split | Keep malformed migration coverage; prioritize native helper/shell error behavior. Tk scroll clamping and Tk status rendering are legacy maintenance. |

The referenced June audit is on #79's branch, which explains why these issues refer to a document absent from both integration heads. Preserve that document when consolidating.

## Implementation order and release gates

Each row should be a small PR or tightly scoped set of PRs, with its own acceptance evidence. The identifiers below are proposed work packages, not existing GitHub issues.

| Order | Work package | Why it comes here | Required outcome |
|---|---|---|---|
| 1 | R1: consolidate branches and release authority | All later work needs one baseline | Preserve both branches' fixes, green Python 3.13/macOS checks, one native release path, updated README/TODO/agent instructions. Retain legacy source support without letting it define release readiness. |
| 2 | R2: prove the installed app identity and distribution path | Permission attribution could invalidate the architecture | Build an installed candidate, test permission prompts under its final identity, sign properly and rehearse notarization. Establish supported OS/architecture explicitly. |
| 3 | R3: reliable helper and permission state | Every user interaction depends on this | Graceful shutdown/restart, no stale-process callbacks, single engine ownership, permission refresh/recovery, actionable launch/audio errors, Swift supervisor tests. |
| 4 | R4: preserve user work and offline guarantees | Current failure paths can lose work or mislead users | Observable injection outcomes, safe target handling, atomic config/dictionary writes, shared input validation, local-model-only runtime selection. |
| 5 | R5: finish native interaction quality | UI can now reflect reliable state | Truthful readiness/status labels, keyboard/VoiceOver review, focus behavior, first-run practice, useful error recovery and dictionary feedback. |
| 6 | R6: candidate qualification and controlled release | Prove the artifact users actually get | Supported-runtime CI, real bundled-model test, signed DMG installation/upgrade checks, cold-machine offline dictation, state screenshots, bounded beta, release only the verified artifact. |

R2 should start immediately after consolidation: do not polish for weeks before discovering permission identity or signing is still wrong. R3/R4 establish the behavior R5 presents. R6 testing should accumulate throughout development, with the final candidate rerun after the last change.

### R2: installation and signing

`release.yml` on development uses ad-hoc signing and leaves notarization commented out. Its release workflow has advanced further than the stale TODO suggests, but it is not a polished public distribution path yet.

Use Developer ID signing with the appropriate hardened-runtime configuration and nested-code signing order, submit a supported archive/DMG format, staple and validate, then test a quarantined download on another Mac. Do not simply uncomment the existing raw `.app` submission example. Review entitlements per executable and validate required native-library exceptions. Apple references: [distribution signing](https://developer.apple.com/documentation/xcode/creating-distribution-signed-code-for-the-mac), [notarization](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

Acceptance: no Terminal needed; no global Python/Homebrew dependency on the user's Mac; correct Dock/icon identity; understandable permission attribution for the shell/helper; permissions survive a normal update; installed app and helper quit fully. Developer enrollment/certificate availability was not inspected.

### R3: helper lifecycle and readiness

Code-backed findings in `HelperSupervisor.swift` and `helper.py`:

- Shutdown sends a command and immediately terminates the process; restart uses a fixed 0.3-second delay. Use an asynchronous graceful-exit deadline, then escalation, and start a successor only after confirmed exit.
- Callbacks carry no process-generation identity. A queued old termination/event callback can affect a replacement. Clear stream remainders and transient capture/permission state at the correct lifecycle boundary and reject stale callbacks.
- Shell logs `hello` but does not validate the protocol version. Add a bounded handshake and explicit incompatible-helper recovery.
- SwiftUI launches `aside.helper` directly; the legacy `__main__` file lock does not guard this path. Introduce shared single-engine ownership so duplicate app copies or a legacy app cannot register competing hotkeys/inject twice.
- Model `ready` callbacks can replace an earlier permission error; `_start_recording` checks the state alone. Represent model readiness, process health, permissions, and capture separately; gate dictation on the required conjunction.
- Permission refresh is user-triggered; refresh when returning from System Settings and recover the event tap as needed. Confirm revoked grants transition to a recoverable state.
- Audio open failure can return false while the shell remains ready. Publish a specific device error. Guarantee stream teardown even when stop fails, including sleep/wake and device removal.

Swift tests should cover framed/fragmented IPC, malformed/unknown events, handshake timeout, unexpected exit, rapid restart, stale callbacks, shutdown during recording/transcription, and state reset. Keep process control behind an injectable boundary; avoid a broad UI rewrite just to create tests.

### R4: trustworthy dictation and persistence

1. **Injection outcome:** `inject_text` swallows errors and returns zero; `transcribe` still appends context and reports transcription/ready. It can also partially post events before returning zero. Report posting failures accurately and retain the processed result in memory for deliberate recovery. A successfully posted Quartz event still does not prove a destination accepted the text; use honest wording and real-app testing.
2. **Destination safety:** injection uses whichever app is focused at completion. Capture destination identity and detect focus changes; pause ambiguous delivery instead of sending text or destructive commands into a newly focused app. Scope `delete that` to a valid last-insertion context and invalidate it after uncertain focus/edit changes. Native behavior needs manual verification.
3. **Offline models:** SwiftUI offers tiny/base/small/medium/large-v3, while the bundle includes base. `_resolve_model_source` returns the model name when local assets are missing, allowing faster-whisper's download path. First release should expose only verified local assets, reject missing models with a recovery message, and explicitly prohibit runtime network fallback. Test existing configs selecting an unavailable model. Optional models should use deliberate local import if the no-network requirement remains.
4. **Model changes:** concurrent asynchronous loads have no generation check. Serialize changes or discard stale completions; avoid replacing a newer selection with an older load. Prevent changes from corrupting recording/transcription state.
5. **Settings saves:** helper commands ignore the boolean returned by `config_saver` and emit updated settings anyway. Validate a candidate, save successfully, then publish/apply it; surface failure without claiming persistence. Use atomic replacement and restrictive permissions from file creation, not just chmod afterward.
6. **Dictionary edits:** normalize all separators in the shared helper path, validate delimiter/comment semantics, and catch write failures at the command boundary. A hotword containing the arrow delimiter can be interpreted as a replacement. Preserve unrelated text and overflow entries: remove operations currently reserialize the parser's capped 50-term view, which can discard comments and entries beyond the cap. Test a file containing more than 50 terms and edits made outside the app.

### R5: better product ideas worth implementing

- **First successful dictation as onboarding completion.** Grants lead directly to a focused Practice scratch pad and a short phrase. Show the text result and an explicit success/retry action. Existing Practice is a scratch pad plus prompts; it does not verify outcomes. Keep action commands confined to the intended practice target.
- **A truthful readiness summary.** Replace hardcoded “Local model ready” with actual model/permission/helper state. Explain the one action needed to recover. Keep interpreter paths and raw logs in a diagnostics disclosure.
- **Recover the last undelivered result in memory.** Show processed text only when delivery is uncertain, with intentional insertion after target selection. Clear on quit or explicit dismissal; avoid automatic persistent history and do not introduce clipboard injection.
- **A local health check.** Model asset integrity, permissions, helper handshake, device availability, and bundle/build identity. Any export should exclude transcript text and dictionary contents by default. This is more useful at launch than a new command tier.
- **Recording feedback that prevents mistakes.** Clear recording/transcribing/error states, an accessible elapsed timer, cancel/discard, and a bounded recording policy. Audio chunks currently accumulate without a duration bound. Establish the limit from measured memory/latency and make the user-visible behavior explicit.

Review keyboard traversal, hotkey capture/cancel, menu-bar window focus, return from System Settings, contrast in supported appearance modes, VoiceOver labels, reduced motion where applicable, and layout at the supported minimum window size. Extract shared state/types and major panels from the large app file only where it makes these changes safer.

### R6: what qualifies the release

The current protocol-smoke mode uses no-op audio/hotkeys/transcriber. Keep it: it proves shell/helper plumbing. Add separate gates so its `ready` marker cannot be mistaken for working speech recognition.

| Gate | Required evidence |
|---|---|
| Logic and protocol | Python 3.13 suite, Swift supervisor tests, preserved command boundary/order and modifier-release behavior. |
| Real engine | Known local audio fixture through the bundled model, with expected command/rendering assertions tolerant of ASR variation; no network and no user cache dependency. |
| Bundle portability | Verify all nested Mach-O dependencies/architectures, loader paths and symlinks, model manifest integrity, versions, embedded helper, icons. Existing verification only scans a subset of native-library locations. |
| Distribution | Developer ID signature, notarization/stapling validation, quarantine/Gatekeeper acceptance, final DMG mounted/copied to Applications and launched. Current workflow verifies mounted structure but smoke-launches the build-directory app. |
| Actual dictation | Real microphone → push-to-talk and toggle → transcription → intended text field, punctuation, numbers, replacements, action commands; check TextEdit and representative browser/native editors. |
| Recovery | Deny/revoke/regrant each permission; no mic/unplugged mic; sleep/wake; helper crash; repeated restart; duplicate app launch; quit while recording/transcribing; focus switch before injection; read-only/corrupt config; unavailable model. |
| Upgrade and polish | Existing v1.2.1 configuration/dictionary preserved, understandable permissions, correct app/icon/version, accessible UI and screenshots for idle/loading/recording/transcribing/error/onboarding/settings. |

Freeze one candidate commit and artifact digest. Use a small beta with fresh-install and upgrade users, capture reproducible defects without automatic telemetry, and rerun affected gates after fixes. Never treat green legacy checks as native release approval. Add dependency constraints for repeatable release builds; pinning the model revision alone does not make the entire artifact reproducible.

### Defer and prevent recurrence

Defer Homebrew distribution, new command tiers, custom-command schemas, cloud/LLM enhancements, persistent/searchable transcript history, a separate tutorial website, and a native transcription-engine rewrite. Preserve existing behavior before broadening scope.

After consolidation, point automated maintenance at the canonical branch and native release goals. Require each proposed change to identify a reproducible user problem, check for an existing PR/fix, name the affected runtime surface, and provide relevant evidence. Pause repetitive legacy palette/parser campaigns. Archive superseded branches only after their unique work is preserved and their disposition is recorded.

The first implementation should be R1's integration PR. The first major proof should be R2's installed identity and signing rehearsal. That sequence removes uncertainty before investing in more visual polish.
