# Perplexity AI Wrapper - Usage Guide

## Quick Start

### Windows PowerShell

```powershell
# Use the wrapper script
.\perplexity.ps1 search "your query here"

# Or use batch script
.\perplexity.bat search "your query here"

# Direct Python command (if venv is activated)
python -m src.interfaces.cli search "your query here"
```

### Ubuntu/WSL2

```bash
# Use the wrapper script
./perplexity.sh search "your query here"

# Direct Python command (if venv is activated)
python3 -m src.interfaces.cli search "your query here"
```

## Installation

### Windows PowerShell

```powershell
# Run the installer
.\install.bat
```

### Ubuntu/WSL2

```bash
# Run the installer
bash install.sh

# Make sure Google Chrome is installed
sudo apt-get install google-chrome-stable
```

## Available Commands

### Search Commands

All these commands work on both Windows PowerShell and Ubuntu/WSL2:

```bash
# API mode (fast, direct API call)
python -m src.interfaces.cli search "How far is Saturn from earth on average?"

# Interactive browser mode (browser opens, stays open)
python -m src.interfaces.cli search "How far is Saturn from earth on average?" --interactive

# Headless browser mode (no visible browser)
python -m src.interfaces.cli search "How far is Saturn from earth on average?" --headless

# Using wrapper scripts (after installation)
perplexity search "How far is Saturn from earth on average?"
perplexity search "How far is Saturn from earth on average?" --interactive
perplexity search "How far is Saturn from earth on average?" --headless
```

### Browser Automation

The system automatically uses Google Chrome (not Chromium) for browser automation. If Chrome is not installed, it falls back to Chromium.

## Modes

1. **API Mode** (default): Fast, direct API calls with Cloudflare bypass
2. **Interactive Browser Mode** (`--interactive`): Browser opens, performs search, stays open
3. **Headless Browser Mode** (`--headless`): Browser runs in background, no GUI

## Automatic Fallback

If API mode fails (e.g., Cloudflare blocking), the system automatically falls back to browser automation.

## Notes

- On Windows PowerShell, use `.\perplexity.ps1` or `.\perplexity.bat`
- On Ubuntu/WSL2, use `./perplexity.sh`
- Make sure Google Chrome is installed for best browser automation experience
- The system will automatically fall back to Chromium if Chrome is not available

