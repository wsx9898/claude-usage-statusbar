"""選單列「燃料量表」圖示。

以一個彩色形狀（依使用率變色）＋ 5 格 ▰▱ 量表（代表剩餘額度，越用越見底）表示狀態。
形狀可選方形 / 圓形 / 愛心（皆有完整四色 emoji）；≥90% 為純紅，不閃爍。

`worst` 為「最緊張的那個窗口」的使用百分比（0–100）。
`shape` 為形狀代號（square / circle / heart）。
"""

from __future__ import annotations

import math

_CELLS = 5

# 各形狀的四色階：[綠 <50, 黃 50–69, 橘 70–89, 紅 ≥90]
_TIERS: dict[str, list[str]] = {
    "square": ["🟩", "🟨", "🟧", "🟥"],
    "circle": ["🟢", "🟡", "🟠", "🔴"],
    "heart": ["💚", "💛", "🧡", "❤️"],
}
_EMPTY = "◽"  # 無資料時的佔位


def fuel_bar(worst: float) -> str:
    """以 ▰（剩餘）/◧（半格）/▱（已用）畫出 5 格量表。越用越見底。

    每格代表一個 20% 區段，再細分半格（10%）：該半段沒用完就不掉，未滿額至少留半格。
    """
    worst = max(0.0, float(worst))
    if worst >= 100:
        return "▱" * _CELLS
    remaining = 100.0 - worst
    halves = min(_CELLS * 2, max(1, math.ceil(remaining / 10.0)))  # 0–10 個半格
    full = halves // 2
    half = halves % 2
    return "▰" * full + ("◧" if half else "") + "▱" * (_CELLS - full - half)


def indicator(worst: float, has_data: bool, shape: str = "square") -> str:
    """依使用率回傳彩色形狀；≥90% 為純紅（不閃爍）。"""
    if not has_data:
        return _EMPTY
    tier = _TIERS.get(shape, _TIERS["square"])
    if worst >= 90:
        return tier[3]
    if worst >= 70:
        return tier[2]
    if worst >= 50:
        return tier[1]
    return tier[0]


def render(worst: float, has_data: bool, shape: str = "square") -> str:
    """組出「形狀＋量表」前綴，例如：🟩▰▰▰▰▱"""
    if not has_data:
        return indicator(worst, has_data, shape)
    return indicator(worst, has_data, shape) + fuel_bar(worst)
