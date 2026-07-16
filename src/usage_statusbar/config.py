"""讀取使用者設定檔。

設定檔位置：~/.config/claude-usage-statusbar/config.json（可選）
範例：
{
  "refresh_seconds": 60,
  "claude_5h_token_limit": 0,
  "claude_weekly_token_limit": 0
}

claude_*_token_limit 設為大於 0 時，會用該值換算 Claude 用量百分比；
設為 0（預設）則只顯示 token 數與估算成本。
"""

from __future__ import annotations

import json
import os

CONFIG_DIR = os.path.expanduser("~/.config/claude-usage-statusbar")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")

_DEFAULTS = {
    # UI 刷新間隔（讀本機檔＋重繪）。本機掃描有 mtime 快取、成本極低，可以開高頻率。
    "refresh_seconds": 20,
    # 官方 API 抓取的最小間隔：refresh 再頻繁，打 API 也不會比這個密。
    "official_refresh_seconds": 60,
    "claude_5h_token_limit": 0,
    "claude_weekly_token_limit": 0,
    # 是否讀取 Claude 官方用量（重用 Keychain token，與 /usage 一致）。
    # 設為 false 則只用本機估算、且不會觸發 Keychain 授權彈窗。
    "use_official_claude": True,
    # 量表（顏色/閃爍/能量條）與標題要納入哪些工具。
    # 預設只看 Claude；Codex 預設關閉（避免陳舊或已用滿的額度把燈號鎖成紅的）。
    # 想監看 Codex 時，把 show_codex 設為 true，或在選單列勾選。
    "show_claude": True,
    "show_codex": False,
    # 介面語言："zh"（中文）或 "en"（English）。
    "language": "zh",
    # 量表前方的指示形狀："square"（方形）/ "circle"（圓形）/ "heart"（愛心）。
    "shape": "square",
}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            user = json.load(f)
        if isinstance(user, dict):
            cfg.update({k: user[k] for k in user if k in _DEFAULTS})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    # 安全範圍處理
    try:
        cfg["refresh_seconds"] = max(10, int(cfg["refresh_seconds"]))
    except (TypeError, ValueError):
        cfg["refresh_seconds"] = 20
    try:
        cfg["official_refresh_seconds"] = max(30, int(cfg["official_refresh_seconds"]))
    except (TypeError, ValueError):
        cfg["official_refresh_seconds"] = 60
    cfg["show_claude"] = bool(cfg.get("show_claude", True))
    cfg["show_codex"] = bool(cfg.get("show_codex", False))
    cfg["language"] = "en" if str(cfg.get("language", "zh")).lower() == "en" else "zh"
    shape = str(cfg.get("shape", "square")).lower()
    cfg["shape"] = shape if shape in ("square", "circle", "heart") else "square"
    return cfg


def save_config(cfg: dict) -> None:
    """把目前設定寫回設定檔。保留檔案中既有的未知鍵，只覆蓋已知鍵。"""
    data: dict = {}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if isinstance(existing, dict):
            data = existing
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    for k in _DEFAULTS:
        if k in cfg:
            data[k] = cfg[k]
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, CONFIG_PATH)
