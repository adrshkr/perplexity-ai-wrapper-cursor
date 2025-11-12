# Perplexity AI Wrapper - Command Line Interface
# Auto-activates venv and executes Perplexity searches

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,  # Required: Your search query
    [string]$Mode = "browser",  # "api" or "browser" (default: browser for reliability)
    [string]$Profile = "fresh",  # Cookie profile name
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

# Activate venv if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1" | Out-Null
} elseif (Test-Path "venv\Scripts\python.exe") {
    # Alternative activation method
    $env:VIRTUAL_ENV = Join-Path $scriptDir "venv"
    $env:PATH = "$(Join-Path $scriptDir "venv\Scripts");$env:PATH"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    & "venv\Scripts\Activate.ps1" | Out-Null
    pip install -e . | Out-Null
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

    # Build Python command arguments
    $headlessFlag = if ($Headless) { "True" } else { "False" }
    $keepOpenFlag = if ($KeepBrowserOpen) { "True" } else { "False" }
    $debugFlag = if ($DebugMode) { "True" } else { "False" }

    # Create temporary Python script file to avoid interpolation issues
    $tempScript = Join-Path $env:TEMP "perplexity_search.py"

    $pythonCode = @"
import sys
import os
sys.path.insert(0, '.')

def main():
    try:
        from src.automation.web_driver import PerplexityWebDriver

        # Configuration
        headless = $headlessFlag
        keep_open = $keepOpenFlag
        debug_mode = $debugFlag
        query = '''$($Query.Replace("'", "\'"))'''
        search_mode = '$SearchMode'

        if debug_mode:
            print(f'Query: {query}')
            print(f'Search Mode: {search_mode}')
            print(f'Headless: {headless}')
            print(f'Keep Open: {keep_open}')

        # Initialize driver
        driver = PerplexityWebDriver(headless=headless, stealth_mode=True)
        driver.start()
        driver.navigate_to_perplexity()

        # Perform search
        result = driver.search(query, mode=search_mode, wait_for_response=True)

        # Display results
        print('=' * 60)
        print('SEARCH RESULTS')
        print('=' * 60)
        print(result)

        # Handle browser cleanup
        if not keep_open:
            driver.close()
            if debug_mode:
                print('Browser closed')
        else:
            print('Browser kept open as requested')
            print('Press Ctrl+C to close when done')

    except KeyboardInterrupt:
        print('\nSearch interrupted by user')
        try:
            driver.close()
        except:
            pass
        sys.exit(0)
    except Exception as e:
        print(f'Error: {e}')
        if debug_mode:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
"@

    # Write Python script to temp file
    $pythonCode | Out-File -FilePath $tempScript -Encoding UTF8

    try {
        # Execute the temporary Python script
        python $tempScript

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Browser automation failed!" -ForegroundColor Red
            exit 1
        }

        # Handle export if requested
        if ($ExportMarkdown) {
            Write-Host "Export functionality will be implemented in future version" -ForegroundColor Yellow
        }

    } finally {
        # Clean up temp file
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force
        }
    }
}

Write-Host "Search completed!" -ForegroundColor Green
