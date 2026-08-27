@echo off
rem Install (Windows): create venv, install deps, enable start-at-login,
rem and launch the app immediately. Windows has no TCC-style restriction
rem like macOS, so we run straight out of this project folder (no copy step).
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
if "%PYTHON_BIN%"=="" set "PYTHON_BIN=python"

echo [install] Creating virtual environment and installing dependencies...
echo [install] (first run downloads pystray/Pillow, a few MB, please wait)
if not exist "%VENV_DIR%\Scripts\python.exe" (
  "%PYTHON_BIN%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [install] Failed to create venv. Make sure Python 3 is installed and on PATH.
    exit /b 1
  )
  "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
)
"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%requirements.txt"

set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"

echo [install] Enabling start at login...
"%VENV_DIR%\Scripts\python.exe" -c "from usage_statusbar import autostart_windows as a; a.enable()"

echo [install] Starting the app...
start "" "%VENV_DIR%\Scripts\pythonw.exe" -m usage_statusbar

echo [install] Done. The icon should appear in the system tray (bottom-right).
echo           If you don't see it, click the up-arrow to show hidden icons,
echo           then drag it onto the taskbar to pin it.
echo           It will also start automatically on every login from now on.
echo           For troubleshooting / verbose output, run run_windows.bat manually.
echo           To uninstall: uninstall_windows.bat

endlocal
