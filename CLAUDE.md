# claude-usage-statusbar — Claude 專案指引

> Created: 2026-08-15 | Last Modified: 2026-08-15

請都用繁體中文回答。

## 🔄 Session 開場：先與 GitHub 同步（每次都做）

使用者可能從別台機器（例如 AMD server `ssh n3`）用 Claude Code commit / push，
**所以這個 checkout 隨時可能落後 GitHub**。**每個新 session 在讀 / 改任何檔案前先跑：**

```bash
git fetch origin
git status -sb                  # 看落後幾個 commit、有無未提交變更
git pull --ff-only origin main
```

- **`--ff-only` 失敗（本地與遠端分岔）或有未提交變更 → 停下來問使用者**，不要自行
  merge / rebase / reset / stash 硬幹。
- 本專案**目前只有 Mac 這一份 checkout**（`~/Documents/GitHub/claude-usage-statusbar`），
  n3 `~/apps/` 底下沒有它。若之後在 n3 也 clone 了，記得回來補這條規則。

## 專案概要

Claude Code 用量 statusbar 腳本（`src/`），安裝／移除用 `install.sh`／`uninstall.sh`，
跑法與設定見 `README.md`。
