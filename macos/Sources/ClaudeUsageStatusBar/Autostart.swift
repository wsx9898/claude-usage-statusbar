// 管理 macOS LaunchAgent（登入時自動啟動）。
//
// - LaunchAgent 的 KeepAlive=false：從選單列按「結束」就是永久關閉，launchd 不會拉回來；
//   只有「登入」時才會依 RunAtLoad 自動開。
// - 「開機時自動啟動」開關 = 這個 plist 是否存在。關閉時只移除 plist，不殺掉目前的程序。
// - ProgramArguments 直接指向目前執行中的 .app 執行檔。

import Foundation

enum Autostart {
    static let label = "com.user.claude-usage-statusbar"

    private static let home = FileManager.default.homeDirectoryForCurrentUser
    static let plistURL = home.appendingPathComponent("Library/LaunchAgents/\(label).plist")
    private static let logDir = home.appendingPathComponent("Library/Logs")

    private static var plistContents: [String: Any] {
        [
            "Label": label,
            "ProgramArguments": [Bundle.main.executablePath ?? CommandLine.arguments[0]],
            "RunAtLoad": true,
            "KeepAlive": false,
            "ProcessType": "Interactive",
            "StandardOutPath": logDir.appendingPathComponent("\(label).log").path,
            "StandardErrorPath": logDir.appendingPathComponent("\(label).err.log").path,
        ]
    }

    static var isEnabled: Bool { FileManager.default.fileExists(atPath: plistURL.path) }

    /// 寫入/更新 plist 並向 launchd 註冊。只做 load：已載入時是 no-op，不會砍掉目前的程序。
    static func enable() {
        writePlist()
        launchctl("load", plistURL.path)
    }

    /// 移除 plist，使下次登入不再自動啟動。不殺掉目前正在跑的程序。
    static func disable() {
        try? FileManager.default.removeItem(at: plistURL)
    }

    /// 啟動時呼叫：若已啟用，確保 plist 內容指向目前的執行檔（只重寫檔案、不重載）。
    static func sync() {
        if isEnabled { writePlist() }
    }

    private static func writePlist() {
        try? FileManager.default.createDirectory(
            at: plistURL.deletingLastPathComponent(), withIntermediateDirectories: true)
        if let data = try? PropertyListSerialization.data(
            fromPropertyList: plistContents, format: .xml, options: 0) {
            try? data.write(to: plistURL, options: .atomic)
        }
    }

    private static func launchctl(_ args: String...) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        p.arguments = args
        p.standardOutput = FileHandle.nullDevice
        p.standardError = FileHandle.nullDevice
        try? p.run()
        p.waitUntilExit()
    }
}
