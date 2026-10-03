// 讀取 Claude 官方用量（與 `claude /usage` 同源）。
//
// 做法：重用 Claude Code 已登入、存在 Keychain 的 OAuth token，呼叫 Claude Code 內部
// 用來查 /usage 的同一個端點：GET https://api.anthropic.com/api/oauth/usage
//
// 設計原則（穩定優先）：
// - 只「讀取」既有 token，不自行刷新、不寫回 Keychain（避免與 Claude Code 衝突）。
// - Keychain 透過系統 `security` 指令讀取（與舊 Python 版相同）：使用者先前對
//   `security` 按過的「一律允許」可直接沿用，重新編譯 App 也不會再次跳授權窗。
// - 任何失敗都回傳 ok=false 或沿用上次成功值（stale），由上層退回本機估算。
//
// 注意：此端點為 Claude Code 內部 API，非公開文件；改版時會自動 fallback，不致崩潰。

import Foundation

struct ClaudeOfficial {
    var ok = false
    var fiveHourPct = 0.0
    var weeklyPct = 0.0
    var fiveHourReset = 0  // epoch 秒
    var weeklyReset = 0
    var plan = ""
    var error = ""
    var stale = false  // 上次成功的快取值（本次取用官方失敗，例如 429）
    var projected = false  // 在快取值上疊加了本機用量推估（尚未校正）
    var updatedAt = 0.0  // 這份官方數字最後一次成功抓取的時間
}

/// 非執行緒安全：只在 UsageReader 的序列佇列上使用。
final class ClaudeRemote {
    private static let keychainService = "Claude Code-credentials"
    private static let usageURL = URL(string: "https://api.anthropic.com/api/oauth/usage")!
    private static let failCooldown = 120.0  // 秒

    // 上一次成功的官方數字；取用失敗時沿用，避免閃回估算/變色。
    private var lastGood: ClaudeOfficial?
    // 失敗後的冷卻：在此時間前不再打網路，直接回快取，少踩 429。
    private var cooldownUntil = 0.0

    /// 抓取官方用量。force=true（手動重新整理）時忽略節流/冷卻，強制重打。
    /// minInterval：兩次成功抓取之間的最小間隔秒數，間隔內直接沿用上次官方值。
    func fetch(force: Bool, minInterval: Double) -> ClaudeOfficial {
        let now = Date().timeIntervalSince1970
        if !force {
            if let g = lastGood, now - g.updatedAt < minInterval {
                return cached("間隔內（沿用上次官方值）")
            }
            if now < cooldownUntil {
                return cached("冷卻中（沿用上次官方值）")
            }
        }

        guard let oauth = Self.readOAuth() else { return cached("讀不到 Claude 憑證（Keychain）") }
        guard let token = oauth["accessToken"] as? String, !token.isEmpty else {
            return cached("憑證缺少 accessToken")
        }
        // 憑證已明確過期：打了必是 401，直接沿用快取，等 Claude Code 下次刷新 token。
        if !force, let exp = oauth["expiresAt"] as? NSNumber, exp.doubleValue / 1000 < now {
            return cached("token 已過期（等待 Claude Code 刷新）")
        }

        var req = URLRequest(url: Self.usageURL, timeoutInterval: 10)
        req.httpMethod = "GET"
        req.setValue("oauth-2025-04-20", forHTTPHeaderField: "anthropic-beta")
        req.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        req.setValue("claude-usage-statusbar", forHTTPHeaderField: "User-Agent")
        req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")

        let (data, response, error) = Self.syncRequest(req)
        if let error {
            cooldownUntil = Date().timeIntervalSince1970 + Self.failCooldown
            return cached("連線失敗：\(error.localizedDescription)")
        }
        if let http = response as? HTTPURLResponse, !(200..<300).contains(http.statusCode) {
            let code = http.statusCode
            // 429（限流）/ 5xx / 401（token 過期）：進入冷卻並沿用上次官方值。
            if code == 401 || code == 429 || code >= 500 {
                cooldownUntil = Date().timeIntervalSince1970 + Self.failCooldown
            }
            return cached("API 回應 \(code)")
        }
        guard let data, let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] else {
            return cached("回應格式無法解析")
        }

        let fh = json["five_hour"] as? [String: Any] ?? [:]
        let sd = json["seven_day"] as? [String: Any] ?? [:]
        let fhReset = Int(parseISO8601(fh["resets_at"] as? String) ?? 0)
        let sdReset = Int(parseISO8601(sd["resets_at"] as? String) ?? 0)
        let result = ClaudeOfficial(
            ok: true,
            fiveHourPct: Self.util(num(fh["utilization"]), fhReset),
            weeklyPct: Self.util(num(sd["utilization"]), sdReset),
            fiveHourReset: fhReset,
            weeklyReset: sdReset,
            plan: oauth["subscriptionType"] as? String ?? "",
            updatedAt: Date().timeIntervalSince1970
        )
        lastGood = result
        cooldownUntil = 0  // 成功即解除冷卻
        return result
    }

    /// 取用官方失敗時：有上次成功值就沿用（標記 stale），否則回錯誤。
    /// 沿用時仍重新套用 util，使視窗過了重置時間會自動歸零。
    private func cached(_ error: String) -> ClaudeOfficial {
        guard let g = lastGood else { return ClaudeOfficial(error: error) }
        var o = g
        o.fiveHourPct = Self.util(g.fiveHourPct, g.fiveHourReset)
        o.weeklyPct = Self.util(g.weeklyPct, g.weeklyReset)
        o.error = error
        o.stale = true
        return o
    }

    /// 視窗一旦過了重置時間就視為已重置（歸零），避免被陳舊數字卡住。
    private static func util(_ pct: Double, _ resetAt: Int) -> Double {
        if resetAt != 0 && Date().timeIntervalSince1970 >= Double(resetAt) { return 0 }
        return pct
    }

    /// 用 `security` 讀出 Keychain 中的 claudeAiOauth 區塊。失敗回 nil。
    private static func readOAuth() -> [String: Any]? {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/usr/bin/security")
        p.arguments = ["find-generic-password", "-s", keychainService, "-w"]
        let out = Pipe()
        p.standardOutput = out
        p.standardError = FileHandle.nullDevice
        do { try p.run() } catch { return nil }

        // 逾時保護：10 秒內沒結束就終止（例如授權窗沒人理）
        let killer = DispatchWorkItem { if p.isRunning { p.terminate() } }
        DispatchQueue.global().asyncAfter(deadline: .now() + 10, execute: killer)
        let data = out.fileHandleForReading.readDataToEndOfFile()
        p.waitUntilExit()
        killer.cancel()

        guard p.terminationStatus == 0,
              let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
        else { return nil }
        return json["claudeAiOauth"] as? [String: Any]
    }

    private static func syncRequest(_ req: URLRequest) -> (Data?, URLResponse?, Error?) {
        let sem = DispatchSemaphore(value: 0)
        var result: (Data?, URLResponse?, Error?) = (nil, nil, nil)
        URLSession.shared.dataTask(with: req) { d, r, e in
            result = (d, r, e)
            sem.signal()
        }.resume()
        sem.wait()
        return result
    }
}
