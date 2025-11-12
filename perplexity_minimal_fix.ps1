# Perplexity AI Wrapper - Command Line Interface
# Auto-activates venv and executes Perplexity searches

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,  # Required: Your search query
    [string]$Mode = "browser",  # "api" or "browser" (default: browser for reliability)
    [string]$CookieProfile = "fresh",  # Cookie profile name (changed from Profile)
    [string]$SearchMode = "search",  # "search", "research", or "labs" (default: search)
    [switch]$Headless,
    [switch]$KeepBrowserOpen,
    [switch]$DebugMode,  # Enable debug logging
    [switch]$Research,   # Enable research mode
    [switch]$ExportMarkdown,  # Export thread as Markdown file after search
    [string]$ExportDir = ""  # Directory to save exported Markdown (default: exports/)
)

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Check if we're already in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment already active: $env:VIRTUAL_ENV" -ForegroundColor Green
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
} elseif (Test-Path "venv\Scripts\python.exe") {
    # Alternative activation method
    $env:VIRTUAL_ENV = Join-Path $scriptDir "venv"
    $env:PATH = "$(Join-Path $scriptDir "venv\Scripts");$env:PATH"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & "venv\Scripts\Activate.ps1"
    pip install -e .
}

# Set search mode based on Research flag
if ($Research) {
    $SearchMode = "research"
}

if ($Mode -eq "api") {
    Write-Host "Using API mode..." -ForegroundColor Cyan
    try {
        python -m src.interfaces.cli search "$Query" --format text --mode $SearchMode
    } catch {
        Write-Host "API mode failed, switching to browser mode..." -ForegroundColor Yellow
        $Mode = "browser"
    }
}

if ($Mode -eq "browser") {
    Write-Host "Using browser automation..." -ForegroundColor Cyan

    # Direct Python browser automation call with original working approach
    $headlessFlag = if ($Headless) { "True" } else { "False" }
    $keepOpenFlag = if ($KeepBrowserOpen) { "True" } else { "False" }

    python -c "
import sys
sys.path.insert(0, '.')
try:
    from src.automation.web_driver import PerplexityWebDriver
    driver = PerplexityWebDriver(headless=$headlessFlag, stealth_mode=True)
    driver.start()
    driver.navigate_to_perplexity()
    result = driver.search('$Query', mode='$SearchMode', wait_for_response=True)
    print('='*60)
    print('SEARCH RESULTS')
    print('='*60)
    print(result)
    if not ($keepOpenFlag == 'True'):
        driver.close()
    else:
        print('Browser kept open as requested')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"

    if ($LASTEXITCODE -ne 0) {
        Write-Host "Browser automation failed!" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Search completed!" -ForegroundColor Green
