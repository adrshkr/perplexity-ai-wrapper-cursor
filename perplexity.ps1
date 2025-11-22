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

# Handle SearchMode and Research flag conflict
# Check if SearchMode was explicitly provided (not just using default)
$SearchModeExplicitlySet = $PSBoundParameters.ContainsKey('SearchMode')

# Set search mode based on Research flag
if ($Research) {
    # If SearchMode was explicitly set to something other than "research", warn user
    if ($SearchModeExplicitlySet -and $SearchMode -ne "research") {
        Write-Warning "Both -SearchMode ($SearchMode) and -Research flag were provided. -Research flag takes precedence and will use 'research' mode."
    }
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
    # Map browser search modes to API search modes
    # API modes: 'auto', 'pro', 'reasoning', 'deep_research'
    # Browser modes: 'search', 'research', 'labs'
    $ApiMode = switch ($SearchMode) {
        "search"   { "auto" }
        "research" { "deep_research" }
        "labs"     { "reasoning" }
        default    { "auto" }
    }
    python -m src.interfaces.cli search "$Query" --format text --mode $ApiMode
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
