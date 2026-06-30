"""讀取 Claude 官方用量（與 `claude /usage` 同源）。

做法：重用 Claude Code 已登入、存在 macOS Keychain 的 OAuth token，
呼叫 Claude Code 內部用來查 /usage 的同一個端點：
    GET https://api.anthropic.com/api/oauth/usage

設計原則（穩定優先）：
- 只「讀取」既有 token，不自行刷新、不寫回 Keychain（避免與 Claude Code 衝突）。
  你持續使用 Claude Code 時，它會自動維持 token 新鮮。
- 任何失敗（讀不到憑證、token 過期 401、無網路…）都回傳 ok=False，
  由上層自動退回本機估算，最壞情況與「不接官方」時相同。

注意：此端點為 Claude Code 內部 API，非公開文件；Claude 改版時有機會變動，
屆時會自動 fallback，不致讓 App 崩潰。
"""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass

KEYCHAIN_SERVICE = "Claude Code-credentials"
USAGE_URL = "https://api.anthropic.com/api/oauth/usage"

_HEADERS = {
    "anthropic-beta": "oauth-2025-04-20",
    "anthropic-version": "2023-06-01",
    "User-Agent": "claude-usage-statusbar",
}


@dataclass
class ClaudeOfficial:
    ok: bool = False
    five_hour_pct: float = 0.0
    weekly_pct: float = 0.0
    five_hour_reset: int = 0  # epoch 秒
    weekly_reset: int = 0
    plan: str = ""
    error: str = ""


def _read_oauth() -> dict | None:
    """從 Keychain 取出 claudeAiOauth 區塊。失敗回 None。"""
    try:
        out = subprocess.run(
            ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
    oauth = data.get("claudeAiOauth")
    return oauth if isinstance(oauth, dict) else None


def _parse_iso(s: str) -> int:
    if not s:
        return 0
    try:
        from datetime import datetime

        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except (ValueError, TypeError):
        return 0


def fetch_official() -> ClaudeOfficial:
    oauth = _read_oauth()
    if not oauth:
        return ClaudeOfficial(error="讀不到 Claude 憑證（Keychain）")

    token = oauth.get("accessToken")
    if not token:
        return ClaudeOfficial(error="憑證缺少 accessToken")

    headers = dict(_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(USAGE_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        # 401 多半代表 token 過期，待 Claude Code 下次刷新即可恢復
        return ClaudeOfficial(error=f"API 回應 {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return ClaudeOfficial(error=f"連線失敗：{e}")
    except json.JSONDecodeError:
        return ClaudeOfficial(error="回應格式無法解析")

    fh = data.get("five_hour") or {}
    sd = data.get("seven_day") or {}
    return ClaudeOfficial(
        ok=True,
        five_hour_pct=float(fh.get("utilization") or 0),
        weekly_pct=float(sd.get("utilization") or 0),
        five_hour_reset=_parse_iso(fh.get("resets_at", "")),
        weekly_reset=_parse_iso(sd.get("resets_at", "")),
        plan=str(oauth.get("subscriptionType", "") or ""),
        error="",
    )
