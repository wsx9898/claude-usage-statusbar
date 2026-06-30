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
  - 最近 5 小時：token 數 + 估算成本（+ 百分比，需設定額度）
  - 最近 7 天：token 數 + 估算成本（+ 百分比，需設定額度）
- **Codex**
  - 最近 5 小時：使用百分比 + 重置時間
  - 每週：使用百分比 + 重置時間
  - 方案類型（free / plus / pro…）

## 資料來源

| 工具 | 來源檔案 | 取得方式 |
|------|----------|----------|
| Claude Code | `~/.claude/projects/*/*.jsonl` | 彙整每筆訊息的 `usage`（input/output/cache tokens）與時間戳，算出滾動 5 小時 / 7 天視窗的 token 與估算成本 |
| Codex | `~/.codex/sessions/**/rollout-*.jsonl` | 讀取最新 `token_count` 事件中的 `rate_limits`（5 小時窗、每週窗的 `used_percent`、`resets_at`、`plan_type`）— 為官方回報的精準百分比 |

> **註**：Claude Code 的本機檔沒有官方「額度百分比」欄位，因此這裡是以 token 用量與**估算成本**呈現。
> 若你想看百分比，可在設定檔填入自己的額度（見下方）。成本為估算值，並非帳單金額。

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

## 設定（可選）

設定檔位置：`~/.config/claude-usage-statusbar/config.json`
（可從選單「開啟設定檔位置」直接建立並開啟）

```json
{
  "refresh_seconds": 60,
  "claude_5h_token_limit": 0,
  "claude_weekly_token_limit": 0
}
```

- `refresh_seconds`：重新整理間隔秒數（最小 15）。
- `claude_5h_token_limit` / `claude_weekly_token_limit`：填入大於 0 的 token 額度後，
  Claude 區塊與標題會改用**百分比**顯示；預設 0 則只顯示 token 數與估算成本。

> 修改設定檔後，從選單「立即重新整理」或重啟 App 生效。

## 專案結構

```
claude-usage-statusbar/
├── src/usage_statusbar/
│   ├── app.py        # rumps 選單列 App（UI / 定時器）
│   ├── readers.py    # 讀取 Claude / Codex 本機快取
│   ├── pricing.py    # 模型估價表
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
