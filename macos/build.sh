#!/bin/bash
# 編譯 Swift 版並組成 .app（ad-hoc 簽章）。產物：macos/build/ClaudeUsageStatusBar.app
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="ClaudeUsageStatusBar"
APP="$DIR/build/$NAME.app"

cd "$DIR"
swift build -c release
BIN="$(swift build -c release --show-bin-path)/$NAME"

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS"
cp "$BIN" "$APP/Contents/MacOS/$NAME"
cp "$DIR/Info.plist" "$APP/Contents/Info.plist"
codesign --force --sign - "$APP" >/dev/null 2>&1 || true

echo "$APP"
