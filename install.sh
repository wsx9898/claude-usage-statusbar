#!/bin/bash
# 安裝 LaunchAgent：登入時自動啟動（RunAtLoad）。
# KeepAlive=false：從選單列「結束」即永久關閉，launchd 不會把它拉回來；
# 是否登入自動啟動可在選單列「開機時自動啟動」切換。
#
# 重要：macOS 會對 ~/Documents、~/Desktop、~/Downloads 等位置做 TCC 權限保護，
# 由 launchd 啟動的程序無法在這些位置「執行」程式碼（會出現 Operation not permitted）。
# 因此安裝時會把執行用的副本部署到不受保護的：
#   ~/Library/Application Support/claude-usage-statusbar/
# 開發用原始碼仍可放在 ~/Documents 的 git 倉庫中；此處只是部署一份執行副本。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LABEL="com.user.claude-usage-statusbar"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs"
APP_HOME="$HOME/Library/Application Support/claude-usage-statusbar"

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR" "$APP_HOME"

# 1) 部署執行副本到不受 TCC 保護的位置
echo "[install] 部署執行副本到：$APP_HOME"
rm -rf "$APP_HOME/src"
cp -R "$SCRIPT_DIR/src" "$APP_HOME/src"
cp "$SCRIPT_DIR/run.sh" "$APP_HOME/run.sh"
cp "$SCRIPT_DIR/requirements.txt" "$APP_HOME/requirements.txt"
chmod +x "$APP_HOME/run.sh"

# 2) 在副本位置預先建立 venv 與相依套件（此時由 Terminal 執行，具備存取權）
echo "[install] 建立執行環境（首次會安裝 rumps，請稍候）…"
PYTHON_BIN="${PYTHON_BIN:-python3}" bash "$APP_HOME/run.sh" &
SETUP_PID=$!
# 等待 venv 與套件就緒（最多 ~90 秒），就緒後即可結束這個前置啟動
for _ in $(seq 1 90); do
  if "$APP_HOME/.venv/bin/python" -c "import rumps" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
sleep 2
kill "$SETUP_PID" >/dev/null 2>&1 || true
wait "$SETUP_PID" 2>/dev/null || true

# 3) 寫入 LaunchAgent，指向副本位置的 run.sh
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
        <string>/bin/bash</string>
        <string>$APP_HOME/run.sh</string>
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

# 4) 重新載入
launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"

echo "[install] 完成！App 已啟動並會在每次登入時自動執行。"
echo "          執行副本：$APP_HOME"
echo "          記錄檔：$LOG_DIR/$LABEL.log"
echo "          解除安裝：bash uninstall.sh"
