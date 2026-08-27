@echo off
rem Uninstall (Windows): removes the start-at-login setting.
rem Keeps .venv by default; pass --purge to also delete it.
rem If the app is currently running, quit it from the tray menu yourself.
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

if exist "%VENV_DIR%\Scripts\python.exe" (
  "%VENV_DIR%\Scripts\python.exe" -c "from usage_statusbar import autostart_windows as a; a.disable()"
  echo [uninstall] Start-at-login setting removed.
) else (
  echo [uninstall] No venv found; it may not be installed.
)

if "%~1"=="--purge" (
  echo [uninstall] Deleting virtual environment: %VENV_DIR%
  rmdir /s /q "%VENV_DIR%"
)

echo [uninstall] If the app is still running, quit it from the tray menu.

endlocal
