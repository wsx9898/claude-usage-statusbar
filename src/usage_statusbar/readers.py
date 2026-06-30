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
    return CodexWindow(
        used_percent=float(d.get("used_percent", 0) or 0),
        window_minutes=int(d.get("window_minutes", 0) or 0),
        resets_at=int(d.get("resets_at", 0) or 0),
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


def read_all(use_official: bool = True) -> Snapshot:
    official = (
        claude_remote.fetch_official() if use_official else claude_remote.ClaudeOfficial()
    )
    return Snapshot(
        claude=read_claude_usage(),
        codex=read_codex_usage(),
        claude_official=official,
    )
