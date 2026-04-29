#!/bin/bash
# Regenerate AppIcon.icns from aside-logo.png
# Run from the project root after updating aside-logo.png.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE="$SCRIPT_DIR/aside-logo.png"
ICONSET="$SCRIPT_DIR/aside-icon.iconset"
OUTPUT="$SCRIPT_DIR/AppIcon.icns"
ASSETS_OUTPUT="$SCRIPT_DIR/assets/AppIcon.icns"

if [ ! -f "$SOURCE" ]; then
    echo "❌  aside-logo.png not found at $SOURCE"
    exit 1
fi

mkdir -p "$ICONSET"

for size in 16 32 128 256 512; do
    sips -z $size $size "$SOURCE" --out "$ICONSET/icon_${size}x${size}.png" > /dev/null
    double=$((size * 2))
    sips -z $double $double "$SOURCE" --out "$ICONSET/icon_${size}x${size}@2x.png" > /dev/null
done

iconutil -c icns "$ICONSET" -o "$OUTPUT"
rm -rf "$ICONSET"

mkdir -p "$SCRIPT_DIR/assets"
cp "$OUTPUT" "$ASSETS_OUTPUT"

echo "✅  AppIcon.icns updated ($OUTPUT)"
echo "✅  Assets copy updated ($ASSETS_OUTPUT)"
