"""macOS 選單列（右上角）用量監看 App。

使用 rumps 建立一個輕量的選單列圖示，定時讀取本機快取檔，
顯示 Claude Code 與 Codex 的用量。完全離線、不需登入。
"""

from __future__ import annotations

import rumps

from . import autostart
from . import format as fmt
from . import i18n
from . import icon
from . import readers
from .config import CONFIG_PATH, load_config


def _line(label_key: str, value: str) -> str:
    """組出「  標籤：值」格式的明細列（含兩格縮排）。"""
    return f"  {i18n.t(label_key)}{i18n.t('colon')}{value}"


class UsageStatusBarApp(rumps.App):
    def __init__(self) -> None:
        super().__init__("AI", title=i18n.t("title_loading"), quit_button=None)
        self.cfg = load_config()
        i18n.set_lang(self.cfg.get("language", "zh"))

        dash = i18n.t("dash")
        # 選單項目（先建立，之後更新文字）
        self.item_claude_header = rumps.MenuItem("Claude Code")
        self.item_claude_5h = rumps.MenuItem(_line("lbl_5h", dash))
        self.item_claude_7d = rumps.MenuItem(_line("lbl_weekly", dash))
        self.item_claude_est = rumps.MenuItem(_line("lbl_est", dash))
        self.item_claude_plan = rumps.MenuItem(_line("lbl_plan", dash))

        self.item_codex_header = rumps.MenuItem("Codex")
        self.item_codex_5h = rumps.MenuItem(_line("lbl_5h", dash))
        self.item_codex_week = rumps.MenuItem(_line("lbl_weekly", dash))
        self.item_codex_plan = rumps.MenuItem(_line("lbl_plan", dash))

        self.item_updated = rumps.MenuItem(i18n.t("lbl_updated") + i18n.t("colon") + dash)

        # 顯示開關（顏色/閃爍/能量條只會納入已勾選的工具）
        self.item_toggle_claude = rumps.MenuItem(
            i18n.t("menu_show_claude"), callback=self.on_toggle_claude
        )
        self.item_toggle_codex = rumps.MenuItem(
            i18n.t("menu_show_codex"), callback=self.on_toggle_codex
        )
        self.item_toggle_claude.state = bool(self.cfg.get("show_claude", True))
        self.item_toggle_codex.state = bool(self.cfg.get("show_codex", False))

        # 開機自動啟動開關（以 LaunchAgent plist 是否存在為準）
        autostart.sync_plist_file()
        self.item_toggle_autostart = rumps.MenuItem(
            i18n.t("menu_autostart"), callback=self.on_toggle_autostart
        )
        self.item_toggle_autostart.state = autostart.is_enabled()

        # 其餘靜態項目（保留參考，切換語言時重新命名）
        self.item_lang = rumps.MenuItem(i18n.t("menu_lang"), callback=self.on_toggle_lang)
        self.item_refresh = rumps.MenuItem(i18n.t("menu_refresh"), callback=self.on_refresh)
        self.item_open_config = rumps.MenuItem(
            i18n.t("menu_open_config"), callback=self.on_open_config
        )
        self.item_quit = rumps.MenuItem(i18n.t("menu_quit"), callback=self.on_quit)

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
            self.item_toggle_autostart,
            self.item_lang,
            self.item_refresh,
            self.item_open_config,
            None,
            self.item_quit,
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

    def on_toggle_autostart(self, sender) -> None:
        if sender.state:  # 目前開 → 關閉
            autostart.disable()
        else:  # 目前關 → 開啟
            autostart.enable()
        sender.state = autostart.is_enabled()

    def on_toggle_lang(self, _sender) -> None:
        self.cfg["language"] = "en" if i18n.LANG == "zh" else "zh"
        i18n.set_lang(self.cfg["language"])
        self._save_cfg()
        self._apply_menu_language()
        self.refresh()

    def on_quit(self, _sender) -> None:
        # KeepAlive=false，按下即永久關閉，launchd 不會再拉回來。
        rumps.quit_application()

    def _apply_menu_language(self) -> None:
        """切換語言後，重新命名所有靜態選單項目（動態項目交給 refresh）。"""
        self.item_toggle_claude.title = i18n.t("menu_show_claude")
        self.item_toggle_codex.title = i18n.t("menu_show_codex")
        self.item_toggle_autostart.title = i18n.t("menu_autostart")
        self.item_lang.title = i18n.t("menu_lang")
        self.item_refresh.title = i18n.t("menu_refresh")
        self.item_open_config.title = i18n.t("menu_open_config")
        self.item_quit.title = i18n.t("menu_quit")

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
                    '  "language": "zh",\n'
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
            self.item_updated.title = i18n.t("read_error", exc=exc)
            return

        self._update_claude(snap.claude, snap.claude_official)
        self._update_codex(snap.codex)
        self._update_title(snap)

        import time

        self.item_updated.title = (
            i18n.t("lbl_updated") + i18n.t("colon") + time.strftime("%H:%M:%S")
        )

    def _claude_pct(self, tokens: int, limit_key: str) -> float | None:
        limit = self.cfg.get(limit_key, 0) or 0
        if limit > 0:
            return min(100.0, tokens / limit * 100.0)
        return None

    def _update_claude(self, c: readers.ClaudeUsage, o) -> None:
        # 估算行（永遠顯示，作為成本參考與官方失敗時的後備）
        if c.ok:
            self.item_claude_est.title = "  " + i18n.t(
                "est_line",
                t5=fmt.fmt_tokens(c.tokens_5h),
                c5=fmt.fmt_cost(c.cost_5h),
                t7=fmt.fmt_tokens(c.tokens_7d),
                c7=fmt.fmt_cost(c.cost_7d),
            )
        else:
            self.item_claude_est.title = _line("lbl_est", c.error or i18n.t("no_data"))

        # 官方數字（與 /usage 一致）優先
        if o.ok:
            if o.projected:
                tag = i18n.t("tag_official_proj")
            elif o.stale:
                tag = i18n.t("tag_official_cache")
            else:
                tag = i18n.t("tag_official")
            self.item_claude_5h.title = _line(
                "lbl_5h", f"{fmt.fmt_pct(o.five_hour_pct)}  ·  {fmt.fmt_reset(o.five_hour_reset)}{tag}"
            )
            self.item_claude_7d.title = _line(
                "lbl_weekly", f"{fmt.fmt_pct(o.weekly_pct)}  ·  {fmt.fmt_reset(o.weekly_reset)}{tag}"
            )
            self.item_claude_plan.title = _line("lbl_plan", o.plan or i18n.t("dash"))
            return

        # 官方失敗 → 退回估算（如有設定額度則換算百分比）
        reason = o.error or i18n.t("no_data")
        pct5 = self._claude_pct(c.tokens_5h, "claude_5h_token_limit")
        pct7 = self._claude_pct(c.tokens_7d, "claude_weekly_token_limit")
        self.item_claude_5h.title = _line("lbl_5h", self._est_value(c, c.tokens_5h, pct5))
        self.item_claude_7d.title = _line("lbl_weekly", self._est_value(c, c.tokens_7d, pct7))
        self.item_claude_plan.title = _line(
            "lbl_plan", i18n.t("official_unavailable", reason=reason)
        )

    def _est_value(self, c: readers.ClaudeUsage, tokens: int, pct: float | None) -> str:
        if not c.ok:
            return i18n.t("dash")
        if pct is not None:
            return i18n.t("pct_est", p=fmt.fmt_pct(pct))
        return i18n.t("tokens_est", n=fmt.fmt_tokens(tokens))

    def _update_codex(self, x: readers.CodexUsage) -> None:
        if not x.ok:
            self.item_codex_5h.title = _line("lbl_5h", x.error or i18n.t("no_data"))
            self.item_codex_week.title = _line("lbl_weekly", i18n.t("dash"))
            self.item_codex_plan.title = _line("lbl_plan", i18n.t("dash"))
            return

        if x.primary:
            self.item_codex_5h.title = _line(
                "lbl_5h",
                f"{fmt.fmt_pct(x.primary.used_percent)}  ·  {fmt.fmt_reset(x.primary.resets_at)}",
            )
        else:
            self.item_codex_5h.title = _line("lbl_5h", i18n.t("dash"))

        if x.secondary:
            self.item_codex_week.title = _line(
                "lbl_weekly",
                f"{fmt.fmt_pct(x.secondary.used_percent)}  ·  {fmt.fmt_reset(x.secondary.resets_at)}",
            )
        else:
            self.item_codex_week.title = _line("lbl_weekly", i18n.t("dash"))

        self.item_codex_plan.title = _line("lbl_plan", x.plan_type or i18n.t("dash"))

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
            self.title = icon.render(0.0, self._phase, False) + " " + i18n.t("title_no_data")
            return
        gauge = icon.render(self._worst, self._phase, True)
        self.title = f"{gauge}  " + " · ".join(self._parts)


def main() -> None:
    UsageStatusBarApp().run()


if __name__ == "__main__":
    main()
