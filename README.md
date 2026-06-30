# claude-usage-statusbar

放在 macOS 右上角選單列的輕量「AI 用量監看」工具。它是一個**本機儀表板**，
透過讀取本機快取檔，監看你的 **Claude Code** 與 **Codex** 用量／額度。

> 完全離線：只讀取 `~/.claude` 與 `~/.codex` 底下的本機檔案，**不會發送任何網路請求、也不需要登入**。

## 它顯示什麼

選單列標題（右上角）會以精簡格式顯示，例如：`🟢 C 9.0M · X 20%`

- **C** = Claude Code 最近 5 小時的用量（未設定額度時顯示 token 數；設定額度後顯示百分比）
- **X** = Codex 最近 5 小時的用量百分比
- 燈號（🟢/🟠/🔴）依目前最高使用率變化

點開選單可看到詳細資訊：

- **Claude Code**
  - 5 小時 / 每週：**官方使用百分比**（與 `claude /usage` 一致）+ 重置時間
  - 估算：5 小時 / 7 天的 token 數與估算成本（成本參考用，也是官方數字不可用時的後備）
  - 方案類型
- **Codex**
  - 最近 5 小時：使用百分比 + 重置時間
  - 每週：使用百分比 + 重置時間
  - 方案類型（free / plus / pro…）

## 資料來源

| 工具 | 來源 | 取得方式 |
|------|------|----------|
| **Claude Code（官方）** | macOS Keychain 的 `Claude Code-credentials` + Anthropic API | 重用 Claude Code 已登入的 OAuth token，呼叫 `/usage` 同源端點 `GET /api/oauth/usage`，取得 5 小時 / 每週的**官方使用百分比**與重置時間 |
| Claude Code（估算） | `~/.claude/projects/*/*.jsonl` | 彙整每筆訊息的 `usage`（input/output/cache tokens）與時間戳，算出滾動 5 小時 / 7 天的 token 與估算成本（成本參考 + 官方失敗時後備）|
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

## 安裝（含自動啟動 / 自動重啟）

需求：macOS、Python 3（`python3`）。

```bash
cd claude-usage-statusbar
bash install.sh
```

`install.sh` 會：

1. 把執行用副本部署到 `~/Library/Application Support/claude-usage-statusbar/`，
   並在該處建立隔離的 Python 虛擬環境（`.venv`）、安裝相依套件（`rumps`）。
2. 安裝一個 **LaunchAgent**，設定 `RunAtLoad`（每次登入自動啟動）與 `KeepAlive`
   （結束或閃退後自動重啟）— 即「開機/登入即開、關掉會自己重開」。

安裝後圖示會立刻出現在右上角，往後每次登入也會自動出現。

> **為何要部署副本？** macOS 的 TCC 權限會保護 `~/Documents`、`~/Desktop` 等位置，
> 由 `launchd` 啟動的程序無法在這些位置「執行」程式碼（會出現 *Operation not permitted*）。
> 因此安裝時會把執行副本放到不受保護的 `~/Library/Application Support`；
> 你的 git 開發倉庫可繼續留在 `~/Documents`。改了原始碼後重新執行 `bash install.sh` 即可更新副本。

解除安裝：

```bash
bash uninstall.sh          # 移除 LaunchAgent，保留執行副本
bash uninstall.sh --purge  # 一併刪除執行副本與 venv
```

## 手動執行（不安裝自動啟動）

```bash
bash run.sh
```

第一次執行會自動建立 `.venv` 並安裝相依套件，之後直接啟動。

## 啟動、關閉、重新開啟

| 情況 | 會怎樣 / 該怎麼做 |
|------|------------------|
| **重開機 / 重新登入** | 自動出現在右上角，**不用手動開**（`RunAtLoad`）。 |
| **按選單「結束」** | 幾秒後會自己回來——因為設了 `KeepAlive`（「關掉自己重開」）。所以「結束」≒ 重啟一次。 |
| **想完全關掉（不再自動開）** | `bash uninstall.sh`（移除自動啟動，保留副本）。 |
| **關掉後想再開回來** | `bash install.sh`，或直接重新登入。 |
| **只想臨時跑一次、不裝自動啟動** | `bash run.sh`。 |

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
  "refresh_seconds": 60,
  "use_official_claude": true,
  "claude_5h_token_limit": 0,
  "claude_weekly_token_limit": 0
}
```

- `refresh_seconds`：重新整理間隔秒數（最小 15）。
- `use_official_claude`：是否讀取 Claude 官方用量（預設 `true`）。設 `false` 則只用本機估算、
  也不會觸發 Keychain 授權。
- `claude_5h_token_limit` / `claude_weekly_token_limit`：僅在**官方數字不可用、退回估算**時生效；
  填入大於 0 的 token 額度後，估算會換算成百分比，否則顯示 token 數與估算成本。

> 修改設定檔後，從選單「立即重新整理」或重啟 App 生效。

## 專案結構

```
claude-usage-statusbar/
├── src/usage_statusbar/
│   ├── app.py          # rumps 選單列 App（UI / 定時器）
│   ├── readers.py      # 讀取 Claude / Codex 本機快取（估算）
│   ├── claude_remote.py # 重用 Keychain token 取 Claude 官方用量
│   ├── pricing.py      # 模型估價表
│   ├── format.py     # 顯示格式化
│   └── config.py     # 設定檔讀取
├── run.sh            # 啟動器（建立 venv + 啟動）
├── install.sh        # 安裝 LaunchAgent（自動啟動 + 自動重啟）
├── uninstall.sh      # 解除安裝
└── requirements.txt
```

## 疑難排解

- 看不到圖示：確認登入的是有畫面的桌面工作階段；查看記錄檔
  `~/Library/Logs/com.user.claude-usage-statusbar.log`。
- 顯示「無資料」：表示對應的快取檔尚未產生或近期沒有用量。
- Claude 顯示「官方數字不可用」：多半是 token 暫時過期（再開一下 Claude Code 就會刷新），
  或 Keychain 授權被取消；會自動退回估算，不影響運作。

## Windows 支援（目前僅 macOS）

目前只支援 macOS。核心的「讀檔解析 + 估價」邏輯（`readers.py`、`pricing.py`、`config.py`、`format.py`）
是跨平台的，要移植到 Windows 主要改三塊與系統綁定的部分：

1. **選單列 / 系統匣 UI**：`rumps` 只支援 macOS → 改用 `pystray`（搭配 `Pillow`）之類的系統匣套件。
2. **讀官方用量的憑證**：macOS 用 `security` 讀 Keychain → Windows 需改讀 Windows 認證管理員
   或 Claude Code 在 Windows 的憑證存放位置。
3. **開機自動啟動**：macOS 用 LaunchAgent（plist）→ Windows 改用「工作排程器」或啟動資料夾捷徑。

檔案路徑用的是 `~`（`os.path.expanduser`），在 Windows 也能解析，多半不用大改。
需要 Windows 版時再跟我說。
