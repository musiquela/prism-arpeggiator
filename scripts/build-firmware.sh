#!/bin/bash
# Build firmware distribution package for Prism MIDI Arpeggiator
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VERSION=$(cat "$PROJECT_ROOT/VERSION" | tr -d '[:space:]')

BUILD_DIR="$PROJECT_ROOT/dist/build"
OUTPUT_DIR="$PROJECT_ROOT/dist"
PACKAGE_NAME="prism-firmware-v${VERSION}"
BUNDLE_URL="https://github.com/adafruit/Adafruit_CircuitPython_Bundle/releases/download/20250513/adafruit-circuitpython-bundle-9.x-mpy-20250513.zip"

echo "Building Prism MIDI Arpeggiator firmware v${VERSION}"
echo "================================================"

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/$PACKAGE_NAME"
mkdir -p "$BUILD_DIR/$PACKAGE_NAME/lib"
mkdir -p "$OUTPUT_DIR"

# Copy application files
echo "Copying application files..."
cp "$PROJECT_ROOT/code.py" "$BUILD_DIR/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/boot.py" "$BUILD_DIR/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/arpeggiator.py" "$BUILD_DIR/$PACKAGE_NAME/"
cp "$PROJECT_ROOT/note_buffer.py" "$BUILD_DIR/$PACKAGE_NAME/"

# Download and extract libraries
echo "Downloading CircuitPython library bundle..."
BUNDLE_ZIP="$BUILD_DIR/bundle.zip"
curl -L -s -o "$BUNDLE_ZIP" "$BUNDLE_URL"

echo "Extracting required libraries..."
BUNDLE_EXTRACT="$BUILD_DIR/bundle"
unzip -q "$BUNDLE_ZIP" -d "$BUNDLE_EXTRACT"
BUNDLE_LIB="$BUNDLE_EXTRACT/adafruit-circuitpython-bundle-9.x-mpy-20250513/lib"

# Copy required libraries
cp -r "$BUNDLE_LIB/adafruit_midi" "$BUILD_DIR/$PACKAGE_NAME/lib/"
cp -r "$BUNDLE_LIB/adafruit_display_text" "$BUILD_DIR/$PACKAGE_NAME/lib/"
cp -r "$BUNDLE_LIB/adafruit_display_shapes" "$BUILD_DIR/$PACKAGE_NAME/lib/"
cp "$BUNDLE_LIB/adafruit_max1704x.mpy" "$BUILD_DIR/$PACKAGE_NAME/lib/"

# Create INSTALL.txt
echo "Creating install instructions..."
cat > "$BUILD_DIR/$PACKAGE_NAME/INSTALL.txt" << 'EOF'
PRISM MIDI ARPEGGIATOR - FIRMWARE UPDATE

1. Delete everything on the CIRCUITPY drive
2. Copy all files from this folder to CIRCUITPY
EOF

# Create ZIP
echo "Creating distribution package..."
cd "$BUILD_DIR"
zip -r -q "$OUTPUT_DIR/$PACKAGE_NAME.zip" "$PACKAGE_NAME"

# Cleanup
rm -rf "$BUILD_DIR"

echo ""
echo "Done! Package created:"
echo "  $OUTPUT_DIR/$PACKAGE_NAME.zip"
echo ""
echo "Contents:"
unzip -l "$OUTPUT_DIR/$PACKAGE_NAME.zip" | head -20
