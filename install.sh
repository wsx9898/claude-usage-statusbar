#!/bin/bash
# macOS 安裝：編譯 Swift 版選單列 App，安裝到 ~/Applications，並設定登入自動啟動（LaunchAgent）。
# KeepAlive=false：從選單列「結束」即永久關閉，launchd 不會把它拉回來；
# 是否登入自動啟動可在選單列「開機時自動啟動」切換。
#
# 需求：Xcode Command Line Tools（`xcode-select --install`，提供 swift 編譯器）。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.user.claude-usage-statusbar"
NAME="ClaudeUsageStatusBar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
APP_DIR="$HOME/Applications"
APP="$APP_DIR/$NAME.app"
LEGACY_HOME="$HOME/Library/Application Support/claude-usage-statusbar"  # 舊 Python 版的執行副本

if ! command -v swift >/dev/null 2>&1; then
  echo "[install] 找不到 swift，請先執行：xcode-select --install" >&2
  exit 1
fi

# 1) 編譯
echo "[install] 編譯 Swift 版（首次約需 1 分鐘）…"
BUILT="$(bash "$SCRIPT_DIR/macos/build.sh" | tail -n 1)"

# 2) 停掉舊的執行個體（含舊 Python 版），再部署 .app
launchctl unload "$PLIST" >/dev/null 2>&1 || true
pkill -f "$APP/Contents/MacOS/$NAME" >/dev/null 2>&1 || true
pkill -f "python.* -m usage_statusbar" >/dev/null 2>&1 || true

mkdir -p "$APP_DIR" "$HOME/Library/LaunchAgents" "$LOG_DIR"
rm -rf "$APP"
cp -R "$BUILT" "$APP"
echo "[install] 已安裝：$APP"

if [ -d "$LEGACY_HOME" ]; then
  rm -rf "$LEGACY_HOME"
  echo "[install] 已移除舊 Python 版執行副本：$LEGACY_HOME"
fi

# 3) 寫入 LaunchAgent（與 App 內「開機時自動啟動」寫出的內容相同）
echo "[install] 寫入 LaunchAgent：$PLIST"
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$APP/Contents/MacOS/$NAME</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>StandardOutPath</key>
    <string>$LOG_DIR/$LABEL.log</string>
    <key>StandardErrorPath</key>
    <string>$LOG_DIR/$LABEL.err.log</string>
</dict>
</plist>
PLIST_EOF

# 4) 載入（RunAtLoad 會立刻啟動）
launchctl load "$PLIST"

echo "[install] 完成！App 已啟動並會在每次登入時自動執行。"
echo "          App：$APP"
echo "          記錄檔：$LOG_DIR/$LABEL.log"
echo "          解除安裝：bash uninstall.sh"
