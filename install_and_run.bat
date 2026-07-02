@echo off
title Skython AI Installer and Launcher
echo ============================================================
echo   SKYTHON AI - Autonomous Offline Python Mentor
echo ============================================================
echo.

REM ─── Check Python ────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo Found Python %PY_VER%

REM ─── Check for uv ────────────────────────────────────────────────────────────
uv --version >nul 2>&1
if errorlevel 1 (
    echo uv not found — installing via pip...
    pip install uv --quiet
    if errorlevel 1 (
        echo WARNING: Could not install uv. Will use pip directly.
        goto USE_PIP
    )
)
echo Found uv package manager.

REM ─── Install dependencies via uv ─────────────────────────────────────────────
echo.
echo Installing dependencies with uv...
uv pip install -r requirements.txt
if errorlevel 1 (
    echo uv install failed — falling back to pip...
    goto USE_PIP
)
goto LAUNCH

:USE_PIP
echo Installing dependencies with pip...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Dependency installation failed.
    echo Check your internet connection and try again.
    pause
    exit /b 1
)

:LAUNCH
echo.
echo ============================================================
echo   Starting Skython AI...
echo ============================================================
echo.
echo TIP: Make sure Ollama is running!
echo      If not: download from https://ollama.com then run: ollama serve
echo      Pull the model:  ollama pull gemma3:1b
echo.
python main.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   Skython AI exited with an error.
    echo   Check skython.log for details.
    echo ============================================================
)
pause
