# Grok Chat Wrapper - Simple PowerShell Script
# Usage: .\grok.ps1 "your message"
# Example: .\grok.ps1 "Hello, how are you?"
# Example: .\grok.ps1 "Explain AI" -Stream
# Example: .\grok.ps1 "Write code" -Output response.txt
# Example: .\grok.ps1 "Hello" -DebugMode
# Example: .\grok.ps1 "Hello" --debug
# Example: .\grok.ps1 "research query" --DeepSearch --private --model expert
# Example: .\grok.ps1 extract-cookies --browser firefox --profile my_account

# Get all arguments before PowerShell tries to parse them
$allArgs = $args

# Change to script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

# Use parent directory's venv (shared with perplexity wrapper)
$parentDir = Split-Path -Parent $scriptDir
$venvPath = Join-Path $parentDir "venv"

# Activate parent venv if it exists
if (Test-Path "$venvPath\Scripts\Activate.ps1") {
    & "$venvPath\Scripts\Activate.ps1" | Out-Null
} elseif (Test-Path "$venvPath\bin\activate") {
    & "$venvPath\bin\activate" | Out-Null
} else {
    Write-Host "Warning: venv not found in parent directory. Creating one..." -ForegroundColor Yellow
    Set-Location $parentDir
    python -m venv venv
    & "venv\Scripts\Activate.ps1" | Out-Null
    pip install -r requirements.txt -q
    Set-Location $scriptDir
}

# Check if we have any arguments
if ($allArgs.Count -eq 0) {
    # No arguments - show help
    Write-Host "Usage: .\grok.ps1 'your message' or .\grok.ps1 <command> [options]" -ForegroundColor Yellow
    Write-Host "Examples:" -ForegroundColor Cyan
    Write-Host "  .\grok.ps1 'Hello, how are you?'" -ForegroundColor White
    Write-Host "  .\grok.ps1 extract-cookies --browser firefox --profile my_account" -ForegroundColor White
    python -m src.interfaces.cli --help
    exit 0
}

# Check if first argument is a known command
$knownCommands = @("extract-cookies", "list-profiles", "login", "chat")
$firstArg = $allArgs[0]

if ($knownCommands -contains $firstArg) {
    # This is a command, pass all arguments through directly
    $cmdArgs = $allArgs
} else {
    # Assume it's a chat message - prepend "chat" command
    $cmdArgs = @("chat") + $allArgs
}

# Execute
python -m src.interfaces.cli $cmdArgs
