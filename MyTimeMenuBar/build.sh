#!/bin/bash
# Build MyTimeMenuBar and launch it standalone, no Xcode required.
#
# Usage:
#   ./build.sh            # Debug build, then (re)launch it
#   ./build.sh Release     # Release build, then (re)launch it
set -euo pipefail
cd "$(dirname "$0")"

CONFIGURATION="${1:-Debug}"

xcodebuild -project MyTimeMenuBar.xcodeproj \
  -scheme MyTimeMenuBar \
  -configuration "$CONFIGURATION" \
  -derivedDataPath build \
  build

BUILT_APP_PATH="build/Build/Products/$CONFIGURATION/MyTimeMenuBar.app"
INSTALLED_APP_PATH="/Applications/MyTimeMenuBar.app"

# Kill any already-running instance so testing always picks up the new build.
killall MyTimeMenuBar 2>/dev/null || true

echo "Installing to $INSTALLED_APP_PATH"
rm -rf "$INSTALLED_APP_PATH"
ditto "$BUILT_APP_PATH" "$INSTALLED_APP_PATH"

echo "Launching $INSTALLED_APP_PATH"
open "$INSTALLED_APP_PATH"
