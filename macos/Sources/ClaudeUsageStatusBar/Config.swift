// 讀取 / 寫入使用者設定檔。
//
// 設定檔位置：~/.config/claude-usage-statusbar/config.json（可選）。
// 與 Python（Windows）版共用同一格式；寫回時保留檔案中既有的未知鍵。

import Foundation

enum Shape: String, CaseIterable {
    case square, circle, heart

    var next: Shape {
        let all = Shape.allCases
        return all[(all.firstIndex(of: self)! + 1) % all.count]
    }
}

struct Config {
    // UI 刷新間隔（讀本機檔＋重繪）。本機掃描有 mtime 快取、成本極低，可以開高頻率。
    var refreshSeconds = 20
    // 官方 API 抓取的最小間隔：refresh 再頻繁，打 API 也不會比這個密。
    var officialRefreshSeconds = 60
    var claude5hTokenLimit = 0
    var claudeWeeklyTokenLimit = 0
    // 是否讀取 Claude 官方用量（重用 Keychain token，與 /usage 一致）。
    var useOfficialClaude = true
    // 量表（顏色/能量條）與標題要納入哪些工具。Codex 預設關閉。
    var showClaude = true
    var showCodex = false
    var language: Lang = .zh
    var shape: Shape = .square

    static let dir = FileManager.default.homeDirectoryForCurrentUser
        .appendingPathComponent(".config/claude-usage-statusbar")
    static let path = dir.appendingPathComponent("config.json")

    static func load() -> Config {
        var cfg = Config()
        guard let data = try? Data(contentsOf: path),
              let user = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else { return cfg }

        if let v = intValue(user["refresh_seconds"]) { cfg.refreshSeconds = max(10, v) }
        if let v = intValue(user["official_refresh_seconds"]) { cfg.officialRefreshSeconds = max(30, v) }
        if let v = intValue(user["claude_5h_token_limit"]) { cfg.claude5hTokenLimit = v }
        if let v = intValue(user["claude_weekly_token_limit"]) { cfg.claudeWeeklyTokenLimit = v }
        if let v = user["use_official_claude"] as? Bool { cfg.useOfficialClaude = v }
        if let v = user["show_claude"] as? Bool { cfg.showClaude = v }
        if let v = user["show_codex"] as? Bool { cfg.showCodex = v }
        if let v = user["language"] as? String { cfg.language = v.lowercased() == "en" ? .en : .zh }
        if let v = user["shape"] as? String { cfg.shape = Shape(rawValue: v.lowercased()) ?? .square }
        return cfg
    }

    var dictionary: [String: Any] {
        [
            "refresh_seconds": refreshSeconds,
            "official_refresh_seconds": officialRefreshSeconds,
            "claude_5h_token_limit": claude5hTokenLimit,
            "claude_weekly_token_limit": claudeWeeklyTokenLimit,
            "use_official_claude": useOfficialClaude,
            "show_claude": showClaude,
            "show_codex": showCodex,
            "language": language.rawValue,
            "shape": shape.rawValue,
        ]
    }

    /// 把目前設定寫回設定檔。保留檔案中既有的未知鍵，只覆蓋已知鍵。
    func save() throws {
        var data: [String: Any] = [:]
        if let raw = try? Data(contentsOf: Config.path),
           let existing = (try? JSONSerialization.jsonObject(with: raw)) as? [String: Any] {
            data = existing
        }
        data.merge(dictionary) { _, new in new }
        try FileManager.default.createDirectory(at: Config.dir, withIntermediateDirectories: true)
        var out = try JSONSerialization.data(
            withJSONObject: data, options: [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes])
        out.append(0x0A)
        try out.write(to: Config.path, options: .atomic)
    }

    /// 設定檔不存在時寫入一份預設值（供「開啟設定檔位置」使用）。
    static func ensureExists() {
        guard !FileManager.default.fileExists(atPath: path.path) else { return }
        try? Config().save()
    }

    private static func intValue(_ v: Any?) -> Int? {
        if let n = v as? NSNumber, !(v is Bool) { return n.intValue }
        if let s = v as? String { return Int(s) }
        return nil
    }
}
