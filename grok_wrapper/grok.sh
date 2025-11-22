#!/bin/bash
# Grok Chat Wrapper - Command Line Interface (Linux/Mac)
# Auto-activates venv and executes Grok chat

# Usage: ./grok.sh "your message" [options]
# Example: ./grok.sh "Hello, how are you?"
# Example: ./grok.sh "Explain AI" --stream

if [ $# -lt 1 ]; then
    echo "Usage: $0 \"your message\" [options]"
    echo "Example: $0 \"Hello!\""
    echo "Example: $0 \"Explain AI\" --stream"
    exit 1
fi

MESSAGE="$1"
shift  # Remove first argument, rest are options

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Use parent directory's venv (shared with perplexity wrapper)
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PATH="$PARENT_DIR/venv"

# Activate parent venv if it exists
if [ -f "$VENV_PATH/bin/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/bin/activate"
elif [ -f "$VENV_PATH/Scripts/activate" ]; then
    echo "Activating virtual environment..."
    source "$VENV_PATH/Scripts/activate"
else
    echo "Warning: venv not found in parent directory. Creating one..."
    cd "$PARENT_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt -q
    cd "$SCRIPT_DIR"
fi

echo ""
echo "========================================"
echo "Grok Chat Wrapper"
echo "========================================"
echo ""

python -m src.interfaces.cli chat "$MESSAGE" "$@"

echo ""
echo "========================================"
echo "Complete"
echo "========================================"

