@echo off
REM Wrapper script for perplexity command
cd /d "%~dp0"

REM Try installed package first (if installed via pip)
where perplexity >nul 2>&1
if %ERRORLEVEL% == 0 (
    perplexity %*
    exit /b %ERRORLEVEL%
)

REM Fallback to development mode with venv
if exist venv\Scripts\python.exe (
    venv\Scripts\python.exe -m src.interfaces.cli %*
) else (
    python -m src.interfaces.cli %*
)

