@echo off
REM Perplexity AI Wrapper - Installation Script for Windows
REM Creates virtual environment and installs all dependencies

echo ===================================
echo Perplexity AI Wrapper - Installer
echo ===================================
echo.

REM Initialize git submodules (for cloudscraper)
if exist ".git" (
    echo [0/6] Initializing git submodules...
    git submodule update --init --recursive
    if %ERRORLEVEL% neq 0 (
        echo WARNING: Failed to initialize git submodules (cloudscraper may not be available)
    )
)

REM Remove existing venv if it exists (to avoid permission issues)
if exist "venv" (
    echo [0.5/6] Removing existing venv directory...
    rmdir /s /q venv 2>nul
)

REM Create virtual environment
echo [1/6] Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to create virtual environment
    echo Make sure Python 3.8+ is installed and in PATH
    echo.
    echo If venv directory exists and is locked:
    echo   1. Close all Python processes
    echo   2. Delete the venv folder manually
    echo   3. Run this script again
    echo.
    pause
    exit /b 1
)

REM Activate and upgrade pip
echo [2/6] Activating virtual environment and upgrading pip...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)
python -m pip install --upgrade pip
if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
)

REM Install dependencies
echo [3/6] Installing dependencies...
echo This may take a few minutes...
pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Failed to install dependencies
    echo Check the error messages above
    pause
    exit /b 1
)

REM Install cloudscraper from submodule (if available)
if exist "cloudscraper" (
    echo [4/6] Installing cloudscraper from submodule...
    cd cloudscraper
    pip install -e . 2>nul || pip install . 2>nul || echo WARNING: Could not install cloudscraper from submodule
    cd ..
) else (
    echo [4/6] cloudscraper submodule not found - skipping
)

REM Install Playwright browser (Firefox/Camoufox)
echo [5/6] Installing Playwright Firefox browser...
echo This may take a few minutes...
playwright install firefox
if %ERRORLEVEL% neq 0 (
    echo WARNING: Failed to install Playwright browser
    echo You can install it later with: playwright install firefox
)

REM Create necessary directories
echo [6/6] Creating directories...
if not exist logs mkdir logs
if not exist exports mkdir exports
if not exist screenshots mkdir screenshots
if not exist browser_data mkdir browser_data

echo.
echo ===================================
echo Installation complete!
echo ===================================
echo.
echo Next steps:
echo   1. Activate virtual environment: venv\Scripts\activate
echo   2. Test installation: .\perplexity.bat --help
echo   3. Run a search: .\perplexity.bat search "What is AI?"
echo.
echo Press any key to exit...
pause >nul
