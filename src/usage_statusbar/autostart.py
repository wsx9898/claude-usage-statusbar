"""「開機（登入）時自動啟動」的平台分派層。

實際邏輯依平台拆在：
- macOS   -> autostart_macos.py（LaunchAgent plist）
- Windows -> autostart_windows.py（HKCU Run 機碼）
"""

from __future__ import annotations

import sys

if sys.platform == "darwin":
    from .autostart_macos import disable, enable, is_enabled, sync_startup
elif sys.platform == "win32":
    from .autostart_windows import disable, enable, is_enabled, sync_startup
else:
    # 其他平台（例如純 Linux）：尚未支援自動啟動，開關永遠是關閉且無作用。
    def is_enabled() -> bool:
        return False

    def enable() -> None:
        pass

    def disable() -> None:
        pass

    def sync_startup() -> None:
        pass
