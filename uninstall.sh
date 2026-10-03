#!/bin/bash
# 解除安裝 LaunchAgent 並停止 App。
# 預設保留 ~/Applications/ClaudeUsageStatusBar.app；加上 --purge 一併刪除。
set -euo pipefail

LABEL="com.user.claude-usage-statusbar"
NAME="ClaudeUsageStatusBar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="$HOME/Applications/$NAME.app"
LEGACY_HOME="$HOME/Library/Application Support/claude-usage-statusbar"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  echo "[uninstall] 已移除 LaunchAgent。"
else
  echo "[uninstall] 找不到 LaunchAgent，可能尚未安裝。"
fi
pkill -f "$APP/Contents/MacOS/$NAME" >/dev/null 2>&1 || true
echo "[uninstall] 已停止 App。"

if [ "${1:-}" = "--purge" ]; then
  rm -rf "$APP" "$LEGACY_HOME"
  echo "[uninstall] 已刪除：$APP"
else
  echo "[uninstall] 保留：$APP（加 --purge 可一併刪除）"
fi
