"""Windows 系統匣（右下角）用量監看 App。

用 pystray 建立系統匣圖示，定時讀取本機快取檔，顯示 Claude Code 與 Codex 的用量。
與 macOS 版（macos/，原生 Swift）功能對等，但受限於 Windows 系統匣沒有
「文字標題」這種東西（只有圖示＋滑鼠移過去的提示文字），所以：

- 彩色形狀＋使用率百分比畫成一張小圖當系統匣圖示（見 icon.render_image）。
- macOS 選單列上的「標題文字」改放到系統匣圖示的提示文字（title/tooltip）。
- 選單裡的明細列改用文字置灰（enabled=False）的項目呈現，效果等同 macOS 版本。
"""

from __future__ import annotations

import os
import threading
import time

import pystray

from . import autostart
from . import format as fmt
from . import i18n
from . import icon as icon_mod
from . import readers
from .config import CONFIG_PATH, load_config, save_config


def _line(label_key: str, value: str) -> str:
    return f"{i18n.t(label_key)}{i18n.t('colon')}{value}"


class UsageTrayApp:
    def __init__(self) -> None:
        self.cfg = load_config()
        i18n.set_lang(self.cfg.get("language", "zh"))
        autostart.sync_startup()

        self._running = True
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self._force_next = False

        dash = i18n.t("dash")
        self._claude_lines = {"5h": dash, "7d": dash, "est": dash, "plan": dash}
        self._codex_lines = {
            "5h": i18n.t("lbl_5h") + i18n.t("colon") + dash,
            "week": i18n.t("lbl_weekly") + i18n.t("colon") + dash,
            "plan": dash,
        }
        self._updated_text = dash
        self._worst = 0.0
        self._has_data = False

        self.icon = pystray.Icon(
            "claude-usage-statusbar",
            icon=icon_mod.render_image(0.0, False, self.cfg.get("shape", "square")),
            title=i18n.t("title_loading"),
            menu=pystray.Menu(self._menu_items),
        )

    # -- 選單 ----------------------------------------------------------------
    def _shape_menu_title(self) -> str:
        shape = self.cfg.get("shape", "square")
        return i18n.t("menu_shape") + i18n.t("colon") + i18n.t("shape_" + shape)

    def _menu_items(self):
        MI = pystray.MenuItem
        SEP = pystray.Menu.SEPARATOR
        c = self._claude_lines
        x = self._codex_lines
        return (
            MI("Claude Code", None, enabled=False),
            MI(_line("lbl_5h", c["5h"]), None, enabled=False),
            MI(_line("lbl_weekly", c["7d"]), None, enabled=False),
            MI(_line("lbl_est", c["est"]), None, enabled=False),
            MI(_line("lbl_plan", c["plan"]), None, enabled=False),
            SEP,
            MI("Codex", None, enabled=False),
            MI(x["5h"], None, enabled=False),
            MI(x["week"], None, enabled=False),
            MI(_line("lbl_plan", x["plan"]), None, enabled=False),
            SEP,
            MI(i18n.t("lbl_updated") + i18n.t("colon") + self._updated_text, None, enabled=False),
            MI(
                i18n.t("menu_show_claude"),
                self.on_toggle_claude,
                checked=lambda item: bool(self.cfg.get("show_claude", True)),
            ),
            MI(
                i18n.t("menu_show_codex"),
                self.on_toggle_codex,
                checked=lambda item: bool(self.cfg.get("show_codex", False)),
            ),
            MI(
                i18n.t("menu_autostart"),
                self.on_toggle_autostart,
                checked=lambda item: autostart.is_enabled(),
            ),
            MI(self._shape_menu_title(), self.on_cycle_shape),
            MI(i18n.t("menu_lang"), self.on_toggle_lang),
            MI(i18n.t("menu_refresh"), self.on_refresh),
            MI(i18n.t("menu_open_config"), self.on_open_config),
            SEP,
            MI(i18n.t("menu_quit"), self.on_quit),
        )

    # -- 事件 ------------------------------------------------------------
    def on_cycle_shape(self, icon, item) -> None:
        order = ["square", "circle", "heart"]
        cur = self.cfg.get("shape", "square")
        nxt = order[(order.index(cur) + 1) % len(order)] if cur in order else "square"
        self.cfg["shape"] = nxt
        self._save_cfg()
        self._render_icon()
        icon.update_menu()

    def on_toggle_claude(self, icon, item) -> None:
        self.cfg["show_claude"] = not bool(self.cfg.get("show_claude", True))
        self._save_cfg()
        icon.update_menu()
        self.request_refresh()

    def on_toggle_codex(self, icon, item) -> None:
        self.cfg["show_codex"] = not bool(self.cfg.get("show_codex", False))
        self._save_cfg()
        icon.update_menu()
        self.request_refresh()

    def on_toggle_autostart(self, icon, item) -> None:
        if autostart.is_enabled():
            autostart.disable()
        else:
            autostart.enable()
        icon.update_menu()

    def on_toggle_lang(self, icon, item) -> None:
        self.cfg["language"] = "en" if i18n.LANG == "zh" else "zh"
        i18n.set_lang(self.cfg["language"])
        self._save_cfg()
        icon.update_menu()
        self.request_refresh()

    def on_refresh(self, icon, item) -> None:
        self.request_refresh(force=True)

    def on_open_config(self, icon, item) -> None:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(
                    '{\n'
                    '  "refresh_seconds": 20,\n'
                    '  "official_refresh_seconds": 60,\n'
                    '  "language": "zh",\n'
                    '  "use_official_claude": true,\n'
                    '  "claude_5h_token_limit": 0,\n'
                    '  "claude_weekly_token_limit": 0,\n'
                    '  "show_claude": true,\n'
                    '  "show_codex": false\n'
                    '}\n'
                )
        try:
            os.startfile(os.path.dirname(CONFIG_PATH))  # type: ignore[attr-defined]
        except OSError:
            pass

    def on_quit(self, icon, item) -> None:
        self._running = False
        self._wake.set()
        icon.stop()

    def _save_cfg(self) -> None:
        try:
            save_config(self.cfg)
        except OSError:
            pass

    def request_refresh(self, force: bool = False) -> None:
        if force:
            with self._lock:
                self._force_next = True
        self._wake.set()

    # -- 核心：背景執行緒定時讀檔 + 連網 --------------------------------------
    def _run_loop(self, icon) -> None:
        icon.visible = True
        while self._running:
            with self._lock:
                force = self._force_next
                self._force_next = False
            self._refresh_once(force=force)
            interval = float(self.cfg.get("refresh_seconds", 20))
            self._wake.wait(timeout=interval)
            self._wake.clear()

    def _refresh_once(self, force: bool) -> None:
        use_official = bool(self.cfg.get("use_official_claude", True))
        official_interval = float(self.cfg.get("official_refresh_seconds", 60))
        try:
            snap = readers.read_all(
                use_official=use_official, force=force, official_interval=official_interval
            )
            err = None
        except Exception as exc:  # 保底：任何讀取錯誤都不該讓 App 崩潰
            snap, err = None, exc

        if err is not None:
            self.icon.title = i18n.t("read_error", exc=err)
            return

        self._update_claude(snap.claude, snap.claude_official)
        self._update_codex(snap.codex)
        self._update_title(snap)
        self._updated_text = time.strftime("%H:%M:%S")
        self.icon.update_menu()

    def _claude_pct(self, tokens: int, limit_key: str) -> float | None:
        limit = self.cfg.get(limit_key, 0) or 0
        if limit > 0:
            return min(100.0, tokens / limit * 100.0)
        return None

    def _update_claude(self, c: readers.ClaudeUsage, o) -> None:
        if c.ok:
            self._claude_lines["est"] = i18n.t(
                "est_line",
                t5=fmt.fmt_tokens(c.tokens_5h),
                c5=fmt.fmt_cost(c.cost_5h),
                t7=fmt.fmt_tokens(c.tokens_7d),
                c7=fmt.fmt_cost(c.cost_7d),
            )
        else:
            self._claude_lines["est"] = c.error or i18n.t("no_data")

        if o.ok:
            if o.projected:
                tag = i18n.t("tag_official_proj")
            elif o.stale:
                tag = i18n.t("tag_official_cache")
            else:
                tag = i18n.t("tag_official")
            self._claude_lines["5h"] = (
                f"{fmt.fmt_pct(o.five_hour_pct)}  ·  {fmt.fmt_reset(o.five_hour_reset)}{tag}"
            )
            self._claude_lines["7d"] = (
                f"{fmt.fmt_pct(o.weekly_pct)}  ·  {fmt.fmt_reset(o.weekly_reset)}{tag}"
            )
            self._claude_lines["plan"] = o.plan or i18n.t("dash")
            return

        reason = o.error or i18n.t("no_data")
        pct5 = self._claude_pct(c.tokens_5h, "claude_5h_token_limit")
        pct7 = self._claude_pct(c.tokens_7d, "claude_weekly_token_limit")
        self._claude_lines["5h"] = self._est_value(c, c.tokens_5h, pct5)
        self._claude_lines["7d"] = self._est_value(c, c.tokens_7d, pct7)
        self._claude_lines["plan"] = i18n.t("official_unavailable", reason=reason)

    def _est_value(self, c: readers.ClaudeUsage, tokens: int, pct: float | None) -> str:
        if not c.ok:
            return i18n.t("dash")
        if pct is not None:
            return i18n.t("pct_est", p=fmt.fmt_pct(pct))
        return i18n.t("tokens_est", n=fmt.fmt_tokens(tokens))

    def _update_codex(self, x: readers.CodexUsage) -> None:
        if not x.ok:
            self._codex_lines["5h"] = i18n.t("lbl_5h") + i18n.t("colon") + (
                x.error or i18n.t("no_data")
            )
            self._codex_lines["week"] = i18n.t("lbl_weekly") + i18n.t("colon") + i18n.t("dash")
            self._codex_lines["plan"] = i18n.t("dash")
            return

        self._codex_lines["5h"] = self._codex_window_line(x.primary, "lbl_5h")
        self._codex_lines["week"] = self._codex_window_line(x.secondary, "lbl_weekly")
        self._codex_lines["plan"] = x.plan_type or i18n.t("dash")

    def _codex_window_line(self, w: readers.CodexWindow | None, fallback_key: str) -> str:
        if w is None:
            return i18n.t(fallback_key) + i18n.t("colon") + i18n.t("dash")
        label = i18n.codex_window_label(w.window_minutes)
        value = f"{fmt.fmt_pct(w.used_percent)}  ·  {fmt.fmt_reset(w.resets_at)}"
        return f"{label}{i18n.t('colon')}{value}"

    def _update_title(self, snap: readers.Snapshot) -> None:
        parts: list[str] = []
        worst = 0.0

        o = snap.claude_official
        c = snap.claude
        if self.cfg.get("show_claude", True):
            if o.ok:
                parts.append(f"C {fmt.fmt_pct(o.five_hour_pct)}")
                worst = max(worst, o.five_hour_pct)
            elif c.ok:
                pct5 = self._claude_pct(c.tokens_5h, "claude_5h_token_limit")
                if pct5 is not None:
                    parts.append(f"C {fmt.fmt_pct(pct5)}")
                    worst = max(worst, pct5)
                else:
                    parts.append(f"C {fmt.fmt_tokens(c.tokens_5h)}")

        x = snap.codex
        if self.cfg.get("show_codex", False) and x.ok and x.primary:
            parts.append(f"X {fmt.fmt_pct(x.primary.used_percent)}")
            worst = max(worst, x.primary.used_percent)

        self._worst = worst
        self._has_data = bool(parts)
        self._render_icon()
        self.icon.title = " · ".join(parts) if parts else i18n.t("title_no_data")

    def _render_icon(self) -> None:
        shape = self.cfg.get("shape", "square")
        self.icon.icon = icon_mod.render_image(self._worst, self._has_data, shape)


def main() -> None:
    app = UsageTrayApp()
    app.icon.run(setup=app._run_loop)


if __name__ == "__main__":
    main()
