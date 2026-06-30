#!/bin/bash
# 啟動器：第一次執行時建立隔離的 venv 並安裝相依套件，之後直接啟動 App。
# LaunchAgent 與手動執行都呼叫這支腳本。
set -euo pipefail

# 取得腳本所在目錄（即專案根目錄），不依賴呼叫者的工作目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR="$SCRIPT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

# 建立 venv（若尚未存在）
if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "[setup] 建立虛擬環境：$VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null
fi

# 安裝/更新相依套件（rumps 不存在時才裝，加快後續啟動）
if ! "$VENV_DIR/bin/python" -c "import rumps" >/dev/null 2>&1; then
  echo "[setup] 安裝相依套件"
  "$VENV_DIR/bin/python" -m pip install -r "$SCRIPT_DIR/requirements.txt"
fi

# 讓 Python 找得到 src 下的套件
export PYTHONPATH="$SCRIPT_DIR/src${PYTHONPATH:+:$PYTHONPATH}"

exec "$VENV_DIR/bin/python" -m usage_statusbar
