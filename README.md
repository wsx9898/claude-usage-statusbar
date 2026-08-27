# claude-usage-statusbar

放在選單列（macOS）／系統匣（Windows）的輕量「AI 用量監看」工具。它是一個**本機儀表板**，
透過讀取本機快取檔，監看你的 **Claude Code** 與 **Codex** 用量／額度。

> 主要靠讀取 `~/.claude`、`~/.codex` 的本機檔案，以及作業系統存放 Claude Code 登入憑證的地方
> （macOS 是 Keychain，Windows 是 `%USERPROFILE%\.claude\.credentials.json`）；**不需要另外登入**。
> 取 Claude 官方用量時會用既有 token 打一次 Anthropic 的 usage 端點（可在設定關閉，見下方）。
> macOS 安裝／使用見下方「安裝（macOS）」，Windows 見「Windows 支援」。

## 它顯示什麼

選單列標題（右上角）是**燃料量表**風格：`🟩▰▰▰▰▱  C 12% · X 20%`

- 前面的**彩色形狀＋ `▰▱` 量表**＝**5 小時窗**的狀態（與標題顯示的數字同一個窗，顏色不會被每週窗影響）：
  量表代表「**剩餘額度**」，越用越見底。每格 20%、可顯示半格 `◧`（10% 解析度）。
  顏色 🟩綠（<50%）→ 🟨黃（50–69%）→ 🟧橘（70–89%）→ 🟥紅（≥90%）。
- 形狀可在選單列「圖示形狀」點擊循環切換：方形 🟥 / 圓形 🔴 / 愛心 ❤️（皆有完整四色）。
- **C** = Claude Code 用量（官方 5 小時 %；官方不可用時顯示估算 token/百分比）
- **X** = Codex 最近 5 小時用量百分比（**預設關閉**，見下方「顯示哪些工具」）

```
🟩▰▰▰▰◧  C 12%            ← 很閒（預設只看 Claude；◧ 為半格）
🟨▰▰▱▱▱  C 68%            ← 用一半了
🟥◧▱▱▱▱  C 96%            ← 快爆/已爆（純紅，不閃爍）
```

> 預設只把 **Claude** 納入量表與標題。若想同時監看 Codex，在選單列勾「顯示 Codex」，
> 就會變回 `🟨▰▰▱▱▱  C 68% · X 55%` 這種雙工具樣式（量表取兩者的 5 小時窗中較緊張者）。

### 顯示哪些工具

選單列可即時勾選（會存進設定檔）：

- **顯示 Claude** / **顯示 Codex**：控制顏色、閃爍、能量條與標題要納入哪些工具。
  只訂閱 Claude 時，建議維持 Codex 關閉，避免 Codex 陳舊或已用滿的額度把燈號鎖成紅的。
- **圖示形狀**：點擊循環切換方形 / 圓形 / 愛心（存進設定檔 `shape`）。
- **切換語言 / Language**：中 ↔ 英即時切換（也會存進設定檔 `language`）。

點開選單可看到詳細資訊：

- **Claude Code**
  - 5 小時 / 每週：**官方使用百分比**（與 `claude /usage` 一致）+ 重置時間
  - 估算：5 小時 / 7 天的 token 數與估算成本（成本參考用，也是官方數字不可用時的後備）
  - 方案類型
- **Codex**
  - 主視窗 / 次視窗：使用百分比 + 重置時間（標籤依實際窗長動態顯示：5 小時 / 每週 / 每月…）
  - 方案類型（free / plus / pro…）

## 資料來源

| 工具 | 來源 | 取得方式 |
|------|------|----------|
| **Claude Code（官方）** | macOS Keychain 的 `Claude Code-credentials` + Anthropic API | 重用 Claude Code 已登入的 OAuth token，呼叫 `/usage` 同源端點 `GET /api/oauth/usage`，取得 5 小時 / 每週的**官方使用百分比**與重置時間 |
| Claude Code（估算） | `~/.claude/projects/*/*.jsonl` | 彙整每筆訊息的 `usage`（input/output/cache tokens）與時間戳，算出滾動 5 小時 / 7 天的 token 與估算成本（成本參考 + 官方失敗時後備）。同一則訊息重複出現在多個檔案時以 `requestId:message.id` 去重；快取寫入依 TTL 分級計價（5 分鐘 1.25x、1 小時 2x）|
| Codex | `~/.codex/sessions/**/rollout-*.jsonl` | 讀取最新 `token_count` 事件的 `rate_limits`（5 小時窗、每週窗的 `used_percent`、`resets_at`、`plan_type`）— 官方回報的精準百分比 |

