"""字串格式化工具。"""

from __future__ import annotations

import time

from . import i18n


def fmt_tokens(n: int) -> str:
    n = int(n or 0)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_cost(c: float) -> str:
    return f"${c:.2f}"


def fmt_pct(p: float) -> str:
    return f"{p:.0f}%"


def fmt_reset(resets_at: int) -> str:
    """以「剩餘時間」描述距離重置還有多久。"""
    if not resets_at:
        return ""
    remain = int(resets_at - time.time())
    if remain <= 0:
        return i18n.t("reset_soon")
    hours, rem = divmod(remain, 3600)
    minutes = rem // 60
    if hours >= 24:
        days, h = divmod(hours, 24)
        return i18n.t("reset_days", d=days, h=h)
    if hours >= 1:
        return i18n.t("reset_hours", h=hours, m=minutes)
    return i18n.t("reset_mins", m=minutes)


def dot_for_percent(p: float) -> str:
    """依百分比給出燈號。"""
    if p >= 90:
        return "🔴"
    if p >= 70:
        return "🟠"
    return "🟢"
