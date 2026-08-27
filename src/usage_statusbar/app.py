"""選單列 / 系統匣 App 的平台分派層。

實際 UI 實作依平台拆在：
- macOS   -> app_macos.py（rumps 選單列）
- Windows -> app_windows.py（pystray 系統匣）
"""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from .app_macos import main
elif sys.platform == "win32":
    from .app_windows import main
else:
    def main() -> None:
        raise RuntimeError(
            "claude-usage-statusbar 目前只支援 macOS 與 Windows。"
        )
