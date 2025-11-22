@echo off
REM Grok Chat Wrapper - Batch Script (Windows)
REM Auto-activates venv and executes Grok chat

REM Usage: grok.bat "your message" [options]
REM Example: grok.bat "Hello, how are you?"
REM Example: grok.bat "Explain AI" --stream

if "%~1"=="" (
    echo Usage: %~nx0 "your message" [options]
    echo Example: %~nx0 "Hello!"
    exit /b 1
)

REM Change to script directory
cd /d "%~dp0"

REM Use parent directory's venv (shared with perplexity wrapper)
set SCRIPT_DIR=%~dp0
set PARENT_DIR=%SCRIPT_DIR%..
set VENV_PATH=%PARENT_DIR%\venv

REM Activate parent venv if it exists
if exist "%VENV_PATH%\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "%VENV_PATH%\Scripts\activate.bat"
) else (
    echo Warning: venv not found in parent directory. Creating one...
    cd /d "%PARENT_DIR%"
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt -q
    cd /d "%SCRIPT_DIR%"
)

echo.
echo ========================================
echo Grok Chat Wrapper
echo ========================================
echo.

python -m src.interfaces.cli chat %*

echo.
echo ========================================
echo Complete
echo ========================================

