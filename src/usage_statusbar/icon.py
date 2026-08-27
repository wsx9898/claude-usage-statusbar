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


# ---------------------------------------------------------------------------
# Windows 系統匣點陣圖（macOS 選單列可直接顯示文字，Windows 系統匣只吃圖示，
# 沒有等效的「文字標題」，所以用 Pillow 把顏色＋百分比畫成一張小圖）
# ---------------------------------------------------------------------------

# 各形狀的四色階（十六進位色碼版，對應 emoji 的顏色觀感）
_TIERS_RGB: dict[str, list[str]] = {
    "square": ["#3DD65C", "#FFD426", "#FF9F1A", "#FF3B30"],
    "circle": ["#34C759", "#FFCC00", "#FF9500", "#FF3B30"],
    "heart": ["#34C759", "#FFCC00", "#FF9500", "#FF3B30"],
}
_GRAY = "#9AA0A6"  # 無資料時的佔位色

_FONT_CANDIDATES = (
    "seguisb.ttf",  # Segoe UI Semibold（Windows 內建）
    "segoeuib.ttf",  # Segoe UI Bold
    "arialbd.ttf",  # Arial Bold
    "arial.ttf",
    "DejaVuSans-Bold.ttf",
)


def _tier_color(worst: float, shape: str) -> str:
    tiers = _TIERS_RGB.get(shape, _TIERS_RGB["square"])
    if worst >= 90:
        return tiers[3]
    if worst >= 70:
        return tiers[2]
    if worst >= 50:
        return tiers[1]
    return tiers[0]


def _load_font(size: int):
    from PIL import ImageFont

    for name in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_shape(draw, shape: str, box: tuple[int, int, int, int], color: str) -> None:
    x0, y0, x1, y1 = box
    if shape == "circle":
        draw.ellipse(box, fill=color)
    elif shape == "heart":
        w, h = x1 - x0, y1 - y0
        cx = (x0 + x1) / 2
        r = w / 4
        draw.ellipse((x0, y0, x0 + 2 * r, y0 + 2 * r), fill=color)
        draw.ellipse((x1 - 2 * r, y0, x1, y0 + 2 * r), fill=color)
        draw.polygon(
            [(x0, y0 + r), (cx, y1), (x1, y0 + r)],
            fill=color,
        )
    else:  # square（實際上畫成圓角矩形，比較耐看）
        radius = min(x1 - x0, y1 - y0) // 5
        draw.rounded_rectangle(box, radius=radius, fill=color)


def render_image(worst: float, has_data: bool, shape: str = "square", size: int = 64):
    """畫出系統匣用的彩色形狀＋百分比點陣圖，回傳 PIL.Image。"""
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(2, size // 16)
    box = (pad, pad, size - pad, size - pad)

    if not has_data:
        _draw_shape(draw, shape, box, _GRAY)
        text = "…"
    else:
        color = _tier_color(worst, shape)
        _draw_shape(draw, shape, box, color)
        pct = max(0, min(99, int(worst)))
        text = str(pct)

    font = _load_font(size // 2 if len(text) <= 2 else size // 3)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (size - tw) / 2 - bbox[0]
    ty = (size - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font, fill="#FFFFFF")
    return img
