#!/bin/bash
# Perplexity AI Wrapper - Command Line Interface (Linux/Mac)
# Auto-activates venv and executes Perplexity searches

# Usage: ./perplexity.sh [mode] "your query" [profile] [headless]
# Example: ./perplexity.sh api "What is AI?" fresh
# Example: ./perplexity.sh browser "How does ML work?" fresh

if [ $# -lt 2 ]; then
    echo "Usage: $0 [api|browser] \"your query\" [profile] [headless]"
    echo "Example: $0 api \"What is artificial intelligence?\""
    echo "Example: $0 browser \"How does machine learning work?\" fresh"
    exit 1
fi

MODE=${1:-"api"}  # "api" or "browser" (default: api)
QUERY=${2}  # Required: Your search query
PROFILE=${3:-"fresh"}
HEADLESS=${4:-""}

# Change to script directory
cd "$(dirname "$0")"

# Activate venv if it exists
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    echo "Activating virtual environment..."
    source venv/Scripts/activate
else
    echo "Warning: venv not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
fi

echo ""
echo "========================================"
echo "Perplexity AI Wrapper"
echo "========================================"
echo ""

if [ "$MODE" = "api" ]; then
    echo "Mode: Direct API Method"
    echo "Query: $QUERY"
    echo ""
    python -m src.interfaces.cli search "$QUERY" --format text
else
    echo "Mode: Browser Automation"
    echo "Query: $QUERY"
    echo "Profile: $PROFILE"
    echo ""
    if [ -n "$HEADLESS" ]; then
        python -m src.interfaces.cli browser-search "$QUERY" --profile "$PROFILE" --headless
    else
        python -m src.interfaces.cli browser-search "$QUERY" --profile "$PROFILE"
    fi
fi

echo ""
echo "========================================"
echo "Complete"
echo "========================================"

