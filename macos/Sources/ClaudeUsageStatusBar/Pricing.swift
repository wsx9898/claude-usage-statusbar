// 模型計價表（每 100 萬 tokens 的美金價格）。
//
// 這些數字用於「估算」用量成本，並非帳單真實金額。官方計價可能調整，必要時請更新此表。

import Foundation

enum Pricing {
    // (子字串, input_per_mtok, output_per_mtok)；越靠前越優先。
    private static let prices: [(String, Double, Double)] = [
        ("claude-fable", 10.0, 50.0),
        ("claude-mythos", 10.0, 50.0),
        ("claude-opus-4-8", 5.0, 25.0),
        ("claude-opus-4-7", 5.0, 25.0),
        ("claude-opus-4-6", 5.0, 25.0),
        ("claude-opus-4-5", 5.0, 25.0),
        ("claude-opus-4-1", 15.0, 75.0),
        ("claude-opus-4", 15.0, 75.0),
        ("claude-opus", 15.0, 75.0),
        ("claude-sonnet-5", 3.0, 15.0),
        ("claude-sonnet-4-6", 3.0, 15.0),
        ("claude-sonnet-4-5", 3.0, 15.0),
        ("claude-sonnet-4", 3.0, 15.0),
        ("claude-sonnet", 3.0, 15.0),
        ("claude-haiku-4-5", 1.0, 5.0),
        ("claude-haiku-3-5", 0.8, 4.0),
        ("claude-haiku", 0.25, 1.25),
    ]

    // 快取定價倍率（相對 input 價格）：寫入依 TTL 分級（5 分鐘 1.25x、1 小時 2x）
    private static let cacheWrite5m = 1.25
    private static let cacheWrite1h = 2.0
    private static let cacheRead = 0.10

    private static let fallback = (5.0, 25.0)  // 未知模型先當 opus 級估算

    private static func rates(_ model: String?) -> (Double, Double) {
        guard let m = model?.lowercased(), !m.isEmpty else { return fallback }
        for (key, inp, out) in prices where m.contains(key) {
            return (inp, out)
        }
        return fallback
    }

    /// 快取寫入成本：優先用 cache_creation 明細（5m/1h 費率不同），否則整筆當 5m。
    private static func cacheWriteCost(_ usage: [String: Any], _ inp: Double) -> Double {
        if let detail = usage["cache_creation"] as? [String: Any] {
            return num(detail["ephemeral_5m_input_tokens"]) * inp * cacheWrite5m
                + num(detail["ephemeral_1h_input_tokens"]) * inp * cacheWrite1h
        }
        return num(usage["cache_creation_input_tokens"]) * inp * cacheWrite5m
    }

    /// 依單筆 usage 估算美金成本。
    static func estimateCost(model: String?, usage: [String: Any]) -> Double {
        let (inp, out) = rates(model)
        let cost = num(usage["input_tokens"]) * inp
            + num(usage["output_tokens"]) * out
            + cacheWriteCost(usage, inp)
            + num(usage["cache_read_input_tokens"]) * inp * cacheRead
        return cost / 1_000_000
    }
}
