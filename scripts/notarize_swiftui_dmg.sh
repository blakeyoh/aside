#!/usr/bin/env bash
set -euo pipefail

# Submit a signed DMG with a previously stored notarytool keychain profile,
# require an Accepted result, then staple and validate the ticket.

PROFILE="${1:-}"
KEYCHAIN="${2:-}"
DMG="${3:-}"
NOTARY_TIMEOUT="${NOTARY_TIMEOUT:-30m}"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

[[ -n "$PROFILE" ]] || fail "notarytool keychain profile is required"
[[ -n "$KEYCHAIN" ]] || fail "keychain path is required"
[[ -f "$KEYCHAIN" ]] || fail "keychain not found: $KEYCHAIN"
[[ -n "$DMG" && -f "$DMG" ]] || fail "signed DMG not found: $DMG"

codesign --verify --verbose=2 "$DMG"

RESULT_PATH="${DMG%.dmg}.notary.json"
LOG_PATH="${DMG%.dmg}.notary-log.json"

echo "==> Submitting $DMG for notarization"
set +e
xcrun notarytool submit "$DMG" \
  --keychain-profile "$PROFILE" \
  --keychain "$KEYCHAIN" \
  --wait \
  --timeout "$NOTARY_TIMEOUT" \
  --output-format json | tee "$RESULT_PATH"
SUBMIT_STATUS="${PIPESTATUS[0]}"
set -e

SUBMISSION_ID="$(python3 - "$RESULT_PATH" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.load(handle).get("id", ""))
except (OSError, json.JSONDecodeError):
    print("")
PY
)"

NOTARY_STATUS="$(python3 - "$RESULT_PATH" <<'PY'
import json
import sys

try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        print(json.load(handle).get("status", ""))
except (OSError, json.JSONDecodeError):
    print("")
PY
)"

if [[ "$SUBMIT_STATUS" != "0" || "$NOTARY_STATUS" != "Accepted" ]]; then
  if [[ -n "$SUBMISSION_ID" ]]; then
    xcrun notarytool log \
      --keychain-profile "$PROFILE" \
      --keychain "$KEYCHAIN" \
      "$SUBMISSION_ID" "$LOG_PATH" || true
  fi
  fail "notarization was not accepted (command=$SUBMIT_STATUS, status=${NOTARY_STATUS:-unknown})"
fi

echo "==> Stapling and validating notarization ticket"
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"
spctl --assess --type open --context context:primary-signature --verbose=4 "$DMG"

echo "==> Notarized DMG ready: $DMG"
