// 極簡中英文字串表。用法：`L.t("key", ["n": "3"])`；切換語言：`L.lang = .en`。

import Foundation

enum Lang: String {
    case zh, en
}

enum L {
    nonisolated(unsafe) static var lang: Lang = .zh

    private static let strings: [String: (zh: String, en: String)] = [
        // 選單（靜態）
        "menu_show_claude": ("顯示 Claude", "Show Claude"),
        "menu_show_codex": ("顯示 Codex", "Show Codex"),
        "menu_autostart": ("開機時自動啟動", "Start at login"),
        "menu_refresh": ("立即重新整理", "Refresh now"),
        "menu_open_config": ("開啟設定檔位置", "Open config location"),
        "menu_quit": ("結束（永久關閉）", "Quit (permanent)"),
        // 語言切換項：顯示「切換到的目標語言」
        "menu_lang": ("切換語言：English", "切換語言 / Language：中文"),
        // 圖示形狀（點擊循環切換）
        "menu_shape": ("圖示形狀", "Icon shape"),
        "shape_square": ("方形", "Square"),
        "shape_circle": ("圓形", "Circle"),
        "shape_heart": ("愛心", "Heart"),
        // 標題列
        "title_loading": ("AI …", "AI …"),
        "title_no_data": ("AI 無資料", "AI no data"),
        // 明細欄位標籤
        "lbl_5h": ("5 小時", "5h"),
        "lbl_weekly": ("每週", "Weekly"),
        "lbl_monthly": ("每月", "Monthly"),
        "lbl_window_h": ("{h} 小時窗", "{h}h window"),
        "lbl_window_d": ("{d} 天窗", "{d}d window"),
        "lbl_est": ("估算", "Estimate"),
        "lbl_plan": ("方案", "Plan"),
        "lbl_updated": ("更新時間", "Updated"),
        "colon": ("：", ": "),
        "dash": ("—", "—"),
        "no_data": ("無資料", "no data"),
        // 官方數字來源標註
        "tag_official": ("（官方）", " (official)"),
        "tag_official_cache": ("（官方·快取）", " (official·cached)"),
        "tag_official_proj": ("（官方·推估中）", " (official·projected)"),
        // 估算字串
        "est_line": ("估算：5h {t5}/{c5} · 7d {t7}/{c7}", "Estimate: 5h {t5}/{c5} · 7d {t7}/{c7}"),
        "tokens_est": ("{n} tokens（估算）", "{n} tokens (est.)"),
        "pct_est": ("{p}（估算）", "{p} (est.)"),
        "official_unavailable": ("官方數字不可用（{reason}）", "official unavailable ({reason})"),
        // 重置時間（Fmt.reset 使用）
        "reset_soon": ("即將重置", "resetting soon"),
        "reset_days": ("{d} 天 {h} 小時後重置", "resets in {d}d {h}h"),
        "reset_hours": ("{h} 小時 {m} 分後重置", "resets in {h}h {m}m"),
        "reset_mins": ("{m} 分後重置", "resets in {m}m"),
    ]

    static func t(_ key: String, _ args: [String: CustomStringConvertible] = [:]) -> String {
        guard let entry = strings[key] else { return key }
        var s = lang == .en ? entry.en : entry.zh
        for (k, v) in args {
            s = s.replacingOccurrences(of: "{\(k)}", with: v.description)
        }
        return s
    }

    /// 依視窗長度給出合適標籤（Codex 各方案的窗長不同）。
    static func codexWindowLabel(_ windowMinutes: Int) -> String {
        let m = windowMinutes
        if m <= 360 { return t("lbl_5h") }  // ≤6 小時（含未知 0）
        if (9000...11000).contains(m) { return t("lbl_weekly") }  // ~7 天
        if (40000...46000).contains(m) { return t("lbl_monthly") }  // ~30 天
        if m < 1440 { return t("lbl_window_h", ["h": Int((Double(m) / 60).rounded())]) }
        return t("lbl_window_d", ["d": Int((Double(m) / 1440).rounded())])
    }
}
