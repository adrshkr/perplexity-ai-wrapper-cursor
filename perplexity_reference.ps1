# Perplexity AI Wrapper - Working PowerShell Script
# This script provides a clean, working interface to the Perplexity AI Wrapper

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Query,

    [Parameter()]
    [ValidateSet("api", "browser")]
    [string]$Mode = "browser",

    [Parameter()]
    [string]$Profile = "fresh",

    [Parameter()]
    [ValidateSet("search", "research", "labs")]
    [string]$SearchMode = "search",

    [Parameter()]
    [switch]$Headless,

    [Parameter()]
    [switch]$KeepBrowserOpen,

    [Parameter()]
    [switch]$DebugMode,

    [Parameter()]
    [switch]$Research,

    [Parameter()]
    [switch]$ExportMarkdown,

    [Parameter()]
    [string]$ExportDir = ""
)

# Set error handling
$ErrorActionPreference = "Stop"

# Get script directory and change to it
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

Write-Host "🚀 Perplexity AI Wrapper - Starting..." -ForegroundColor Green
Write-Host "Query: $Query" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Cyan

# Override SearchMode if Research flag is used
if ($Research) {
    $SearchMode = "research"
    Write-Host "Research mode enabled - using comprehensive analysis" -ForegroundColor Yellow
}

# Virtual environment activation
$venvPath = Join-Path $scriptDir "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
$pythonExe = Join-Path $venvPath "Scripts\python.exe"

if (Test-Path $activateScript) {
    Write-Host "📦 Activating virtual environment..." -ForegroundColor Yellow
    try {
        & $activateScript
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️ Failed to activate venv script, trying alternative..." -ForegroundColor Yellow
        if (Test-Path $pythonExe) {
            $env:VIRTUAL_ENV = $venvPath
            $env:PATH = "$venvPath\Scripts;$env:PATH"
            Write-Host "✅ Virtual environment set via PATH" -ForegroundColor Green
        }
    }
}
elseif (Test-Path $pythonExe) {
    Write-Host "📦 Using existing virtual environment..." -ForegroundColor Yellow
    $env:VIRTUAL_ENV = $venvPath
    $env:PATH = "$venvPath\Scripts;$env:PATH"
    Write-Host "✅ Virtual environment configured" -ForegroundColor Green
}
else {
    Write-Host "📦 Creating new virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & $activateScript
    pip install -e .
    Write-Host "✅ Virtual environment created and activated" -ForegroundColor Green
}

# Convert boolean parameters to strings for Python
$headlessStr = if ($Headless) { "True" } else { "False" }
$keepOpenStr = if ($KeepBrowserOpen) { "True" } else { "False" }
$debugStr = if ($DebugMode) { "True" } else { "False" }
$exportStr = if ($ExportMarkdown) { "True" } else { "False" }

# Escape query for Python string
$escapedQuery = $Query -replace '"', '\"' -replace '\', '\\'

Write-Host "🌐 Starting browser automation..." -ForegroundColor Green

# Python script for direct browser automation
$pythonCode = @"
import sys
import os
from pathlib import Path
import traceback

# Add project root to Python path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

def main():
    try:
        print('🔧 Importing browser automation modules...')
        from src.automation.web_driver import PerplexityWebDriver

        print('🚀 Initializing Perplexity Web Driver...')

        # Configure user data directory
        user_data_dir = None
        if '$Profile' != 'fresh':
            user_data_dir = f'browser_data/$Profile'
            # Create directory if needed
            Path(user_data_dir).mkdir(parents=True, exist_ok=True)

        # Initialize driver
        driver = PerplexityWebDriver(
            headless=$headlessStr,
            user_data_dir=user_data_dir,
            stealth_mode=True
        )

        print('🌍 Starting browser...')
        driver.start(debug_network=$debugStr)

        print('🔗 Navigating to Perplexity.ai...')
        driver.navigate_to_perplexity()

        print('🔍 Executing search...')
        print(f'Query: $escapedQuery')
        print(f'Mode: $SearchMode')

        result = driver.search(
            '$escapedQuery',
            mode='$SearchMode',
            wait_for_response=True,
            structured=True
        )

        # Display results
        print('')
        print('=' * 80)
        print('📊 PERPLEXITY SEARCH RESULTS')
        print('=' * 80)

        if isinstance(result, dict):
            answer = result.get('answer', 'No answer found')
            sources = result.get('sources', [])
            mode = result.get('mode', '$SearchMode')

            print(f'🔍 Search Mode: {mode.upper()}')
            print('')
            print(answer)

            if sources:
                print('')
                print('=' * 60)
                print('📚 SOURCES')
                print('=' * 60)
                for i, source in enumerate(sources[:10], 1):  # Limit to top 10
                    title = source.get('title', 'Unknown Source')
                    url = source.get('url', '')
                    print(f'{i:2d}. {title}')
                    if url:
                        print(f'    🔗 {url}')
                    print()
        else:
            print(str(result))

        print('')
        print('=' * 80)

        # Export if requested
        if $exportStr:
            try:
                print('💾 Exporting to Markdown...')
                export_dir = '$ExportDir' if '$ExportDir' else None
                export_path = driver.export_as_markdown(output_dir=export_dir)
                if export_path:
                    print(f'✅ Exported to: {export_path}')
                else:
                    print('⚠️ Export completed but path not returned')
            except Exception as e:
                print(f'❌ Export failed: {e}')

        # Browser cleanup
        if not $keepOpenStr:
            print('🔄 Closing browser...')
            driver.close()
            print('✅ Browser closed')
        else:
            print('🔓 Browser kept open as requested')
            print('   You can continue using it manually or close it when done.')

        print('')
        print('🎉 Search completed successfully!')
        return True

    except ImportError as e:
        print(f'❌ Import Error: {e}')
        print('')
        print('🔧 SOLUTION:')
        print('   Please ensure all dependencies are installed:')
        print('   pip install -e .')
        print('   playwright install firefox')
        return False

    except Exception as e:
        print(f'❌ Error: {e}')
        if '$debugStr' == 'True':
            print('')
            print('🐛 Debug traceback:')
            traceback.print_exc()
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
"@

# Execute Python script
try {
    Write-Host "🐍 Executing Python automation script..." -ForegroundColor Cyan
    python -c $pythonCode

    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✅ Task completed successfully!" -ForegroundColor Green
    }
    else {
        Write-Host ""
        Write-Host "❌ Task completed with errors (exit code: $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}
catch {
    Write-Host ""
    Write-Host "❌ PowerShell execution error: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
