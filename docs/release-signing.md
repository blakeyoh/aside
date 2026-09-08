# Native release signing and notarization

This is the distribution contract for Aside 1.3.0 and later. The public
artifact is the native SwiftUI app with an embedded Python helper. Ad-hoc
signatures and the standalone customtkinter/py2app DMG are not release paths.

## Identity and bundle layout

- Main app: `com.blakeyoh.aside`
- Embedded helper: `com.blakeyoh.aside.helper`
- Supported target: macOS 13 or later, Apple Silicon (`arm64`)
- Main executable: `Aside.app/Contents/MacOS/Aside`
- Helper bundle: `Aside.app/Contents/Helpers/AsideHelper.app`
- Bundled model: helper `Contents/Resources/faster-whisper-base`

`Contents/Helpers` is intentional. Apple code signing records nested code in
the outer signature, so nested items must use a standard code location and be
signed from the inside out before the outer app.

The SwiftUI process receives no runtime exceptions. The helper alone receives
audio-input and unsigned-executable-memory entitlements because it owns audio
capture and hosts the ctranslate2/libffi native runtime. Any change to that
entitlement set requires installed hardened-runtime dictation evidence.

## Required GitHub secrets

Configure these repository Actions secrets before running the native rehearsal
or pushing a release tag:

- `MACOS_CERTIFICATE`: base64-encoded Developer ID Application `.p12`
- `MACOS_CERTIFICATE_PASSWORD`: password used to export the `.p12`
- `KEYCHAIN_PASSWORD`: ephemeral CI keychain password
- `APPLE_ID`: Apple Developer account email
- `APPLE_TEAM_ID`: ten-character Developer Team ID
- `NOTARIZE_PASSWORD`: app-specific Apple ID password

Both workflows fail before building when a credential is absent. The imported
keychain must contain exactly one valid `Developer ID Application` identity.
The temporary certificate and keychain are deleted in an `always()` step.

## Local sequence

After activating the supported Python 3.13 environment, use the reviewed model
revision and a Developer ID identity available in the current keychain:

```bash
export MODEL_REVISION=ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66
export CODESIGN_IDENTITY="Developer ID Application: Name (TEAMID)"

scripts/build_swiftui_app.sh release
scripts/verify_swiftui_bundle.sh dist-swiftui/Aside.app
scripts/sign_swiftui_bundle.sh "$CODESIGN_IDENTITY" dist-swiftui/Aside.app
scripts/smoke_swiftui_launch.sh --app dist-swiftui/Aside.app
scripts/package_swiftui_dmg.sh "$CODESIGN_IDENTITY"
```

Store notary credentials in a dedicated keychain profile, then submit the DMG:

```bash
xcrun notarytool store-credentials aside-notary \
  --apple-id "$APPLE_ID" \
  --team-id "$APPLE_TEAM_ID" \
  --password "$NOTARIZE_PASSWORD"

scripts/notarize_swiftui_dmg.sh \
  aside-notary "$HOME/Library/Keychains/login.keychain-db" \
  dist-swiftui/Aside-SwiftUI-1.3.0.dmg
scripts/verify_swiftui_dmg.sh --distribution \
  dist-swiftui/Aside-SwiftUI-1.3.0.dmg
```

Do not put credentials directly in repository files, shell history, logs, or
release manifests. Do not remove quarantine or bypass Gatekeeper to make an
artifact appear acceptable.

## What automation proves

The native rehearsal and tag workflow require all of the following before an
artifact can be uploaded or published:

1. Python 3.13 tests and the native build complete.
2. Bundle structure, versions, architecture, helper location, model, native
   links, and symlinks pass verification.
3. All nested Mach-O code is signed inside-out with secure timestamps and
   hardened runtime.
4. Main and helper entitlements match the reviewed per-process minimum.
5. The signed DMG receives an `Accepted` notary result, is stapled, and passes
   `stapler` plus `spctl` assessment.
6. The app copied from the final DMG passes distribution verification and the
   bounded helper protocol smoke.
7. A manifest records commit, artifact digest, model revision, OS,
   architecture, Python, Swift, and Xcode versions.

This still does not prove microphone capture, Accessibility/Input Monitoring
attribution, real text injection, permission persistence after update, or
installed-app quit behavior. Those need the same final DMG on another Mac.

## Clean-Mac manual gate

Record the candidate commit and SHA-256 before starting. On a Mac that has not
built Aside and has no developer checkout or model cache:

1. Download the workflow artifact through the normal browser path so quarantine
   is present. Confirm `xattr -p com.apple.quarantine` returns a value.
2. Open the DMG normally, copy Aside to `/Applications`, and launch that copy.
3. Confirm Gatekeeper accepts it without override instructions.
4. Confirm Dock/menu-bar identity is Aside and note the identity macOS presents
   for Microphone, Accessibility, and Input Monitoring.
5. Grant each permission, perform real push-to-talk and toggle dictation into a
   separate app, then quit Aside. Confirm the helper and event tap exit.
6. Install the same-version candidate again, then perform the planned v1.2.1
   upgrade case. Confirm permissions, `~/.aside/config.json`, and
   `~/.aside/dictionary.txt` remain intact.
7. Deny, revoke, and regrant each permission and record recovery behavior.

Record PASS, FAIL, or NOT RUN for every step. A failure in identity,
Gatekeeper, permission recovery, real dictation, update persistence, or full
quit blocks release and routes the defect to R2 or R3.

## Current evidence

- Local Developer ID identities on the implementation host: none.
- GitHub Actions distribution secret names configured: none.
- Developer ID signing: NOT RUN.
- Notarization and stapling: NOT RUN.
- Quarantined clean-Mac installation and permission identity: NOT RUN.
- Real installed-app dictation: NOT RUN.

Do not edit these entries to PASS without attaching candidate-specific command
output, workflow URLs, artifact digest, OS/architecture, and manual evidence.
