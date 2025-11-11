# Perplexity AI Wrapper - Command Line Interface
# Auto-activates venv and executes Perplexity searches

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,  # Required: Your search query
    [string]$Mode = "api",  # "api" or "browser" (default: api)
    [string]$Profile = "fresh",
    [switch]$Headless,
    [switch]$KeepBrowserOpen,
    [switch]$DebugMode,  # Enable debug logging
    [switch]$ExportMarkdown,  # Export thread as Markdown file after search
    [string]$ExportDir = ""  # Directory to save exported Markdown (default: exports/)
)

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Activate venv if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1 | Out-Null
} else {
    python -m venv venv
    .\venv\Scripts\Activate.ps1 | Out-Null
    pip install -e . | Out-Null
}

if ($Mode -eq "api") {
    python -m src.interfaces.cli search "$Query" --format text
} else {
    # Build command arguments array properly
    $cmdArgs = @("browser-search", "$Query", "--profile", "$Profile")
    
    if ($Headless) { $cmdArgs += "--headless" }
    if ($KeepBrowserOpen) { $cmdArgs += "--keep-browser-open" }
    if ($DebugMode) { $cmdArgs += "--debug" }
    if ($ExportMarkdown) { $cmdArgs += "--export-markdown" }
    if ($ExportDir) { $cmdArgs += "--export-dir"; $cmdArgs += "$ExportDir" }
    
    # Execute with proper argument separation
    & python -m src.interfaces.cli $cmdArgs
}