### 關於官方數字（與 `/usage` 一致）

- **不需要另外登入**：直接重用 Claude Code 已存在 Keychain 的 OAuth token。
- **只讀不寫**：不會刷新 token、也不會寫回 Keychain，避免與 Claude Code 衝突。
  你持續使用 Claude Code 時，它會自動維持 token 新鮮；萬一 token 過期（API 回 401）、
  讀不到憑證或無網路，會**自動退回本機估算**，最壞情況與不接官方時相同。
- **首次授權**：背景程式透過系統 `security` 工具讀取憑證，第一次可能跳出
  「`security` 想存取 Claude Code-credentials」的視窗，按**一律允許**一次即可，之後靜默。
- **注意**：`/api/oauth/usage` 為 Claude Code 內部端點、非公開文件，Claude 改版時有可能變動；
  屆時會自動 fallback，不會讓 App 崩潰。成本仍為估算值、非帳單金額。

> 若不想用官方數字（或不想看到 Keychain 授權），在設定檔把 `use_official_claude` 設為 `false`。

### 隱私與安全

這是一個**本機優先**的工具，設計上盡量不外送任何資料：

- **唯一的對外連線**，是用你**既有**的 Claude Code OAuth token 打一次 Anthropic 的
  `GET /api/oauth/usage`（就是 `claude /usage` 同源端點），只為了取回你自己的用量百分比與重置時間。
  除此之外不連任何伺服器、不做遙測、不上傳本機檔案內容。
- **token 只讀不寫**：透過系統 `security` 工具即時讀取 Keychain 裡的憑證，**不會刷新、不會寫回**，
  也**不會存進任何檔案或記憶體以外的地方**。程式碼本身不含任何密鑰。
- **失敗即退回本機估算**：讀不到憑證、token 過期（401）、無網路或端點變動時，會自動改用
  `~/.claude` / `~/.codex` 的本機紀錄估算，最壞情況與「完全不接官方」相同，不會崩潰。
- **完全可關閉**：把 `use_official_claude` 設為 `false`，就連這唯一的對外連線與 Keychain 讀取都不會發生。
- Codex 與 Claude 估算的數據**全程只在本機讀取**，不對外傳送。

## 安裝（macOS，含登入自動啟動）

需求：macOS、Python 3（`python3`）。

```bash
cd claude-usage-statusbar
bash install.sh
```

`install.sh` 會：

1. 把執行用副本部署到 `~/Library/Application Support/claude-usage-statusbar/`，
   並在該處建立隔離的 Python 虛擬環境（`.venv`）、安裝相依套件（`rumps`）。
2. 安裝一個 **LaunchAgent**，設定 `RunAtLoad`（每次登入自動啟動）；`KeepAlive=false`，
   所以**從選單列「結束（永久關閉）」按下就真的關掉**，launchd 不會把它拉回來。
   是否「登入時自動啟動」可隨時在選單列「開機時自動啟動」切換。

安裝後圖示會立刻出現在右上角，往後每次登入也會自動出現（除非關掉「開機時自動啟動」）。

> **為何要部署副本？** macOS 的 TCC 權限會保護 `~/Documents`、`~/Desktop` 等位置，
> 由 `launchd` 啟動的程序無法在這些位置「執行」程式碼（會出現 *Operation not permitted*）。
> 因此安裝時會把執行副本放到不受保護的 `~/Library/Application Support`；
> 你的 git 開發倉庫可繼續留在 `~/Documents`。改了原始碼後重新執行 `bash install.sh` 即可更新副本。

解除安裝：

```bash
bash uninstall.sh          # 移除 LaunchAgent，保留執行副本
bash uninstall.sh --purge  # 一併刪除執行副本與 venv
```

## 手動執行（macOS，不安裝自動啟動）

```bash
bash run.sh
```

第一次執行會自動建立 `.venv` 並安裝相依套件，之後直接啟動。

## 啟動、關閉、重新開啟（macOS）

