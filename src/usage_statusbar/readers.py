"""讀取本機快取檔，彙整 Claude Code 與 Codex 的用量。

完全離線：只讀取 ~/.claude 與 ~/.codex 下的本機檔案，不發送任何網路請求。
"""

from __future__ import annotations

import glob
import json
import os
import time
from dataclasses import dataclass, field

from . import claude_remote, pricing

CLAUDE_PROJECTS = os.path.expanduser("~/.claude/projects")
CODEX_SESSIONS = os.path.expanduser("~/.codex/sessions")

FIVE_HOURS = 5 * 3600
SEVEN_DAYS = 7 * 24 * 3600


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------
@dataclass
class ClaudeUsage:
    ok: bool = False
    tokens_5h: int = 0
    tokens_7d: int = 0
    cost_5h: float = 0.0
    cost_7d: float = 0.0
    error: str = ""


def _parse_ts(ts: str) -> float | None:
    """解析 ISO8601 時間字串為 epoch 秒。"""
    if not ts:
        return None
    try:
        # 形如 2026-06-30T04:16:46.084Z
        from datetime import datetime, timezone

        s = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(s).timestamp()
    except (ValueError, TypeError):
        return None


def _usage_tokens(usage: dict) -> int:
    return (
        (usage.get("input_tokens", 0) or 0)
        + (usage.get("output_tokens", 0) or 0)
        + (usage.get("cache_creation_input_tokens", 0) or 0)
        + (usage.get("cache_read_input_tokens", 0) or 0)
    )


def read_claude_usage() -> ClaudeUsage:
    now = time.time()
    cutoff_7d = now - SEVEN_DAYS
    cutoff_5h = now - FIVE_HOURS
    result = ClaudeUsage()

    if not os.path.isdir(CLAUDE_PROJECTS):
        result.error = "找不到 ~/.claude/projects"
        return result

    files = glob.glob(os.path.join(CLAUDE_PROJECTS, "*", "*.jsonl"))
    if not files:
        result.error = "尚無 Claude 工作階段紀錄"
        return result

    found_any = False
    for path in files:
        try:
            # 只看 7 天內有更新過的檔案，省去掃描歷史檔
            if os.path.getmtime(path) < cutoff_7d:
                continue
        except OSError:
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or '"usage"' not in line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = rec.get("message")
                    if not isinstance(msg, dict):
                        continue
                    usage = msg.get("usage")
                    if not isinstance(usage, dict):
                        continue
                    ts = _parse_ts(rec.get("timestamp", ""))
                    if ts is None or ts < cutoff_7d:
                        continue

                    found_any = True
                    tokens = _usage_tokens(usage)
                    cost = pricing.estimate_cost(msg.get("model"), usage)

                    result.tokens_7d += tokens
                    result.cost_7d += cost
                    if ts >= cutoff_5h:
                        result.tokens_5h += tokens
                        result.cost_5h += cost
        except OSError:
            continue

    result.ok = found_any
    if not found_any:
        result.error = "7 天內無 Claude 用量"
    return result


# ---------------------------------------------------------------------------
# Codex
# ---------------------------------------------------------------------------
@dataclass
class CodexWindow:
    used_percent: float = 0.0
    window_minutes: int = 0
    resets_at: int = 0


@dataclass
class CodexUsage:
    ok: bool = False
    plan_type: str = ""
    primary: CodexWindow | None = None  # 5 小時窗
    secondary: CodexWindow | None = None  # 每週窗
    updated_at: float = 0.0
    error: str = ""


def _newest_codex_files(limit: int = 6) -> list[str]:
    files = glob.glob(os.path.join(CODEX_SESSIONS, "**", "rollout-*.jsonl"), recursive=True)
    files.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    return files[:limit]


def _extract_rate_limits(path: str) -> tuple[dict, float] | None:
    """回傳檔案中最後一個含 rate_limits 的 token_count 事件。"""
    last = None
    last_ts = 0.0
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if '"rate_limits"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = rec.get("payload", {})
                if payload.get("type") != "token_count":
                    continue
                rl = payload.get("rate_limits")
                if not isinstance(rl, dict):
                    continue
                last = rl
                last_ts = _parse_ts(rec.get("timestamp", "")) or last_ts
    except OSError:
        return None
    if last is None:
        return None
    return last, last_ts


