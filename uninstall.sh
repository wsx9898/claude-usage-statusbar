#!/bin/bash
# 解除安裝 LaunchAgent 並停止 App。
# 預設保留執行副本（~/Library/Application Support/claude-usage-statusbar）；
# 加上 --purge 可一併刪除該副本與 venv。
set -euo pipefail

LABEL="com.user.claude-usage-statusbar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP_HOME="$HOME/Library/Application Support/claude-usage-statusbar"

if [ -f "$PLIST" ]; then
  launchctl unload "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
  echo "[uninstall] 已移除 LaunchAgent 並停止 App。"
else
  echo "[uninstall] 找不到 LaunchAgent，可能尚未安裝。"
fi

if [ "${1:-}" = "--purge" ]; then
  rm -rf "$APP_HOME"
  echo "[uninstall] 已刪除執行副本：$APP_HOME"
else
  echo "[uninstall] 保留執行副本：$APP_HOME（加 --purge 可一併刪除）"
fi
