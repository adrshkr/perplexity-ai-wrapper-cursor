# Grok Chat API Wrapper

A terminal interface for Grok chat with automatic authentication and browser automation.

## Features

- 🔥 **Simple Terminal Command** - Just `grok "your message"`
- 🤖 **Automatic Authentication** - Browser automation handles login and cookie management
- 🍪 **Cookie Persistence** - Saves cookies for future use
- 📡 **Streaming Support** - Real-time response streaming
- 🎨 **Rich Terminal Output** - Beautiful formatted responses
- 🛡️ **Cloudflare Bypass** - Automatic handling via browser automation
- 💾 **Multiple Output Formats** - Text, JSON, Markdown

## Installation

### Quick Install

The Grok wrapper uses the **same Python environment as the Perplexity wrapper** (parent directory's venv).

```bash
# Navigate to parent directory (perplexity-ai-wrapper)
cd ..

# Activate the shared virtual environment
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install Grok wrapper dependencies (if not already installed)
pip install browser-cookie3>=0.19.1

# Install Playwright browsers (if not already installed)
playwright install firefox

# Navigate back to grok_wrapper
cd grok_wrapper
```

**Note:** The wrapper scripts (`grok.ps1`, `grok.sh`, `grok.bat`) automatically use the parent directory's venv, so you don't need to manually activate it.

## Usage

### Basic Chat

```bash
# Using the wrapper script (recommended)
./grok.sh "Hello, how are you?"

# Or using Python directly
python -m src.interfaces.cli chat "Hello, how are you?"

# Or if installed
grok chat "Hello, how are you?"
```

### Streaming Responses

```bash
grok chat "Explain quantum computing" --stream
```

### Save Response to File

```bash
grok chat "Write a Python function" --output response.txt
```

### Different Output Formats

```bash
# JSON format
grok chat "Hello" --format json

# Markdown format
grok chat "Hello" --format markdown

# Text format (default)
grok chat "Hello" --format text
```

### Login and Save Cookies

```bash
# Login interactively (opens browser)
grok login

# Login with profile name
grok login --profile my_account

# Use persistent browser session
grok login --persistent
```

### Use Saved Cookie Profile

```bash
grok chat "Hello" --profile my_account
```

### Headless Mode

```bash
# Run browser in background (no window)
grok chat "Hello" --headless
```

### Persistent Browser Session

```bash
# Use persistent session (cookies persist automatically)
grok chat "Hello" --persistent
```

## Command Reference

### `grok chat`

Send a message to Grok chat.

**Options:**
- `--model, -m`: Model to use (default: grok-4)
- `--stream, -s`: Stream response in real-time
- `--output, -o`: Save response to file
- `--format, -f`: Output format (text, json, markdown)
- `--profile, -p`: Cookie profile to use
- `--headless`: Run browser in headless mode
- `--persistent`: Use persistent browser session
- `--verbose, -v`: Show detailed output
- `--keep-browser-open`: Keep browser open after chat

### `grok login`

Login to Grok and save cookies for future use.

**Options:**
- `--profile, -p`: Profile name to save cookies as
- `--headless`: Run in headless mode (not recommended for login)
- `--persistent`: Use persistent browser session

### `grok list-profiles`

List all saved cookie profiles.

## How It Works

1. **First Time Use**: The wrapper opens a browser for you to login. After login, it saves cookies automatically.

2. **Subsequent Uses**: The wrapper uses saved cookies to make API calls directly. If cookies expire, it automatically falls back to browser automation.

3. **Browser Automation**: When cookies are not available or expired, the wrapper uses Playwright to automate the browser, handle login, and extract responses.

4. **Cookie Management**: Cookies are saved in `~/.grok_cookies/` directory. Each profile is saved as a JSON file.

## Troubleshooting

### "Authentication failed"

- Run `grok login` to refresh your cookies
- Make sure you're logged into Grok in your browser

### "Browser not found"

- Install Playwright browsers: `playwright install firefox`

### "No response received"

- Check your internet connection
- Try running without `--headless` to see what's happening
- Use `--verbose` flag for detailed output

## Examples

```bash
# Simple chat
grok chat "Explain quantum computing"

# Stream response
grok chat "Explain AI" --stream

# Save to file
grok chat "Write code" --output code.txt

# Use specific model
grok chat "Hello" --model grok-4

# Login and save profile
grok login --profile work_account

# Use saved profile
grok chat "Hello" --profile work_account
```

## License

MIT License

