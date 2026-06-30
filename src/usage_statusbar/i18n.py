"""極簡中英文字串表。

用法：`from . import i18n` 後呼叫 `i18n.t("key", **kwargs)`。
切換語言：`i18n.set_lang("en")`。預設中文（zh）。
"""

from __future__ import annotations

LANG = "zh"

_S: dict[str, dict[str, str]] = {
    # 選單（靜態）
    "menu_show_claude": {"zh": "顯示 Claude", "en": "Show Claude"},
    "menu_show_codex": {"zh": "顯示 Codex", "en": "Show Codex"},
    "menu_autostart": {"zh": "開機時自動啟動", "en": "Start at login"},
    "menu_refresh": {"zh": "立即重新整理", "en": "Refresh now"},
    "menu_open_config": {"zh": "開啟設定檔位置", "en": "Open config location"},
    "menu_quit": {"zh": "結束（永久關閉）", "en": "Quit (permanent)"},
    # 語言切換項：顯示「切換到的目標語言」
    "menu_lang": {"zh": "切換語言：English", "en": "切換語言 / Language：中文"},
    # 標題列
    "title_loading": {"zh": "AI …", "en": "AI …"},
    "title_no_data": {"zh": "AI 無資料", "en": "AI no data"},
    "read_error": {"zh": "讀取錯誤：{exc}", "en": "Read error: {exc}"},
    # 明細欄位標籤
    "lbl_5h": {"zh": "5 小時", "en": "5h"},
    "lbl_weekly": {"zh": "每週", "en": "Weekly"},
    "lbl_est": {"zh": "估算", "en": "Estimate"},
    "lbl_plan": {"zh": "方案", "en": "Plan"},
    "lbl_updated": {"zh": "更新時間", "en": "Updated"},
    "colon": {"zh": "：", "en": ": "},
    "dash": {"zh": "—", "en": "—"},
    "no_data": {"zh": "無資料", "en": "no data"},
    # 官方數字來源標註
    "tag_official": {"zh": "（官方）", "en": " (official)"},
    "tag_official_cache": {"zh": "（官方·快取）", "en": " (official·cached)"},
    "tag_official_proj": {"zh": "（官方·推估中）", "en": " (official·projected)"},
    # 估算字串
    "est_line": {
        "zh": "估算：5h {t5}/{c5} · 7d {t7}/{c7}",
        "en": "Estimate: 5h {t5}/{c5} · 7d {t7}/{c7}",
    },
    "tokens_est": {"zh": "{n} tokens（估算）", "en": "{n} tokens (est.)"},
    "pct_est": {"zh": "{p}（估算）", "en": "{p} (est.)"},
    "official_unavailable": {
        "zh": "官方數字不可用（{reason}）",
        "en": "official unavailable ({reason})",
    },
    # 重置時間（format.fmt_reset 使用）
    "reset_soon": {"zh": "即將重置", "en": "resetting soon"},
    "reset_days": {"zh": "{d} 天 {h} 小時後重置", "en": "resets in {d}d {h}h"},
    "reset_hours": {"zh": "{h} 小時 {m} 分後重置", "en": "resets in {h}h {m}m"},
    "reset_mins": {"zh": "{m} 分後重置", "en": "resets in {m}m"},
}


def set_lang(lang: str) -> None:
    global LANG
    LANG = lang if lang in ("zh", "en") else "zh"


def t(key: str, **kwargs) -> str:
    entry = _S.get(key)
    if not entry:
        return key
    s = entry.get(LANG) or entry.get("zh") or key
    return s.format(**kwargs) if kwargs else s
