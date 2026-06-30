"""macOS 選單列（右上角）用量監看 App。

使用 rumps 建立一個輕量的選單列圖示，定時讀取本機快取檔，
顯示 Claude Code 與 Codex 的用量。完全離線、不需登入。
"""

from __future__ import annotations

import rumps

from . import format as fmt
from . import icon
from . import readers
from .config import CONFIG_PATH, load_config


class UsageStatusBarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("AI", title="AI …", quit_button=None)
        self.cfg = load_config()

        # 選單項目（先建立，之後更新文字）
        self.item_claude_header = rumps.MenuItem("Claude Code")
        self.item_claude_5h = rumps.MenuItem("  5 小時：—")
        self.item_claude_7d = rumps.MenuItem("  每週：—")
        self.item_claude_est = rumps.MenuItem("  估算：—")
        self.item_claude_plan = rumps.MenuItem("  方案：—")

        self.item_codex_header = rumps.MenuItem("Codex")
        self.item_codex_5h = rumps.MenuItem("  5 小時：—")
        self.item_codex_week = rumps.MenuItem("  每週：—")
        self.item_codex_plan = rumps.MenuItem("  方案：—")

        self.item_updated = rumps.MenuItem("更新時間：—")

        # 顯示開關（顏色/閃爍/能量條只會納入已勾選的工具）
        self.item_toggle_claude = rumps.MenuItem("顯示 Claude", callback=self.on_toggle_claude)
        self.item_toggle_codex = rumps.MenuItem("顯示 Codex", callback=self.on_toggle_codex)
        self.item_toggle_claude.state = bool(self.cfg.get("show_claude", True))
        self.item_toggle_codex.state = bool(self.cfg.get("show_codex", True))

        self.menu = [
            self.item_claude_header,
            self.item_claude_5h,
            self.item_claude_7d,
            self.item_claude_est,
            self.item_claude_plan,
            None,
            self.item_codex_header,
            self.item_codex_5h,
            self.item_codex_week,
            self.item_codex_plan,
            None,
            self.item_updated,
            self.item_toggle_claude,
            self.item_toggle_codex,
            rumps.MenuItem("立即重新整理", callback=self.on_refresh),
            rumps.MenuItem("開啟設定檔位置", callback=self.on_open_config),
            None,
            rumps.MenuItem("結束", callback=rumps.quit_application),
        ]

        # 標題狀態快取（供動畫定時器重繪用，不重新讀檔/連網）
        self._worst = 0.0
        self._parts: list[str] = []
        self._has_data = False
        self._phase = 0

        # 資料定時器（慢：讀檔 + 連網）
        self.timer = rumps.Timer(self.on_tick, self.cfg["refresh_seconds"])
        self.timer.start()
        # 動畫定時器（快：只重繪標題，讓臨界紅塊閃爍）
        self.anim_timer = rumps.Timer(self.on_anim, 0.5)
        self.anim_timer.start()
        # 啟動即先抓一次
        self.refresh()

    # -- 事件 --------------------------------------------------------------
    def on_tick(self, _timer) -> None:
        self.refresh()

    def on_refresh(self, _sender) -> None:
        self.refresh()

    def on_anim(self, _timer) -> None:
        # 只在臨界（紅塊）時需要閃爍；其餘狀態重繪結果相同、成本極低
        self._phase ^= 1
        self._render_title()

    def on_toggle_claude(self, sender) -> None:
        sender.state = not sender.state
        self.cfg["show_claude"] = bool(sender.state)
        self._save_cfg()
        self.refresh()

    def on_toggle_codex(self, sender) -> None:
        sender.state = not sender.state
        self.cfg["show_codex"] = bool(sender.state)
        self._save_cfg()
        self.refresh()

    def _save_cfg(self) -> None:
        from .config import save_config

        try:
            save_config(self.cfg)
        except OSError:
            pass  # 寫檔失敗不致命，至少本次工作階段仍生效

    def on_open_config(self, _sender) -> None:
        import os
        import subprocess

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(
                    '{\n'
                    '  "refresh_seconds": 60,\n'
                    '  "claude_5h_token_limit": 0,\n'
                    '  "claude_weekly_token_limit": 0,\n'
                    '  "show_claude": true,\n'
                    '  "show_codex": false\n'
                    '}\n'
                )
        subprocess.Popen(["open", "-R", CONFIG_PATH])

    # -- 核心 --------------------------------------------------------------
    def refresh(self) -> None:
        try:
            snap = readers.read_all(use_official=bool(self.cfg.get("use_official_claude", True)))
        except Exception as exc:  # 保底：任何讀取錯誤都不該讓 App 崩潰
            self.title = "AI ⚠️"
            self.item_updated.title = f"讀取錯誤：{exc}"
            return

        self._update_claude(snap.claude, snap.claude_official)
        self._update_codex(snap.codex)
        self._update_title(snap)

        import time

        self.item_updated.title = "更新時間：" + time.strftime("%H:%M:%S")

    def _claude_pct(self, tokens: int, limit_key: str) -> float | None:
        limit = self.cfg.get(limit_key, 0) or 0
        if limit > 0:
            return min(100.0, tokens / limit * 100.0)
        return None

    def _update_claude(self, c: readers.ClaudeUsage, o) -> None:
        # 估算行（永遠顯示，作為成本參考與官方失敗時的後備）
        if c.ok:
            self.item_claude_est.title = (
                f"  估算：5h {fmt.fmt_tokens(c.tokens_5h)}/{fmt.fmt_cost(c.cost_5h)}"
                f" · 7d {fmt.fmt_tokens(c.tokens_7d)}/{fmt.fmt_cost(c.cost_7d)}"
            )
        else:
            self.item_claude_est.title = "  估算：" + (c.error or "無資料")

        # 官方數字（與 /usage 一致）優先
        if o.ok:
            self.item_claude_5h.title = (
                f"  5 小時：{fmt.fmt_pct(o.five_hour_pct)}"
                f"  ·  {fmt.fmt_reset(o.five_hour_reset)}（官方）"
            )
            self.item_claude_7d.title = (
                f"  每週：{fmt.fmt_pct(o.weekly_pct)}"
                f"  ·  {fmt.fmt_reset(o.weekly_reset)}（官方）"
            )
            self.item_claude_plan.title = "  方案：" + (o.plan or "—")
            return

        # 官方失敗 → 退回估算（如有設定額度則換算百分比）
        reason = o.error or "未啟用"
        pct5 = self._claude_pct(c.tokens_5h, "claude_5h_token_limit")
        pct7 = self._claude_pct(c.tokens_7d, "claude_weekly_token_limit")
        s5 = f"  5 小時：{fmt.fmt_tokens(c.tokens_5h)} tokens（估算）" if c.ok else "  5 小時：—"
        if pct5 is not None and c.ok:
            s5 = f"  5 小時：{fmt.fmt_pct(pct5)}（估算）"
        s7 = f"  每週：{fmt.fmt_tokens(c.tokens_7d)} tokens（估算）" if c.ok else "  每週：—"
        if pct7 is not None and c.ok:
            s7 = f"  每週：{fmt.fmt_pct(pct7)}（估算）"
        self.item_claude_5h.title = s5
        self.item_claude_7d.title = s7
        self.item_claude_plan.title = f"  方案：官方數字不可用（{reason}）"

    def _update_codex(self, x: readers.CodexUsage) -> None:
        if not x.ok:
            self.item_codex_5h.title = "  5 小時：" + (x.error or "無資料")
            self.item_codex_week.title = "  每週：—"
            self.item_codex_plan.title = "  方案：—"
            return

        if x.primary:
            self.item_codex_5h.title = (
                f"  5 小時：{fmt.fmt_pct(x.primary.used_percent)}"
                f"  ·  {fmt.fmt_reset(x.primary.resets_at)}"
            )
        else:
            self.item_codex_5h.title = "  5 小時：—"

        if x.secondary:
            self.item_codex_week.title = (
                f"  每週：{fmt.fmt_pct(x.secondary.used_percent)}"
                f"  ·  {fmt.fmt_reset(x.secondary.resets_at)}"
            )
        else:
            self.item_codex_week.title = "  每週：—"

        self.item_codex_plan.title = "  方案：" + (x.plan_type or "—")

    def _update_title(self, snap: readers.Snapshot) -> None:
        parts: list[str] = []
        worst = 0.0

        # Claude：官方 5 小時 % 優先；否則用估算（有額度→%，無額度→token 數）
        o = snap.claude_official
        c = snap.claude
        if self.cfg.get("show_claude", True):
            if o.ok:
                parts.append(f"C {fmt.fmt_pct(o.five_hour_pct)}")
                worst = max(worst, o.five_hour_pct, o.weekly_pct)
            elif c.ok:
                pct5 = self._claude_pct(c.tokens_5h, "claude_5h_token_limit")
                if pct5 is not None:
                    parts.append(f"C {fmt.fmt_pct(pct5)}")
                    worst = max(worst, pct5)
                else:
                    parts.append(f"C {fmt.fmt_tokens(c.tokens_5h)}")

        # Codex：顯示 5 小時 %（並把每週也納入「最緊張」判斷）
        x = snap.codex
        if self.cfg.get("show_codex", True) and x.ok and x.primary:
            parts.append(f"X {fmt.fmt_pct(x.primary.used_percent)}")
            worst = max(worst, x.primary.used_percent)
            if x.secondary:
                worst = max(worst, x.secondary.used_percent)

        # 快取狀態，交給 _render_title（含動畫）
        self._worst = worst
        self._parts = parts
        self._has_data = bool(parts)
        self._render_title()

    def _render_title(self) -> None:
        if not self._has_data:
            self.title = icon.render(0.0, self._phase, False) + " AI 無資料"
            return
        gauge = icon.render(self._worst, self._phase, True)
        self.title = f"{gauge}  " + " · ".join(self._parts)


def main() -> None:
    UsageStatusBarApp().run()


if __name__ == "__main__":
    main()
