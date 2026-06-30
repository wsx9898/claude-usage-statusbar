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
    "refresh_seconds": 60,
    "claude_5h_token_limit": 0,
    "claude_weekly_token_limit": 0,
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
        cfg["refresh_seconds"] = max(15, int(cfg["refresh_seconds"]))
    except (TypeError, ValueError):
        cfg["refresh_seconds"] = 60
    return cfg
