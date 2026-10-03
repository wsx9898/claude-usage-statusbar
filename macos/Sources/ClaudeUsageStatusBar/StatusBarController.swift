// macOS 選單列（右上角）用量監看 App 的 UI 層。
//
// 定時在背景佇列讀檔 + 連網（UsageReader），完成後回主執行緒更新選單列標題與明細。

import AppKit

@MainActor
final class StatusBarController: NSObject {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let reader = UsageReader()
    private var cfg = Config.load()
    private var timer: Timer?

    // 明細項目（之後更新文字）
    private let claudeHeader = NSMenuItem(title: "Claude Code", action: nil, keyEquivalent: "")
    private let claude5h = NSMenuItem()
    private let claude7d = NSMenuItem()
    private let claudeEst = NSMenuItem()
    private let claudePlan = NSMenuItem()
    private let codexHeader = NSMenuItem(title: "Codex", action: nil, keyEquivalent: "")
    private let codex5h = NSMenuItem()
    private let codexWeek = NSMenuItem()
    private let codexPlan = NSMenuItem()
    private let updated = NSMenuItem()

    // 可點擊項目
    private lazy var toggleClaude = item(#selector(onToggleClaude))
    private lazy var toggleCodex = item(#selector(onToggleCodex))
    private lazy var toggleAutostart = item(#selector(onToggleAutostart))
    private lazy var shapeItem = item(#selector(onCycleShape))
    private lazy var langItem = item(#selector(onToggleLang))
    private lazy var refreshItem = item(#selector(onRefresh), key: "r")
    private lazy var openConfigItem = item(#selector(onOpenConfig))
    private lazy var quitItem = item(#selector(onQuit), key: "q")

    // 標題狀態快取（供切換形狀時重繪用，不重新讀檔/連網）
    private var worst = 0.0
    private var parts: [String] = []
    private var fetching = false

    override init() {
        super.init()
        L.lang = cfg.language
        Autostart.sync()

        statusItem.button?.title = L.t("title_loading")
        let menu = NSMenu()
        for i in [claudeHeader, claude5h, claude7d, claudeEst, claudePlan] { menu.addItem(i) }
        menu.addItem(.separator())
        for i in [codexHeader, codex5h, codexWeek, codexPlan] { menu.addItem(i) }
        menu.addItem(.separator())
        for i in [updated, toggleClaude, toggleCodex, toggleAutostart, shapeItem, langItem,
                  refreshItem, openConfigItem] { menu.addItem(i) }
        menu.addItem(.separator())
        menu.addItem(quitItem)
        statusItem.menu = menu

        let dash = L.t("dash")
        for (i, key) in [(claude5h, "lbl_5h"), (claude7d, "lbl_weekly"), (claudeEst, "lbl_est"),
                         (claudePlan, "lbl_plan"), (codex5h, "lbl_5h"), (codexWeek, "lbl_weekly"),
                         (codexPlan, "lbl_plan")] {
            i.title = line(key, dash)
        }
        updated.title = L.t("lbl_updated") + L.t("colon") + dash
        applyMenuLanguage()
        toggleClaude.state = cfg.showClaude ? .on : .off
        toggleCodex.state = cfg.showCodex ? .on : .off
        toggleAutostart.state = Autostart.isEnabled ? .on : .off

        let t = Timer(timeInterval: TimeInterval(cfg.refreshSeconds), repeats: true) { [weak self] _ in
            MainActor.assumeIsolated { self?.refresh() }
        }
        RunLoop.main.add(t, forMode: .common)  // 選單打開時也照常刷新
        timer = t
        refresh()
    }

    private func item(_ action: Selector, key: String = "") -> NSMenuItem {
        let i = NSMenuItem(title: "", action: action, keyEquivalent: key)
        i.target = self
        return i
    }

    /// 組出「  標籤：值」格式的明細列（含兩格縮排）。
    private func line(_ labelKey: String, _ value: String) -> String {
        "  \(L.t(labelKey))\(L.t("colon"))\(value)"
    }

    // MARK: - 事件

    @objc private func onRefresh() { refresh(force: true) }  // 手動：繞過節流/冷卻一次

    @objc private func onToggleClaude() {
        cfg.showClaude.toggle()
        toggleClaude.state = cfg.showClaude ? .on : .off
        saveConfig()
        refresh()
    }

    @objc private func onToggleCodex() {
        cfg.showCodex.toggle()
        toggleCodex.state = cfg.showCodex ? .on : .off
        saveConfig()
        refresh()
    }

    @objc private func onToggleAutostart() {
        if Autostart.isEnabled { Autostart.disable() } else { Autostart.enable() }
        toggleAutostart.state = Autostart.isEnabled ? .on : .off
    }

    @objc private func onCycleShape() {
        cfg.shape = cfg.shape.next
        saveConfig()
        shapeItem.title = shapeMenuTitle()
        renderTitle()
    }

    @objc private func onToggleLang() {
        cfg.language = cfg.language == .zh ? .en : .zh
        L.lang = cfg.language
        saveConfig()
        applyMenuLanguage()
        refresh()
    }

    @objc private func onOpenConfig() {
        Config.ensureExists()
        NSWorkspace.shared.activateFileViewerSelecting([Config.path])
    }

    // KeepAlive=false，按下即永久關閉，launchd 不會再拉回來。
    @objc private func onQuit() { NSApp.terminate(nil) }

    private func shapeMenuTitle() -> String {
        L.t("menu_shape") + L.t("colon") + L.t("shape_" + cfg.shape.rawValue)
    }

    private func applyMenuLanguage() {
        toggleClaude.title = L.t("menu_show_claude")
        toggleCodex.title = L.t("menu_show_codex")
        toggleAutostart.title = L.t("menu_autostart")
        shapeItem.title = shapeMenuTitle()
        langItem.title = L.t("menu_lang")
        refreshItem.title = L.t("menu_refresh")
        openConfigItem.title = L.t("menu_open_config")
        quitItem.title = L.t("menu_quit")
    }

    private func saveConfig() {
        try? cfg.save()  // 寫檔失敗不致命，至少本次工作階段仍生效
    }

    // MARK: - 核心

    private func refresh(force: Bool = false) {
        guard !fetching else { return }
        fetching = true
        let useOfficial = cfg.useOfficialClaude
        let interval = Double(cfg.officialRefreshSeconds)
        let reader = reader
        reader.queue.async {
            let snap = reader.readAll(useOfficial: useOfficial, force: force, officialInterval: interval)
            DispatchQueue.main.async {
                MainActor.assumeIsolated { self.apply(snap) }
            }
        }
    }

    private func apply(_ snap: Snapshot) {
        fetching = false
        updateClaude(snap.claude, snap.claudeOfficial)
        updateCodex(snap.codex)
        updateTitle(snap)
        let f = DateFormatter()
        f.dateFormat = "HH:mm:ss"
        updated.title = L.t("lbl_updated") + L.t("colon") + f.string(from: Date())
    }

    private func claudePct(_ tokens: Int, _ limit: Int) -> Double? {
        limit > 0 ? min(100, Double(tokens) / Double(limit) * 100) : nil
    }

    private func updateClaude(_ c: ClaudeUsage, _ o: ClaudeOfficial) {
        // 估算行（永遠顯示，作為成本參考與官方失敗時的後備）
        if c.ok {
            claudeEst.title = "  " + L.t("est_line", [
                "t5": Fmt.tokens(c.tokens5h), "c5": Fmt.cost(c.cost5h),
                "t7": Fmt.tokens(c.tokens7d), "c7": Fmt.cost(c.cost7d),
            ])
        } else {
            claudeEst.title = line("lbl_est", c.error.isEmpty ? L.t("no_data") : c.error)
        }

        // 官方數字（與 /usage 一致）優先
        if o.ok {
            let tag = L.t(o.projected ? "tag_official_proj" : o.stale ? "tag_official_cache" : "tag_official")
            claude5h.title = line("lbl_5h", "\(Fmt.pct(o.fiveHourPct))  ·  \(Fmt.reset(o.fiveHourReset))\(tag)")
            claude7d.title = line("lbl_weekly", "\(Fmt.pct(o.weeklyPct))  ·  \(Fmt.reset(o.weeklyReset))\(tag)")
            claudePlan.title = line("lbl_plan", o.plan.isEmpty ? L.t("dash") : o.plan)
            return
        }

        // 官方失敗 → 退回估算（如有設定額度則換算百分比）
        let reason = o.error.isEmpty ? L.t("no_data") : o.error
        claude5h.title = line("lbl_5h", estValue(c, c.tokens5h, claudePct(c.tokens5h, cfg.claude5hTokenLimit)))
        claude7d.title = line("lbl_weekly", estValue(c, c.tokens7d, claudePct(c.tokens7d, cfg.claudeWeeklyTokenLimit)))
        claudePlan.title = line("lbl_plan", L.t("official_unavailable", ["reason": reason]))
    }

    private func estValue(_ c: ClaudeUsage, _ tokens: Int, _ pct: Double?) -> String {
        guard c.ok else { return L.t("dash") }
        if let pct { return L.t("pct_est", ["p": Fmt.pct(pct)]) }
        return L.t("tokens_est", ["n": Fmt.tokens(tokens)])
    }

    private func updateCodex(_ x: CodexUsage) {
        guard x.ok else {
            codex5h.title = line("lbl_5h", x.error.isEmpty ? L.t("no_data") : x.error)
            codexWeek.title = line("lbl_weekly", L.t("dash"))
            codexPlan.title = line("lbl_plan", L.t("dash"))
            return
        }
        codex5h.title = codexWindowLine(x.primary, "lbl_5h")
        codexWeek.title = codexWindowLine(x.secondary, "lbl_weekly")
        codexPlan.title = line("lbl_plan", x.planType.isEmpty ? L.t("dash") : x.planType)
    }

    /// 以視窗實際長度（window_minutes）決定標籤，而非寫死 5 小時/每週。
    private func codexWindowLine(_ w: CodexWindow?, _ fallbackKey: String) -> String {
        guard let w else { return line(fallbackKey, L.t("dash")) }
        let label = L.codexWindowLabel(w.windowMinutes)
        return "  \(label)\(L.t("colon"))\(Fmt.pct(w.usedPercent))  ·  \(Fmt.reset(w.resetsAt))"
    }

    private func updateTitle(_ snap: Snapshot) {
        var parts: [String] = []
        var worst = 0.0

        // Claude：官方 5 小時 % 優先；否則用估算（有額度→%，無額度→token 數）。
        // 燈號只跟 5 小時窗，與標題顯示的數字一致；每週窗只在選單明細呈現。
        let o = snap.claudeOfficial, c = snap.claude
        if cfg.showClaude {
            if o.ok {
                parts.append("C \(Fmt.pct(o.fiveHourPct))")
                worst = max(worst, o.fiveHourPct)
            } else if c.ok {
                if let p = claudePct(c.tokens5h, cfg.claude5hTokenLimit) {
                    parts.append("C \(Fmt.pct(p))")
                    worst = max(worst, p)
                } else {
                    parts.append("C \(Fmt.tokens(c.tokens5h))")
                }
            }
        }

        // Codex：燈號只跟 5 小時（primary）窗。
        if cfg.showCodex, snap.codex.ok, let p = snap.codex.primary {
            parts.append("X \(Fmt.pct(p.usedPercent))")
            worst = max(worst, p.usedPercent)
        }

        self.worst = worst
        self.parts = parts
        renderTitle()
    }

    private func renderTitle() {
        guard !parts.isEmpty else {
            statusItem.button?.title = Icon.render(0, hasData: false, shape: cfg.shape) + " " + L.t("title_no_data")
            return
        }
        statusItem.button?.title = Icon.render(worst, hasData: true, shape: cfg.shape)
            + "  " + parts.joined(separator: " · ")
    }
}