| 情況 | 會怎樣 / 該怎麼做 |
|------|------------------|
| **重開機 / 重新登入** | 若「開機時自動啟動」為開，會自動出現在右上角（`RunAtLoad`）。 |
| **按選單「結束（永久關閉）」** | 立刻關閉，**不會自己回來**（`KeepAlive=false`）。下次登入是否自動開取決於「開機時自動啟動」。 |
| **關掉後，想用 terminal 再開** | `launchctl kickstart gui/$(id -u)/com.user.claude-usage-statusbar`（自動啟動為開、agent 已載入時用這個最快）。 |
| **若已關掉「開機時自動啟動」（agent 未載入）** | `bash "$HOME/Library/Application Support/claude-usage-statusbar/run.sh"`，或在選單把「開機時自動啟動」勾回來再 kickstart。 |
| **想要登入不再自動開** | 選單列取消勾選「開機時自動啟動」（移除 plist），或 `bash uninstall.sh`。 |
| **只想臨時跑一次、不裝自動啟動** | `bash run.sh`。 |

> **TL;DR：UI 結束之後要從終端機再開，用這一條：**
> ```bash
> launchctl kickstart gui/$(id -u)/com.user.claude-usage-statusbar
> ```
> 若你曾關掉「開機時自動啟動」（plist 被移除、agent 沒載入），上面那條會找不到服務，
> 改用：`bash "$HOME/Library/Application Support/claude-usage-statusbar/run.sh"`。

## 分享給朋友（macOS）

這個工具是**通用的**——它讀的是「執行者自己」的本機檔與「執行者自己」的 Keychain，
所以朋友拿去用，看到的是他自己的用量，不會碰到你的任何資料或 token。

給朋友的步驟：

1. 把整個專案資料夾給他（用 Git 或壓縮檔皆可；**壓縮前先排除 `.venv/`** 以免肥大且綁路徑）。
2. 他需要：macOS + `python3`（沒有的話 `brew install python`）。
3. 在資料夾內執行 `bash install.sh`。
4. 首次會下載 `rumps`（約 6MB，需網路）；首次可能跳一次 Keychain 授權，按「一律允許」。

> 程式碼本身**不含任何密鑰**——token 是執行時去各自的 Keychain 即時讀取，所以分享資料夾是安全的。
> 朋友要看 Claude 官方數字，前提是他電腦上有登入過的 Claude Code；要看 Codex 則需有 Codex 的本機紀錄。

## 設定（可選）

設定檔位置：`~/.config/claude-usage-statusbar/config.json`
（可從選單「開啟設定檔位置」直接建立並開啟）

```json
{
  "refresh_seconds": 20,
  "official_refresh_seconds": 60,
  "language": "zh",
  "shape": "square",
  "use_official_claude": true,
  "show_claude": true,
  "show_codex": false,
  "claude_5h_token_limit": 0,
  "claude_weekly_token_limit": 0
}
```

- `refresh_seconds`：UI 重新整理間隔秒數（預設 20、最小 10）。只做本機讀檔＋重繪，
  解析結果有 mtime 快取、成本極低，開高頻率不傷磁碟。
- `official_refresh_seconds`：官方 API 抓取的**最小間隔**（預設 60、最小 30）。
  UI 刷新再頻繁，打 Anthropic API 也不會比這個密；間隔內沿用上次官方值＋本機推估。
- `language`：介面語言，`"zh"`（中文，預設）或 `"en"`（English）。可在選單列「切換語言 / Language」即時切換。
- `shape`：指示形狀，`"square"`（方形，預設）/ `"circle"`（圓形）/ `"heart"`（愛心）。可在選單列「圖示形狀」點擊循環。
- `use_official_claude`：是否讀取 Claude 官方用量（預設 `true`）。設 `false` 則只用本機估算、
  也不會觸發 Keychain 授權。
- `show_claude` / `show_codex`：量表（顏色/閃爍/能量條）與標題要納入哪些工具。
  **`show_codex` 預設為 `false`**（只訂閱 Claude 時避免被 Codex 額度干擾）；可在選單列即時切換。
- `claude_5h_token_limit` / `claude_weekly_token_limit`：僅在**官方數字不可用、退回估算**時生效；
  填入大於 0 的 token 額度後，估算會換算成百分比，否則顯示 token 數與估算成本。

> 修改設定檔後，從選單「立即重新整理」或重啟 App 生效。

## 專案結構

