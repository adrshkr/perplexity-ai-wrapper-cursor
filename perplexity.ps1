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

# Check if we're already in a virtual environment
if ($env:VIRTUAL_ENV) {
    Write-Host "Virtual environment already active: $env:VIRTUAL_ENV" -ForegroundColor Green
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Green
    & "venv\Scripts\Activate.ps1"
    # Don't exit on activation failure - might already be active
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Virtual environment activation returned non-zero exit code" -ForegroundColor Yellow
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

# Validate Python and dependencies
Write-Host "Validating Python environment..." -ForegroundColor Cyan
python -c "
import sys
print(f'Python: {sys.executable}')
try:
    from src.automation.web_driver import PerplexityWebDriver
    print('✅ PerplexityWebDriver available')
except ImportError as e:
    print(f'❌ Import error: {e}')
    print('Run: pip install -e .')
    sys.exit(1)
"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Python environment validation failed!" -ForegroundColor Red
    Write-Host "Make sure you've installed dependencies: pip install -e ." -ForegroundColor Yellow
    exit 1
}

# Debug output if requested
if ($DebugMode) {
    Write-Host "`nDEBUG: Script Parameters:" -ForegroundColor Yellow
    Write-Host "  Query: $Query" -ForegroundColor Gray
    Write-Host "  Mode: $Mode" -ForegroundColor Gray
    Write-Host "  CookieProfile: $CookieProfile" -ForegroundColor Gray
    Write-Host "  SearchMode: $SearchMode" -ForegroundColor Gray
    Write-Host "  Headless: $Headless" -ForegroundColor Gray
    Write-Host "  KeepBrowserOpen: $KeepBrowserOpen" -ForegroundColor Gray
    Write-Host "  Research: $Research" -ForegroundColor Gray
    Write-Host "  ExportMarkdown: $ExportMarkdown" -ForegroundColor Gray
    Write-Host ""
}

# Set search mode based on Research flag
if ($Research) {
    $SearchMode = "research"
    if ($DebugMode) {
        Write-Host "DEBUG: SearchMode set to 'research' due to -Research flag" -ForegroundColor Yellow
    }
}

if ($Mode -eq "api") {
    Write-Host "Using API mode..." -ForegroundColor Cyan
    if ($DebugMode) {
        Write-Host "DEBUG: Executing API command: python -m src.interfaces.cli search `"$Query`" --format text --mode $SearchMode" -ForegroundColor Yellow
    }
    try {
        python -m src.interfaces.cli search "$Query" --format text --mode $SearchMode
        if ($LASTEXITCODE -ne 0) {
            throw "API mode failed"
        }
    } catch {
        Write-Host "API mode failed, switching to browser mode..." -ForegroundColor Yellow
        if ($DebugMode) {
            Write-Host "DEBUG: API mode error: $($_.Exception.Message)" -ForegroundColor Yellow
        }
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

    if ($DebugMode) {
        Write-Host "DEBUG: Browser mode configuration:" -ForegroundColor Yellow
        Write-Host "  Headless: $headlessValue" -ForegroundColor Gray
        Write-Host "  Keep Open: $keepOpenValue" -ForegroundColor Gray
        Write-Host "  Debug: $debugValue" -ForegroundColor Gray
        Write-Host "  Escaped Query: $escapedQuery" -ForegroundColor Gray
        Write-Host "  Temp Script: $tempScript" -ForegroundColor Gray
    }

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
        if ($DebugMode) {
            Write-Host "DEBUG: Created temporary script: $tempScript" -ForegroundColor Yellow
            Write-Host "DEBUG: Executing: python $tempScript" -ForegroundColor Yellow
        } else {
            Write-Host "Created temporary script and executing..." -ForegroundColor Gray
        }

        # Execute the temporary Python script
        python $tempScript

        if ($LASTEXITCODE -ne 0) {
            Write-Host "Browser automation failed with exit code: $LASTEXITCODE" -ForegroundColor Red
            if ($DebugMode) {
                Write-Host "DEBUG: Python script execution failed" -ForegroundColor Yellow
                if (Test-Path $tempScript) {
                    Write-Host "DEBUG: Temp script still exists at: $tempScript" -ForegroundColor Yellow
                }
            }
            exit $LASTEXITCODE
        }

        if ($DebugMode) {
            Write-Host "DEBUG: Python script executed successfully" -ForegroundColor Yellow
        }

        # Handle export if requested
        if ($ExportMarkdown) {
            Write-Host "Export functionality will be implemented in future version" -ForegroundColor Yellow
            if ($DebugMode) {
                Write-Host "DEBUG: Export requested but not yet implemented" -ForegroundColor Yellow
            }
        }

    } catch {
        Write-Host "Error executing Python script: $($_.Exception.Message)" -ForegroundColor Red
        if ($DebugMode) {
            Write-Host "DEBUG: Full exception details:" -ForegroundColor Yellow
            Write-Host $_.Exception.ToString() -ForegroundColor Gray
        }
        exit 1
    } finally {
        # Clean up temp file
        if (Test-Path $tempScript) {
            Remove-Item $tempScript -Force -ErrorAction SilentlyContinue
            if ($DebugMode) {
                Write-Host "DEBUG: Cleaned up temporary script: $tempScript" -ForegroundColor Yellow
            }
        } elseif ($DebugMode) {
            Write-Host "DEBUG: Temporary script already removed or not found" -ForegroundColor Yellow
        }
    }
}

if ($DebugMode) {
    Write-Host "DEBUG: Script execution completed" -ForegroundColor Yellow
}
Write-Host "Search completed!" -ForegroundColor Green
