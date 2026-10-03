// 選單列「燃料量表」圖示。
//
// 以一個彩色形狀（依使用率變色）＋ 5 格 ▰▱ 量表（代表剩餘額度，越用越見底）表示狀態。
// 形狀可選方形 / 圓形 / 愛心（皆有完整四色 emoji）；≥90% 為純紅，不閃爍。
// `worst` 為「最緊張的那個窗口」的使用百分比（0–100）。

import Foundation

enum Icon {
    private static let cells = 5

    // 各形狀的四色階：[綠 <50, 黃 50–69, 橘 70–89, 紅 ≥90]
    private static let tiers: [Shape: [String]] = [
        .square: ["🟩", "🟨", "🟧", "🟥"],
        .circle: ["🟢", "🟡", "🟠", "🔴"],
        .heart: ["💚", "💛", "🧡", "❤️"],
    ]
    private static let empty = "◽"  // 無資料時的佔位

    /// 以 ▰（剩餘）/◧（半格）/▱（已用）畫出 5 格量表。
    /// 每格代表一個 20% 區段，再細分半格（10%）：該半段沒用完就不掉，未滿額至少留半格。
    static func fuelBar(_ worst: Double) -> String {
        let w = max(0, worst)
        if w >= 100 { return String(repeating: "▱", count: cells) }
        let halves = min(cells * 2, max(1, Int(((100 - w) / 10).rounded(.up))))
        let full = halves / 2
        let half = halves % 2
        return String(repeating: "▰", count: full) + (half == 1 ? "◧" : "")
            + String(repeating: "▱", count: cells - full - half)
    }

    static func indicator(_ worst: Double, hasData: Bool, shape: Shape) -> String {
        guard hasData else { return empty }
        let tier = tiers[shape]!
        if worst >= 90 { return tier[3] }
        if worst >= 70 { return tier[2] }
        if worst >= 50 { return tier[1] }
        return tier[0]
    }

    /// 組出「形狀＋量表」前綴，例如：🟩▰▰▰▰▱
    static func render(_ worst: Double, hasData: Bool, shape: Shape) -> String {
        let ind = indicator(worst, hasData: hasData, shape: shape)
        return hasData ? ind + fuelBar(worst) : ind
    }
}
