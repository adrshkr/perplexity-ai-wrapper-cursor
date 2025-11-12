# Perplexity AI Wrapper - Command Line Interface
# Auto-activates venv and executes Perplexity searches

param(
    [Parameter(Mandatory=$true)]
    [string]$Query,  # Required: Your search query
    [string]$Mode = "api",  # "api" or "browser" (default: api)
    [string]$CookieProfile = "fresh",
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

# Set search mode based on Research flag
if ($Research) {
    $SearchMode = "research"
}

# Activate venv if it exists
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1 | Out-Null
} else {
    python -m venv venv
    .\venv\Scripts\Activate.ps1 | Out-Null
    pip install -e . | Out-Null
}

if ($Mode -eq "api") {
    python -m src.interfaces.cli search "$Query" --format text --mode $SearchMode
} else {
    # Build command arguments array properly
    $cmdArgs = @("browser-search", "$Query", "--profile", "$CookieProfile", "--mode", "$SearchMode")

    if ($Headless) { $cmdArgs += "--headless" }
    if ($KeepBrowserOpen) { $cmdArgs += "--keep-browser-open" }
    if ($DebugMode) { $cmdArgs += "--debug" }
    if ($ExportMarkdown) { $cmdArgs += "--export-markdown" }
    if ($ExportDir) { $cmdArgs += "--export-dir"; $cmdArgs += "$ExportDir" }

    # Execute with proper argument separation
    & python -m src.interfaces.cli $cmdArgs
}
