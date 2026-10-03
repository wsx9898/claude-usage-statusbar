// 進入點：只顯示選單列圖示（不出現在 Dock / Cmd-Tab）。
// `--dump`：不開 UI，讀一次用量並印出（疑難排解用）。

import AppKit

if CommandLine.arguments.contains("--dump") {
    let cfg = Config.load()
    let s = UsageReader().readAll(
        useOfficial: cfg.useOfficialClaude, force: true,
        officialInterval: Double(cfg.officialRefreshSeconds))
    print("claude:", s.claude)
    print("official:", s.claudeOfficial)
    print("codex:", s.codex)
    exit(0)
}

MainActor.assumeIsolated {
    let app = NSApplication.shared
    app.setActivationPolicy(.accessory)
    let controller = StatusBarController()
    withExtendedLifetime(controller) {
        app.run()
    }
}
