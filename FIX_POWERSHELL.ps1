# PowerShell Script Fixer for Perplexity AI Wrapper
# This script diagnoses and fixes PowerShell parameter issues

[CmdletBinding()]
param(
    [switch]$DiagnoseOnly,
    [switch]$CreateBackup = $true
)

Write-Host "🔧 PowerShell Script Fixer for Perplexity AI Wrapper" -ForegroundColor Green
Write-Host "=" * 60

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $scriptDir

# Check current PowerShell execution policy
$executionPolicy = Get-ExecutionPolicy
Write-Host "Current PowerShell Execution Policy: $executionPolicy" -ForegroundColor Cyan

if ($executionPolicy -eq "Restricted") {
    Write-Host "⚠️  WARNING: PowerShell execution policy is Restricted!" -ForegroundColor Yellow
    Write-Host "   This may cause parameter binding issues."
    Write-Host "   Consider running: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
}

# Function to create a working PowerShell script
function New-WorkingPerplexityScript {
    param(
        [string]$FilePath
    )

    $scriptContent = @'
# Perplexity AI Wrapper - Fixed PowerShell Script
# Created to resolve parameter binding issues

[CmdletBinding()]
param(
    [Parameter(Mandatory=$true, Position=0, HelpMessage="Your search query")]
    [string]$Query,

    [Parameter(HelpMessage="Search mode: api or browser")]
    [ValidateSet("api", "browser")]
    [string]$Mode = "browser",

    [Parameter(HelpMessage="Cookie profile name")]
    [string]$Profile = "fresh",

    [Parameter(HelpMessage="Search type: search, research, or labs")]
    [ValidateSet("search", "research", "labs")]
    [string]$SearchMode = "search",

    [Parameter(HelpMessage="Run browser in headless mode")]
    [switch]$Headless,

    [Parameter(HelpMessage="Keep browser open after search")]
    [switch]$KeepBrowserOpen,

    [Parameter(HelpMessage="Enable debug logging")]
    [switch]$DebugMode,

    [Parameter(HelpMessage="Use research mode for comprehensive analysis")]
    [switch]$Research,

    [Parameter(HelpMessage="Export results as Markdown")]
    [switch]$ExportMarkdown,

    [Parameter(HelpMessage="Directory for exports")]
    [string]$ExportDir = ""
)

# Enhanced error handling
$ErrorActionPreference = "Stop"
trap {
    Write-Host "❌ Error occurred: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Get and set script directory
$ScriptDirectory = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDirectory

Write-Host "🚀 Perplexity AI Wrapper Starting..." -ForegroundColor Green
Write-Host "Query: $Query" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Cyan

# Override search mode if Research flag is set
if ($Research) {
    $SearchMode = "research"
    Write-Host "Research mode enabled - comprehensive analysis activated" -ForegroundColor Yellow
}

# Virtual environment handling
$VenvPath = Join-Path $ScriptDirectory "venv"
$ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"
$PythonExe = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "📦 Setting up Python environment..." -ForegroundColor Yellow

if (Test-Path $ActivateScript) {
    try {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        & $ActivateScript
        Write-Host "✅ Virtual environment activated" -ForegroundColor Green
    }
    catch {
        Write-Host "⚠️  Activation script failed, using alternative method..." -ForegroundColor Yellow
        if (Test-Path $PythonExe) {
            $env:VIRTUAL_ENV = $VenvPath
            $env:PATH = "$VenvPath\Scripts;$env:PATH"
            Write-Host "✅ Environment configured via PATH" -ForegroundColor Green
        }
    }
}
elseif (Test-Path $PythonExe) {
    Write-Host "Using existing virtual environment..." -ForegroundColor Cyan
    $env:VIRTUAL_ENV = $VenvPath
    $env:PATH = "$VenvPath\Scripts;$env:PATH"
    Write-Host "✅ Virtual environment ready" -ForegroundColor Green
}
else {
    Write-Host "Creating new virtual environment..." -ForegroundColor Cyan
    try {
        python -m venv venv
        & $ActivateScript
        Write-Host "Installing dependencies..." -ForegroundColor Cyan
        pip install -e .
        Write-Host "✅ Virtual environment created and configured" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Failed to create virtual environment: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
}

# Prepare parameters for Python script
$HeadlessFlag = if ($Headless) { "True" } else { "False" }
$KeepOpenFlag = if ($KeepBrowserOpen) { "True" } else { "False" }
$DebugFlag = if ($DebugMode) { "True" } else { "False" }
$ExportFlag = if ($ExportMarkdown) { "True" } else { "False" }

# Escape query for safe Python string handling
$SafeQuery = $Query -replace '"', '\"' -replace '\', '\\'

Write-Host "🌐 Starting browser automation..." -ForegroundColor Green

# Create Python automation script
$PythonScript = @"
import sys
import os
from pathlib import Path
import traceback

# Setup Python path
project_root = Path.cwd()
sys.path.insert(0, str(project_root))

def execute_search():
    try:
        print('🔧 Loading browser automation...')
        from src.automation.web_driver import PerplexityWebDriver

        print('🚀 Initializing web driver...')

        # Configure profile directory
        user_data_dir = None
        if '$Profile' != 'fresh':
            profile_dir = Path('browser_data') / '$Profile'
            profile_dir.mkdir(parents=True, exist_ok=True)
            user_data_dir = str(profile_dir)
            print(f'📁 Using profile directory: {user_data_dir}')

        # Initialize driver with configuration
        driver = PerplexityWebDriver(
            headless=$HeadlessFlag,
            user_data_dir=user_data_dir,
            stealth_mode=True
        )

        print('🌍 Starting browser session...')
        driver.start(debug_network=$DebugFlag)

        print('🔗 Navigating to Perplexity.ai...')
        driver.navigate_to_perplexity()

        print('🔍 Executing search query...')
        print(f'   Query: $SafeQuery')
        print(f'   Mode: $SearchMode')

        # Execute the search
        result = driver.search(
            '$SafeQuery',
            mode='$SearchMode',
            wait_for_response=True,
            structured=True
        )

        # Display results
        print('')
        print('=' * 80)
        print('📊 SEARCH RESULTS')
        print('=' * 80)

        if isinstance(result, dict):
            answer = result.get('answer', 'No answer found')
            sources = result.get('sources', [])
            mode_used = result.get('mode', '$SearchMode')

            print(f'🔍 Mode: {mode_used.upper()}')
            print('')
            print(answer)

            if sources:
                print('')
                print('=' * 60)
                print('📚 SOURCES')
                print('=' * 60)
                for i, source in enumerate(sources[:15], 1):
                    title = source.get('title', 'Source')
                    url = source.get('url', '')
                    print(f'{i:2d}. {title}')
                    if url:
                        print(f'    🔗 {url}')
                    print()
        else:
            print(str(result))

        print('=' * 80)

        # Handle markdown export
        if $ExportFlag:
            try:
                print('💾 Exporting to Markdown...')
                export_directory = '$ExportDir' if '$ExportDir' else None
                exported_file = driver.export_as_markdown(output_dir=export_directory)
                if exported_file:
                    print(f'✅ Exported to: {exported_file}')
                else:
                    print('✅ Export completed')
            except Exception as e:
                print(f'⚠️  Export failed: {e}')

        # Browser cleanup
        if not $KeepOpenFlag:
            print('🔄 Closing browser...')
            driver.close()
            print('✅ Browser session closed')
        else:
            print('🔓 Browser kept open for continued use')

        print('')
        print('🎉 Search completed successfully!')
        return True

    except ImportError as e:
        print(f'❌ Import Error: {e}')
        print('')
        print('🔧 SOLUTION NEEDED:')
        print('   Install missing dependencies:')
        print('   pip install -e .')
        print('   playwright install firefox')
        return False

    except Exception as e:
        print(f'❌ Execution Error: {e}')
        if '$DebugFlag' == 'True':
            print('')
            print('🐛 Debug Information:')
            traceback.print_exc()
        print('')
        print('💡 Try running with -DebugMode for more details')
        return False

if __name__ == '__main__':
    success = execute_search()
    sys.exit(0 if success else 1)
"@

    # Execute the Python script
    try {
        Write-Host "🐍 Launching Python automation..." -ForegroundColor Cyan
        python -c $PythonScript

        $ExitCode = $LASTEXITCODE

        if ($ExitCode -eq 0) {
            Write-Host ""
            Write-Host "✅ TASK COMPLETED SUCCESSFULLY!" -ForegroundColor Green
        }
        else {
            Write-Host ""
            Write-Host "❌ Task failed with exit code: $ExitCode" -ForegroundColor Red
            exit $ExitCode
        }
    }
    catch {
        Write-Host ""
        Write-Host "❌ PowerShell execution error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "💡 This may be due to PowerShell execution policy restrictions." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host ""
Write-Host "🎯 PERPLEXITY AI WRAPPER - EXECUTION COMPLETE" -ForegroundColor Green
'@

    # Write the script with proper encoding
    try {
        # Use UTF-8 encoding with Windows line endings
        $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($FilePath, $scriptContent, $utf8NoBom)
        return $true
    }
    catch {
        Write-Host "❌ Failed to write script: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Diagnose existing scripts
Write-Host "🔍 Diagnosing existing PowerShell scripts..." -ForegroundColor Cyan

$existingScripts = @("perplexity.ps1", "perplexity_clean.ps1", "perplexity_fixed.ps1")

foreach ($script in $existingScripts) {
    if (Test-Path $script) {
        Write-Host "📄 Found: $script" -ForegroundColor Green

        # Check file encoding
        $bytes = [System.IO.File]::ReadAllBytes($script)
        if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
            Write-Host "   📝 Encoding: UTF-8 with BOM" -ForegroundColor Yellow
        }
        elseif ($bytes.Length -ge 2 -and $bytes[0] -eq 0xFF -and $bytes[1] -eq 0xFE) {
            Write-Host "   📝 Encoding: UTF-16 LE" -ForegroundColor Yellow
        }
        else {
            Write-Host "   📝 Encoding: UTF-8 or ASCII" -ForegroundColor Green
        }

        # Check for Profile parameter
        $content = Get-Content $script -Raw
        if ($content -match '\$Profile') {
            Write-Host "   ✅ \$Profile parameter found" -ForegroundColor Green
        }
        else {
            Write-Host "   ❌ \$Profile parameter missing" -ForegroundColor Red
        }
    }
    else {
        Write-Host "📄 Not found: $script" -ForegroundColor Gray
    }
}

if ($DiagnoseOnly) {
    Write-Host ""
    Write-Host "🔍 Diagnosis complete. Use without -DiagnoseOnly to create fixes." -ForegroundColor Cyan
    exit 0
}

# Create backup if requested
if ($CreateBackup -and (Test-Path "perplexity.ps1")) {
    $backupName = "perplexity_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').ps1"
    Copy-Item "perplexity.ps1" $backupName
    Write-Host "💾 Created backup: $backupName" -ForegroundColor Green
}

# Create the fixed script
Write-Host ""
Write-Host "🛠️  Creating fixed PowerShell script..." -ForegroundColor Yellow

$newScriptPath = "perplexity_FIXED.ps1"
$success = New-WorkingPerplexityScript -FilePath $newScriptPath

if ($success) {
    Write-Host "✅ Created working script: $newScriptPath" -ForegroundColor Green
    Write-Host ""
    Write-Host "🧪 TEST YOUR COMMAND:" -ForegroundColor Cyan
    Write-Host "   .\perplexity_FIXED.ps1 `"crypto market update`" -Profile fresh -Research -DebugMode" -ForegroundColor White
    Write-Host ""
    Write-Host "📋 If this works, you can replace the original:" -ForegroundColor Cyan
    Write-Host "   Copy-Item perplexity_FIXED.ps1 perplexity.ps1 -Force" -ForegroundColor White
}
else {
    Write-Host "❌ Failed to create fixed script" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎯 PowerShell fix complete!" -ForegroundColor Green
Write-Host "   Your original command should now work with the _FIXED version." -ForegroundColor Cyan
