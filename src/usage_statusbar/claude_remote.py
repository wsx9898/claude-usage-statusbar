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
import time
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
    stale: bool = False  # True 表示這是上次成功的快取值（本次取用官方失敗，例如 429）
    projected: bool = False  # True 表示在快取值上疊加了本機用量推估（尚未校正）
    updated_at: float = 0.0  # 這份官方數字最後一次成功抓取的時間（epoch 秒）


# 上一次成功的官方數字（程序記憶體內）；取用失敗時沿用，避免閃回估算/變色。
_last_good: ClaudeOfficial | None = None
# 失敗後的冷卻：在此時間前不再打網路，直接回快取，少踩 429。
_cooldown_until: float = 0.0
_FAIL_COOLDOWN = 120.0  # 秒


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


def _cached(error: str) -> ClaudeOfficial:
    """取用官方失敗時的回傳：有上次成功值就沿用（標記 stale），否則回錯誤。

    沿用時仍重新套用 `_util`，使視窗過了重置時間會自動歸零、不會卡在舊百分比。
    """
    if _last_good is None:
        return ClaudeOfficial(error=error)
    g = _last_good
    return ClaudeOfficial(
        ok=True,
        five_hour_pct=_util(g.five_hour_pct, g.five_hour_reset),
        weekly_pct=_util(g.weekly_pct, g.weekly_reset),
        five_hour_reset=g.five_hour_reset,
        weekly_reset=g.weekly_reset,
        plan=g.plan,
        error=error,
        stale=True,
        updated_at=g.updated_at,
    )


def fetch_official(force: bool = False, min_interval: float = 60.0) -> ClaudeOfficial:
    """抓取官方用量。force=True（手動重新整理）時忽略節流/冷卻，強制重打。

    min_interval：兩次成功抓取之間的最小間隔秒數。UI 的刷新頻率可以開得比它高，
    間隔內直接沿用上次官方值（配合本機推估），不會多打 API。
    """
    global _last_good, _cooldown_until

    now = time.time()
    if not force:
        # 成功值仍在最小間隔內：直接沿用，不打網路（讓 UI 高頻刷新不會轟炸 API）。
        if _last_good is not None and now - _last_good.updated_at < min_interval:
            return _cached("間隔內（沿用上次官方值）")
        # 失敗冷卻中：即使沒有快取值也不重打，避免啟動失敗後每個 tick 都連網。
        if now < _cooldown_until:
            return _cached("冷卻中（沿用上次官方值）")

    oauth = _read_oauth()
    if not oauth:
        return _cached("讀不到 Claude 憑證（Keychain）")

    token = oauth.get("accessToken")
    if not token:
        return _cached("憑證缺少 accessToken")

    # 憑證已明確過期：打了必是 401，直接沿用快取，等 Claude Code 下次刷新 token。
    expires_at = oauth.get("expiresAt")
    if not force and isinstance(expires_at, (int, float)) and expires_at / 1000.0 < now:
        return _cached("token 已過期（等待 Claude Code 刷新）")

    headers = dict(_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(USAGE_URL, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        # 429（限流）/ 5xx：進入冷卻並沿用上次官方值。
        # 401 代表 token 過期，重試也不會好，同樣冷卻，等 Claude Code 刷新 token。
        if e.code in (401, 429) or e.code >= 500:
            _cooldown_until = time.time() + _FAIL_COOLDOWN
        return _cached(f"API 回應 {e.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        _cooldown_until = time.time() + _FAIL_COOLDOWN
        return _cached(f"連線失敗：{e}")
    except json.JSONDecodeError:
        return _cached("回應格式無法解析")

    fh = data.get("five_hour") or {}
    sd = data.get("seven_day") or {}
    five_hour_reset = _parse_iso(fh.get("resets_at", ""))
    weekly_reset = _parse_iso(sd.get("resets_at", ""))
    result = ClaudeOfficial(
        ok=True,
        five_hour_pct=_util(fh.get("utilization"), five_hour_reset),
        weekly_pct=_util(sd.get("utilization"), weekly_reset),
        five_hour_reset=five_hour_reset,
        weekly_reset=weekly_reset,
        plan=str(oauth.get("subscriptionType", "") or ""),
        error="",
        stale=False,
        updated_at=time.time(),
    )
    _last_good = result
    _cooldown_until = 0.0  # 成功即解除冷卻
    return result


def _util(value, reset_at: int) -> float:
    """視窗一旦過了重置時間就視為已重置（歸零），避免被陳舊數字卡住。"""
    pct = float(value or 0)
    if reset_at and time.time() >= reset_at:
        return 0.0
    return pct
