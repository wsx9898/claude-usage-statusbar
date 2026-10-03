// 字串格式化工具與共用小工具。

import Foundation

enum Fmt {
    static func tokens(_ n: Int) -> String {
        if n >= 1_000_000 { return String(format: "%.1fM", Double(n) / 1_000_000) }
        if n >= 1_000 { return String(format: "%.1fK", Double(n) / 1_000) }
        return String(n)
    }

    static func cost(_ c: Double) -> String { String(format: "$%.2f", c) }

    static func pct(_ p: Double) -> String { String(format: "%.0f%%", p) }

    /// 以「剩餘時間」描述距離重置還有多久。
    static func reset(_ resetsAt: Int) -> String {
        guard resetsAt != 0 else { return "" }
        let remain = resetsAt - Int(Date().timeIntervalSince1970)
        if remain <= 0 { return L.t("reset_soon") }
        let hours = remain / 3600
        let minutes = (remain % 3600) / 60
        if hours >= 24 { return L.t("reset_days", ["d": hours / 24, "h": hours % 24]) }
        if hours >= 1 { return L.t("reset_hours", ["h": hours, "m": minutes]) }
        return L.t("reset_mins", ["m": minutes])
    }
}

/// 解析 ISO8601 時間字串（如 2026-06-30T04:16:46.084Z、…+00:00、含 6 位小數）為 epoch 秒。
func parseISO8601(_ s: String?) -> Double? {
    guard var str = s, !str.isEmpty else { return nil }
    // 先把小數秒拆出來，再交給不含小數的 formatter（避免各版本對小數位數的支援差異）
    var fraction = 0.0
    if let dot = str.firstIndex(of: "."), let tz = str[dot...].firstIndex(where: { $0 == "Z" || $0 == "+" || $0 == "-" }) {
        fraction = Double("0" + str[dot..<tz]) ?? 0
        str.removeSubrange(dot..<tz)
    } else if let dot = str.firstIndex(of: ".") {
        fraction = Double("0" + str[dot...]) ?? 0
        str.removeSubrange(dot...)
    }
    let f = ISO8601DateFormatter()
    f.formatOptions = [.withInternetDateTime]
    if let d = f.date(from: str) { return d.timeIntervalSince1970 + fraction }
    // 無時區：視為 UTC
    if let d = f.date(from: str + "Z") { return d.timeIntervalSince1970 + fraction }
    return nil
}

/// JSON 數值（NSNumber / 字串）轉 Double；缺值或格式不符回 0。
func num(_ v: Any?) -> Double {
    if let n = v as? NSNumber { return n.doubleValue }
    if let s = v as? String { return Double(s) ?? 0 }
    return 0
}
