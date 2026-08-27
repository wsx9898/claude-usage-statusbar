"""管理 Windows 的「開機（登入）時自動啟動」。

設計：
- Windows 沒有 macOS LaunchAgent 那一套，這裡改寫入
  `HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run`，
  這是每個使用者自己的登入啟動清單，不需要系統管理員權限。
- 「開機時自動啟動」開關 = 這個機碼值是否存在。
  關閉時只刪除機碼值（讓下次登入不再自動開），不會殺掉當前正在跑的程序。
- 啟動命令指向 `run_hidden.vbs`（用 wscript 隱藏視窗執行 `run_windows.bat`），
  避免登入時彈出一個閒置的命令提示字元視窗。
"""

from __future__ import annotations

import os
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "ClaudeUsageStatusBar"

# 專案根目錄：本檔案位於 <root>/src/usage_statusbar/，往上兩層即為 <root>
APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
VBS_PATH = os.path.join(APP_ROOT, "run_hidden.vbs")


def _command() -> str:
    return f'wscript.exe "{VBS_PATH}"'


def is_enabled() -> bool:
    """登入時是否會自動啟動（機碼值是否存在）。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
        return True
    except OSError:
        return False


def enable() -> None:
    """寫入登入啟動機碼值，使登入時自動啟動。"""
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, _command())
    except OSError:
        pass


def disable() -> None:
    """移除機碼值，使下次登入不再自動啟動。不殺掉目前正在跑的程序。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, VALUE_NAME)
    except OSError:
        pass


def sync_startup() -> None:
    """啟動時呼叫：若已啟用自動啟動，確保機碼值指向目前的專案路徑。

    專案資料夾若被搬動過，這裡會自動修正登入啟動指令。
    """
    if is_enabled():
        enable()
