"""選單列「燃料量表」圖示。

以一個彩色方塊（依使用率變色）＋ 5 格 ▰▱ 量表（代表剩餘額度，越用越見底）表示狀態。
快到額度（≥90%）時方塊會閃爍，營造像 Running Cat 般的小動畫。

`worst` 為「最緊張的那個窗口」的使用百分比（0–100）。
`phase` 為動畫相位（0/1），由上層的動畫定時器切換。
"""

from __future__ import annotations

_CELLS = 5


def fuel_bar(worst: float) -> str:
    """以 ▰（剩餘）/▱（已用）畫出 5 格量表。越用越見底。"""
    worst = max(0.0, float(worst))
    if worst >= 100:
        filled = 0
    else:
        remaining = 100.0 - worst
        filled = max(1, round(remaining / 20.0))  # 每格 20%；未滿額至少留 1 格
    filled = min(_CELLS, filled)
    return "▰" * filled + "▱" * (_CELLS - filled)


def indicator(worst: float, phase: int, has_data: bool) -> str:
    """依使用率回傳彩色方塊；臨界時隨 phase 閃爍。"""
    if not has_data:
        return "◽"
    if worst >= 90:
        return "🟥" if phase == 0 else "⬜"  # 閃爍
    if worst >= 70:
        return "🟧"
    if worst >= 50:
        return "🟨"
    return "🟩"


def render(worst: float, phase: int, has_data: bool) -> str:
    """組出「方塊＋量表」前綴，例如：🟩▰▰▰▰▱"""
    if not has_data:
        return indicator(worst, phase, has_data)
    return indicator(worst, phase, has_data) + fuel_bar(worst)