```
claude-usage-statusbar/
├── src/usage_statusbar/
│   ├── app.py             # 平台分派層（依 sys.platform 選 app_macos / app_windows）
│   ├── app_macos.py       # rumps 選單列 App（UI / 定時器）
│   ├── app_windows.py     # pystray 系統匣 App（UI / 背景執行緒）
│   ├── readers.py         # 讀取 Claude / Codex 本機快取（估算，跨平台）
│   ├── claude_remote.py   # 重用已登入 token 取 Claude 官方用量（macOS 讀 Keychain／其他讀憑證檔）
│   ├── icon.py            # 燃料量表圖示：macOS 版 emoji 字串 + Windows 版點陣圖
│   ├── autostart.py       # 平台分派層（依 sys.platform 選 autostart_macos / autostart_windows）
│   ├── autostart_macos.py   # 管理 LaunchAgent（開機自動啟動開關）
│   ├── autostart_windows.py # 管理 HKCU Run 機碼（開機自動啟動開關）
│   ├── i18n.py            # 中英文字串表（介面語言切換）
│   ├── pricing.py         # 模型估價表
│   ├── format.py          # 顯示格式化
│   └── config.py          # 設定檔讀取 / 寫入
├── run.sh                 # 啟動器 - macOS/Linux（建立 venv + 啟動）
├── install.sh             # 安裝 LaunchAgent - macOS（登入自動啟動；KeepAlive=false）
├── uninstall.sh           # 解除安裝 - macOS
├── run_windows.bat        # 啟動器 - Windows（建立 venv + 啟動）
├── install_windows.bat    # 安裝 - Windows（建立 venv + 設定登入自動啟動）
├── uninstall_windows.bat  # 解除安裝 - Windows
├── run_hidden.vbs         # Windows 登入自動啟動用：隱藏視窗執行 run_windows.bat
└── requirements.txt       # 依平台標記（rumps 僅 macOS；pystray/Pillow 僅 Windows）
```

## 疑難排解（macOS）

- 看不到圖示：確認登入的是有畫面的桌面工作階段；查看記錄檔
  `~/Library/Logs/com.user.claude-usage-statusbar.log`。
- 顯示「無資料」：表示對應的快取檔尚未產生或近期沒有用量。
- Claude 顯示「官方數字不可用」：多半是 token 暫時過期（再開一下 Claude Code 就會刷新），
  或 Keychain 授權被取消；會自動退回估算，不影響運作。

## Windows 支援

Windows 版是系統匣（工作列右下角）圖示，功能與 macOS 選單列版對等：一樣讀取
`~/.claude`、`~/.codex` 的本機檔案，一樣重用 Claude Code 已登入的 OAuth token
取官方用量（Windows 上這組憑證存在 `%USERPROFILE%\.claude\.credentials.json`，
不是 Keychain，是明文 JSON 檔）。三處與系統綁定的實作已改為 Windows 版本：

| 功能 | macOS | Windows |
|------|-------|---------|
| 選單列 / 系統匣 UI | `rumps` | `pystray` + `Pillow`（把彩色形狀＋使用率百分比畫成圖示；Windows 系統匣沒有文字標題，改放在滑鼠移過去的提示文字） |
| 官方用量憑證 | Keychain（`security` 指令） | `%USERPROFILE%\.claude\.credentials.json` |
| 開機自動啟動 | LaunchAgent（plist） | 登入啟動機碼 `HKCU\...\Run`（透過隱藏的 `run_hidden.vbs`，避免彈出命令提示字元視窗）|

需求：Windows 10/11、Python 3（[python.org](https://www.python.org/downloads/) 下載時記得勾選
「Add python.exe to PATH」）。

### 安裝（含登入自動啟動）

```bat
cd claude-usage-statusbar
install_windows.bat
```

會建立 `.venv`、安裝相依套件（`pystray`、`Pillow`）、設定登入時自動啟動，並立刻啟動 App。
圖示會出現在工作列右下角的系統匣（沒看到就點展開箭頭「顯示隱藏的圖示」，可拖曳釘選出來）。

解除安裝：

```bat
uninstall_windows.bat          rem 移除登入自動啟動設定，保留 .venv
uninstall_windows.bat --purge  rem 一併刪除 .venv
```

### 手動執行（不安裝自動啟動）

```bat
run_windows.bat
```

用一般的 `python.exe`（非 `pythonw.exe`）啟動，會保留命令提示字元視窗顯示輸出，
方便第一次執行或疑難排解時看錯誤訊息。第一次執行會自動建立 `.venv` 並安裝相依套件。

### 疑難排解

- **系統匣看不到圖示**：多半是點了「顯示隱藏的圖示」箭頭後才看得到；也可能是
  `install_windows.bat` 執行中出錯，改用 `run_windows.bat` 手動執行看錯誤訊息。
- **Claude 顯示「官方數字不可用」**：確認電腦上有登入過的 Claude Code CLI
  （`%USERPROFILE%\.claude\.credentials.json` 要存在），或等 Claude Code 下次刷新 token。
- 想同時監看 Codex：在系統匣選單勾選「顯示 Codex」，跟 macOS 版一樣。
