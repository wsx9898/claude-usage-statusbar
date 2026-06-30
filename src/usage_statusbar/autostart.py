"""管理 macOS LaunchAgent（登入時自動啟動）。

設計：
- LaunchAgent 的 `KeepAlive=false`，所以從選單列按「結束」就是永久關閉，
  launchd 不會把它拉回來；只有「登入」時才會依 `RunAtLoad` 自動開。
- 「開機時自動啟動」開關 = 這個 plist 是否存在並載入。
  關閉時只移除 plist（讓下次登入不再自動開），不會殺掉當前正在跑的程序。
"""

from __future__ import annotations

import os
import subprocess

LABEL = "com.user.claude-usage-statusbar"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LABEL}.plist")
APP_HOME = os.path.expanduser("~/Library/Application Support/claude-usage-statusbar")
LOG_DIR = os.path.expanduser("~/Library/Logs")


def _plist_contents() -> str:
    run_sh = os.path.join(APP_HOME, "run.sh")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        f"    <key>Label</key>\n    <string>{LABEL}</string>\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        "        <string>/bin/bash</string>\n"
        f"        <string>{run_sh}</string>\n"
        "    </array>\n"
        "    <key>RunAtLoad</key>\n    <true/>\n"
        "    <key>KeepAlive</key>\n    <false/>\n"
        "    <key>ProcessType</key>\n    <string>Interactive</string>\n"
        f"    <key>StandardOutPath</key>\n    <string>{LOG_DIR}/{LABEL}.log</string>\n"
        f"    <key>StandardErrorPath</key>\n    <string>{LOG_DIR}/{LABEL}.err.log</string>\n"
        "</dict>\n"
        "</plist>\n"
    )


def _write_plist() -> None:
    os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
    tmp = PLIST_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(_plist_contents())
    os.replace(tmp, PLIST_PATH)


def is_enabled() -> bool:
    """登入時是否會自動啟動（plist 是否存在）。"""
    return os.path.exists(PLIST_PATH)


def enable() -> None:
    """寫入/更新 plist 並向 launchd 註冊，使登入時自動啟動。

    只做 `load`（不 unload）：若 agent 已載入會是 no-op（被忽略），
    不會把目前正在跑的程序砍掉重啟；plist 內容變更於下次登入生效。
    （安裝/升級時的強制重載交由 install.sh 處理。）
    """
    _write_plist()
    _launchctl("load", PLIST_PATH)


def disable() -> None:
    """移除 plist，使下次登入不再自動啟動。不殺掉目前正在跑的程序。"""
    try:
        os.remove(PLIST_PATH)
    except (FileNotFoundError, OSError):
        pass


def sync_plist_file() -> None:
    """啟動時呼叫：若已啟用自動啟動，確保 plist 內容為最新（KeepAlive=false）。

    只重寫檔案、不重載，避免殺掉自己；變更於下次登入/重載生效。
    自舊版（KeepAlive=true）升級時，可確保 plist 檔已更新為 false。
    """
    if is_enabled():
        _write_plist()


def _launchctl(action: str, plist: str) -> None:
    try:
        subprocess.run(
            ["launchctl", action, plist],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass
