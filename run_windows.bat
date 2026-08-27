@echo off
rem Launcher (Windows). First run creates an isolated venv and installs deps,
rem then starts the app. Used both for manual runs and by run_hidden.vbs.
setlocal

set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
if "%PYTHON_BIN%"=="" set "PYTHON_BIN=python"

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [setup] Creating virtual environment: %VENV_DIR%
  "%PYTHON_BIN%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo [setup] Failed to create venv. Make sure Python 3 is installed and on PATH.
    exit /b 1
  )
  "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
)

"%VENV_DIR%\Scripts\python.exe" -c "import pystray" >nul 2>&1
if errorlevel 1 (
  echo [setup] Installing dependencies (pystray / Pillow)...
  "%VENV_DIR%\Scripts\python.exe" -m pip install -r "%SCRIPT_DIR%requirements.txt"
)

set "PYTHONPATH=%SCRIPT_DIR%src;%PYTHONPATH%"
"%VENV_DIR%\Scripts\python.exe" -m usage_statusbar
if errorlevel 1 (
  echo.
  echo [error] The app exited with an error ^(see above^). Press any key to close...
  pause >nul
)

endlocal
