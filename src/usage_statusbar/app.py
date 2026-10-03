"""選單列 / 系統匣 App 的平台分派層。

- Windows -> app_windows.py（pystray 系統匣）
- macOS 改用原生 Swift 版（見 macos/，以 `bash install.sh` 安裝）
"""

from __future__ import annotations

import sys

if sys.platform == "win32":
    from .app_windows import main
else:
    def main() -> None:
        raise RuntimeError(
            "Python 版只支援 Windows；macOS 請用 Swift 版（bash install.sh）。"
        )