def _to_window(d: dict | None) -> CodexWindow | None:
    if not isinstance(d, dict):
        return None
    resets_at = int(d.get("resets_at", 0) or 0)
    used = float(d.get("used_percent", 0) or 0)
    # 視窗一旦過了重置時間就視為已重置：即使本機檔案沒有更新（很久沒用 Codex），
    # 也不會再被陳舊的 100% 卡住。
    if resets_at and time.time() >= resets_at:
        used = 0.0
    return CodexWindow(
        used_percent=used,
        window_minutes=int(d.get("window_minutes", 0) or 0),
        resets_at=resets_at,
    )


def read_codex_usage() -> CodexUsage:
    result = CodexUsage()
    if not os.path.isdir(CODEX_SESSIONS):
        result.error = "找不到 ~/.codex/sessions"
        return result

    for path in _newest_codex_files():
        found = _extract_rate_limits(path)
        if found is None:
            continue
        rl, ts = found
        result.ok = True
        result.plan_type = str(rl.get("plan_type", "") or "")
        result.primary = _to_window(rl.get("primary"))
        result.secondary = _to_window(rl.get("secondary"))
        result.updated_at = ts
        return result

    result.error = "尚無 Codex 用量限制資料"
    return result


# ---------------------------------------------------------------------------
# 整合
# ---------------------------------------------------------------------------
@dataclass
class Snapshot:
    claude: ClaudeUsage = field(default_factory=ClaudeUsage)
    codex: CodexUsage = field(default_factory=CodexUsage)
    # Claude 官方用量（與 /usage 一致）；未啟用或失敗時 ok=False，改用 claude 估算
    claude_official: claude_remote.ClaudeOfficial = field(
        default_factory=claude_remote.ClaudeOfficial
    )
    fetched_at: float = field(default_factory=time.time)


# 官方→本機 token 的校準狀態（程序記憶體內）。
# 每次官方成功時記下「官方% 對應的本機 token 量」，據此把後續本機新增用量換算成 %。
_calib: dict[str, float | None] = {"pct5": None, "tok5": None, "pct7": None, "tok7": None}


def _project_official(
    o: claude_remote.ClaudeOfficial, c: ClaudeUsage
) -> claude_remote.ClaudeOfficial:
    """官方失敗時，用最新快取＋本機新增用量推估百分比；官方成功時則重新校準。"""
    from dataclasses import replace

    if not o.ok:
        return o  # 冷啟動且無快取：交由上層退回估算

    if not o.stale:
        # 拿到真正的官方值：記下校準點（需百分比與 token 皆 > 0 才可靠）
        if c.ok and c.tokens_5h > 0 and o.five_hour_pct > 0:
            _calib["pct5"], _calib["tok5"] = o.five_hour_pct, c.tokens_5h
        if c.ok and c.tokens_7d > 0 and o.weekly_pct > 0:
            _calib["pct7"], _calib["tok7"] = o.weekly_pct, c.tokens_7d
        return o

    # 快取（stale）：疊加本機新增用量
    if not c.ok:
        return o  # 沒有本機資料可推估，維持快取值

    p5 = _project_one(
        o.five_hour_pct, o.five_hour_reset, c.tokens_5h, _calib["pct5"], _calib["tok5"]
    )
    p7 = _project_one(
        o.weekly_pct, o.weekly_reset, c.tokens_7d, _calib["pct7"], _calib["tok7"]
    )
    changed = p5 != o.five_hour_pct or p7 != o.weekly_pct
    return replace(o, five_hour_pct=p5, weekly_pct=p7, projected=changed)


def _project_one(
    cached_pct: float,
    reset_at: int,
    tokens_now: int,
    calib_pct: float | None,
    calib_tok: float | None,
) -> float:
    """推估單一視窗：快取% + 自校準點以來新增 token × (校準%/校準token)。

    視窗一旦過了重置時間，強制歸零、不疊加任何推估——「到點就歸零」優先於推估，
    因為重置後舊校準點已無意義，需等下次成功取得官方值才重新校準。
    """
    if reset_at and time.time() >= reset_at:
        return 0.0
    if not calib_pct or not calib_tok or calib_tok <= 0:
        return cached_pct
    ratio = calib_pct / calib_tok  # 每 token 對應的 %
    delta = max(0.0, float(tokens_now) - float(calib_tok))
    return min(100.0, cached_pct + delta * ratio)


def read_all(use_official: bool = True) -> Snapshot:
    official = (
        claude_remote.fetch_official() if use_official else claude_remote.ClaudeOfficial()
    )
    claude = read_claude_usage()
    official = _project_official(official, claude)
    return Snapshot(
        claude=claude,
        codex=read_codex_usage(),
        claude_official=official,
    )
