// 讀取本機快取檔，彙整 Claude Code 與 Codex 的用量；並整合 Claude 官方用量。
//
// - Claude 估算：~/.claude/projects/*/*.jsonl 的 message.usage（依 mtime 快取逐檔解析結果）
// - Codex：~/.codex/sessions/**/rollout-*.jsonl 最新 token_count 事件的 rate_limits

import Foundation

struct ClaudeUsage {
    var ok = false
    var tokens5h = 0
    var tokens7d = 0
    var cost5h = 0.0
    var cost7d = 0.0
    var error = ""
}

struct CodexWindow {
    var usedPercent = 0.0
    var windowMinutes = 0
    var resetsAt = 0
}

struct CodexUsage {
    var ok = false
    var planType = ""
    var primary: CodexWindow?  // 5 小時窗
    var secondary: CodexWindow?  // 每週窗
    var updatedAt = 0.0
    var error = ""
}

struct Snapshot {
    var claude = ClaudeUsage()
    var codex = CodexUsage()
    // Claude 官方用量（與 /usage 一致）；未啟用或失敗時 ok=false，改用 claude 估算
    var claudeOfficial = ClaudeOfficial()
}

/// 所有可變狀態（檔案快取、校準點、官方快取）都只在 `queue` 上存取。
final class UsageReader: @unchecked Sendable {
    let queue = DispatchQueue(label: "claude-usage-statusbar.reader", qos: .utility)

    private let fm = FileManager.default
    private let claudeProjects: URL
    private let codexSessions: URL
    private let remote = ClaudeRemote()

    private static let fiveHours = 5.0 * 3600
    private static let sevenDays = 7.0 * 24 * 3600

    private struct ClaudeRecord {
        let ts: Double
        let tokens: Int
        let cost: Double
        let key: String?
    }

    // path -> (mtime, records)；只在 mtime 變動時重讀
    private var claudeFileCache: [String: (Date, [ClaudeRecord])] = [:]
    // path -> (mtime, (rate_limits, ts)?)
    private var codexFileCache: [String: (Date, ([String: Any], Double)?)] = [:]
    // 官方→本機 token 的校準點：官方% 對應的本機 token 量
    private var calib5: (pct: Double, tok: Double)?
    private var calib7: (pct: Double, tok: Double)?

    init() {
        let home = fm.homeDirectoryForCurrentUser
        claudeProjects = home.appendingPathComponent(".claude/projects")
        codexSessions = home.appendingPathComponent(".codex/sessions")
    }

    func readAll(useOfficial: Bool, force: Bool, officialInterval: Double) -> Snapshot {
        var official = useOfficial
            ? remote.fetch(force: force, minInterval: officialInterval)
            : ClaudeOfficial()
        let claude = readClaude()
        official = projectOfficial(official, claude)
        return Snapshot(claude: claude, codex: readCodex(), claudeOfficial: official)
    }

    // MARK: - Claude Code

    private func readClaude() -> ClaudeUsage {
        let now = Date().timeIntervalSince1970
        let cutoff7d = now - Self.sevenDays
        let cutoff5h = now - Self.fiveHours
        var result = ClaudeUsage()

        guard isDirectory(claudeProjects) else {
            result.error = "找不到 ~/.claude/projects"
            return result
        }
        let files = jsonlFiles(in: claudeProjects)
        guard !files.isEmpty else {
            result.error = "尚無 Claude 工作階段紀錄"
            return result
        }

        var foundAny = false
        var seen = Set<String>()
        var seenMsgs = Set<String>()  // 跨檔去重（同一則訊息可能出現在多個 jsonl）
        for url in files {
            guard let mtime = modificationDate(url) else { continue }
            // 只看 7 天內有更新過的檔案，省去掃描歷史檔
            if mtime.timeIntervalSince1970 < cutoff7d { continue }
            let path = url.path
            seen.insert(path)

            let recs: [ClaudeRecord]
            if let c = claudeFileCache[path], c.0 == mtime {
                recs = c.1
            } else {
                recs = parseClaudeFile(url)
                claudeFileCache[path] = (mtime, recs)
            }

            for r in recs where r.ts >= cutoff7d {
                if let key = r.key {
                    if seenMsgs.contains(key) { continue }
                    seenMsgs.insert(key)
                }
                foundAny = true
                result.tokens7d += r.tokens
                result.cost7d += r.cost
                if r.ts >= cutoff5h {
                    result.tokens5h += r.tokens
                    result.cost5h += r.cost
                }
            }
        }

        // 清掉已不在掃描範圍（超過 7 天或已刪除）的快取，避免無限成長
        claudeFileCache = claudeFileCache.filter { seen.contains($0.key) }

        result.ok = foundAny
        if !foundAny { result.error = "7 天內無 Claude 用量" }
        return result
    }

