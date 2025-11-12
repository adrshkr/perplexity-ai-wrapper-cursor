# Perplexity AI Wrapper - Command Line Interface
# Auto-activates venv and executes Perplexity searches

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,  # Required: Your search query
    [string]$Mode = "browser",  # "api" or "browser" (default: browser for reliability)
    [string]$CookieProfile = "fresh",  # Cookie profile name (renamed from Profile for clarity)
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
    & "venv\Scripts\Activate.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to activate virtual environment" -ForegroundColor Red
        exit 1
    }
} elseif (Test-Path "venv\Scripts\python.exe") {
    # Alternative activation method
    $env:VIRTUAL_ENV = Join-Path $scriptDir "venv"
    $env:PATH = "$(Join-Path $scriptDir "venv\Scripts");$env:PATH"
    Write-Host "Virtual environment activated" -ForegroundColor Green
} else {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
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
        if ($LASTEXITCODE -ne 0) {
            throw "API mode failed"
        }
    } catch {
        Write-Host "API mode failed, switching to browser mode..." -ForegroundColor Yellow
        $Mode = "browser"
    }
}

if ($Mode -eq "browser") {
    Write-Host "Using browser automation..." -ForegroundColor Cyan

    # Convert PowerShell booleans to Python string literals
    $headlessValue = if ($Headless) { "True" } else { "False" }
    $keepOpenValue = if ($KeepBrowserOpen) { "True" } else { "False" }
    $debugValue = if ($DebugMode) { "True" } else { "False" }

    # Escape the query for Python
    $escapedQuery = $Query.Replace('\', '\\').Replace('"', '\"').Replace("'", "\'")

    # Create temporary Python script file to avoid interpolation issues
    $tempScript = Join-Path $env:TEMP "perplexity_search_$(Get-Random).py"

    # Write Python script content to temp file without variable interpolation
    $pythonScriptTemplate = 'import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, ".")

def main():
    try:
        from src.automation.web_driver import PerplexityWebDriver

        # Configuration from PowerShell
        headless = HEADLESS_VALUE
        keep_open = KEEP_OPEN_VALUE
        debug_mode = DEBUG_VALUE
        query = """QUERY_VALUE"""
        search_mode = "SEARCH_MODE_VALUE"
        cookie_profile = "COOKIE_PROFILE_VALUE"

        if debug_mode:
            print(f"Debug: Query = {query}")
            print(f"Debug: Search Mode = {search_mode}")
            print(f"Debug: Cookie Profile = {cookie_profile}")
            print(f"Debug: Headless = {headless}")
            print(f"Debug: Keep Open = {keep_open}")

        print("Initializing browser driver...")
        driver = PerplexityWebDriver(headless=headless, stealth_mode=True)

        print("Starting browser...")
        driver.start()

        print("Navigating to Perplexity...")
        driver.navigate_to_perplexity()

        # Load cookie profile if specified
        if cookie_profile and cookie_profile != "fresh":
            print(f"Loading cookie profile: {cookie_profile}")
            try:
                driver.load_cookie_profile(cookie_profile)
            except Exception as e:
                print(f"Warning: Could not load cookie profile {cookie_profile}: {e}")

        print("Starting search...")
        result = driver.search(query, mode=search_mode, wait_for_response=True)

        print("=" * 60)
        print("SEARCH RESULTS")
        print("=" * 60)
        print(result)

        # Handle browser cleanup
        if not keep_open:
            print("\nClosing browser...")
            driver.close()
            if debug_mode:
                print("Debug: Browser closed")
        else:
            print("\nBrowser kept open as requested")
            print("Press Ctrl+C to close when done")
            input("Press Enter to close browser...")
            driver.close()

        return 0

    except KeyboardInterrupt:
        print("\nSearch interrupted by user")
        try:
            if "driver" in locals():
                driver.close()
        except:
            pass
        return 0
    except ImportError as e:
        print(f"Import Error: {e}")
        print("Make sure all dependencies are installed: pip install -e .")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        if debug_mode:
            print("\nFull traceback:")
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
'

    # Replace placeholders with actual values
    $pythonScript = $pythonScriptTemplate.Replace("HEADLESS_VALUE", $headlessValue)
    $pythonScript = $pythonScript.Replace("KEEP_OPEN_VALUE", $keepOpenValue)
    $pythonScript = $pythonScript.Replace("DEBUG_VALUE", $debugValue)
    $pythonScript = $pythonScript.Replace("QUERY_VALUE", $escapedQuery)
    $pythonScript = $pythonScript.Replace("SEARCH_MODE_VALUE", $SearchMode)
    $pythonScript = $pythonScript.Replace("COOKIE_PROFILE_VALUE", $CookieProfile)

    # Write Python script to temp file
    try {
        $pythonScript | Out-File -FilePath $tempScript -Encoding UTF8
        Write-Host "Created temporary script: $tempScript" -ForegroundColor Gray

        # Execute the temporary Python script
        python $tempScript

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Browser automation failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            exit $LASTEXITCODE
        }

        # Handle export if requested
        if ($ExportMarkdown) {
            Write-Host "Export functionality will be implemented in future version" -ForegroundColor Yellow
        }

    } catch {
        Write-Host "Error executing Python script: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    } finally {
        # Clean up temp file
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
            if ($DebugMode) {
                Write-Host "Cleaned up temporary script" -ForegroundColor Gray
            }
        }
    }
}

Write-Host "Search completed!" -ForegroundColor Green