    /// ~/.claude/projects/*/*.jsonl
    private func jsonlFiles(in root: URL) -> [URL] {
        let dirs = (try? fm.contentsOfDirectory(at: root, includingPropertiesForKeys: nil)) ?? []
        return dirs.flatMap { dir -> [URL] in
            let items = (try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []
            return items.filter { $0.pathExtension == "jsonl" }
        }
    }

    /// 解析單一 jsonl。去重鍵 = requestId:message.id。
    private func parseClaudeFile(_ url: URL) -> [ClaudeRecord] {
        var recs: [ClaudeRecord] = []
        forEachLine(url, containing: "\"usage\"") { rec in
            guard let msg = rec["message"] as? [String: Any],
                  let usage = msg["usage"] as? [String: Any],
                  let ts = parseISO8601(rec["timestamp"] as? String)
            else { return }
            let tokens = num(usage["input_tokens"]) + num(usage["output_tokens"])
                + num(usage["cache_creation_input_tokens"]) + num(usage["cache_read_input_tokens"])
            var key: String?
            if let req = rec["requestId"] as? String, !req.isEmpty,
               let mid = msg["id"] as? String, !mid.isEmpty {
                key = "\(req):\(mid)"
            }
            recs.append(ClaudeRecord(
                ts: ts,
                tokens: Int(tokens),
                cost: Pricing.estimateCost(model: msg["model"] as? String, usage: usage),
                key: key
            ))
        }
        return recs
    }

    // MARK: - Codex

    private func readCodex() -> CodexUsage {
        var result = CodexUsage()
        guard isDirectory(codexSessions) else {
            result.error = "找不到 ~/.codex/sessions"
            return result
        }

        let newest = newestCodexFiles(limit: 6)
        // 只保留最近掃過的檔案，避免快取無限成長
        if codexFileCache.count > 32 {
            let keep = Set(newest.map(\.path))
            codexFileCache = codexFileCache.filter { keep.contains($0.key) }
        }

        for url in newest {
            guard let (rl, ts) = extractRateLimits(url) else { continue }
            result.ok = true
            result.planType = rl["plan_type"] as? String ?? ""
            result.primary = toWindow(rl["primary"])
            result.secondary = toWindow(rl["secondary"])
            result.updatedAt = ts
            return result
        }
        result.error = "尚無 Codex 用量限制資料"
        return result
    }

    private func newestCodexFiles(limit: Int) -> [URL] {
        guard let e = fm.enumerator(
            at: codexSessions, includingPropertiesForKeys: [.contentModificationDateKey])
        else { return [] }
        var files: [(URL, Date)] = []
        for case let url as URL in e {
            let name = url.lastPathComponent
            guard name.hasPrefix("rollout-"), name.hasSuffix(".jsonl") else { continue }
            files.append((url, modificationDate(url) ?? .distantPast))
        }
        return files.sorted { $0.1 > $1.1 }.prefix(limit).map(\.0)
    }

    /// 檔案中最後一個含 rate_limits 的 token_count 事件（依 mtime 快取）。
    private func extractRateLimits(_ url: URL) -> ([String: Any], Double)? {
        guard let mtime = modificationDate(url) else { return nil }
        if let c = codexFileCache[url.path], c.0 == mtime { return c.1 }

        var last: [String: Any]?
        var lastTs = 0.0
        forEachLine(url, containing: "\"rate_limits\"") { rec in
            guard let payload = rec["payload"] as? [String: Any],
                  payload["type"] as? String == "token_count",
                  let rl = payload["rate_limits"] as? [String: Any]
            else { return }
            last = rl
            lastTs = parseISO8601(rec["timestamp"] as? String) ?? lastTs
        }
        let found = last.map { ($0, lastTs) }
        codexFileCache[url.path] = (mtime, found)
        return found
    }

    private func toWindow(_ v: Any?) -> CodexWindow? {
        guard let d = v as? [String: Any] else { return nil }
        let resetsAt = Int(num(d["resets_at"]))
        var used = num(d["used_percent"])
        // 視窗過了重置時間就視為已重置：不會被陳舊的 100% 卡住。
        if resetsAt != 0 && Date().timeIntervalSince1970 >= Double(resetsAt) { used = 0 }
        return CodexWindow(usedPercent: used, windowMinutes: Int(num(d["window_minutes"])), resetsAt: resetsAt)
    }

    // MARK: - 官方值推估

    /// 官方失敗時，用最新快取＋本機新增用量推估百分比；官方成功時則重新校準。
    private func projectOfficial(_ o: ClaudeOfficial, _ c: ClaudeUsage) -> ClaudeOfficial {
        guard o.ok else { return o }  // 冷啟動且無快取：交由上層退回估算

        if !o.stale {
            // 拿到真正的官方值：記下校準點（需百分比與 token 皆 > 0 才可靠）
            if c.ok && c.tokens5h > 0 && o.fiveHourPct > 0 { calib5 = (o.fiveHourPct, Double(c.tokens5h)) }
            if c.ok && c.tokens7d > 0 && o.weeklyPct > 0 { calib7 = (o.weeklyPct, Double(c.tokens7d)) }
            return o
        }
        guard c.ok else { return o }  // 沒有本機資料可推估，維持快取值

        var out = o
        out.fiveHourPct = projectOne(o.fiveHourPct, o.fiveHourReset, c.tokens5h, calib5)
        out.weeklyPct = projectOne(o.weeklyPct, o.weeklyReset, c.tokens7d, calib7)
        out.projected = out.fiveHourPct != o.fiveHourPct || out.weeklyPct != o.weeklyPct
        return out
    }

    /// 快取% + 自校準點以來新增 token × (校準%/校準token)。過了重置時間強制歸零。
    private func projectOne(_ cachedPct: Double, _ resetAt: Int, _ tokensNow: Int,
                            _ calib: (pct: Double, tok: Double)?) -> Double {
        if resetAt != 0 && Date().timeIntervalSince1970 >= Double(resetAt) { return 0 }
        guard let calib, calib.pct > 0, calib.tok > 0 else { return cachedPct }
        let delta = max(0, Double(tokensNow) - calib.tok)
        return min(100, cachedPct + delta * calib.pct / calib.tok)
    }

    // MARK: - 檔案小工具

    private func isDirectory(_ url: URL) -> Bool {
        var isDir: ObjCBool = false
        return fm.fileExists(atPath: url.path, isDirectory: &isDir) && isDir.boolValue
    }

    private func modificationDate(_ url: URL) -> Date? {
        (try? fm.attributesOfItem(atPath: url.path))?[.modificationDate] as? Date
    }

    /// 逐行讀 jsonl，只對含 `needle` 的行做 JSON 解析（大幅減少解析量）。
    private func forEachLine(_ url: URL, containing needle: String, _ body: ([String: Any]) -> Void) {
        guard let data = try? Data(contentsOf: url, options: .mappedIfSafe) else { return }
        let needleData = Data(needle.utf8)
        var start = data.startIndex
        while start < data.endIndex {
            let end = data[start...].firstIndex(of: 0x0A) ?? data.endIndex
            let line = data[start..<end]
            if !line.isEmpty, line.range(of: needleData) != nil,
               let rec = (try? JSONSerialization.jsonObject(with: line)) as? [String: Any] {
                body(rec)
            }
            start = end < data.endIndex ? data.index(after: end) : end
        }
    }
}
