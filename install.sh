#!/bin/bash
# Perplexity AI Wrapper - Installation Script for Linux/Mac/WSL2
# Creates virtual environment and installs all dependencies

set -e  # Exit on error

echo "==================================="
echo "Perplexity AI Wrapper - Installer"
echo "==================================="
echo ""

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.8+ is required but not found"
    echo "Please install Python 3.8 or later"
    exit 1
fi

# Check for python3-venv package (required for venv on Debian/Ubuntu)
if ! python3 -m venv --help &> /dev/null; then
    echo "[0.5/6] python3-venv not found - checking if we need to install it..."
    if command -v apt-get &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | grep -oP '\d+\.\d+' | head -1)
        echo "Installing python3-venv package..."
        echo "You may be prompted for sudo password"
        sudo apt-get update -qq
        sudo apt-get install -y python3-venv python${PYTHON_VERSION}-venv 2>/dev/null || \
        sudo apt-get install -y python3-venv 2>/dev/null || \
        echo "WARNING: Could not auto-install python3-venv. Please run: sudo apt install python3-venv"
    else
        echo "WARNING: python3-venv may not be available. If venv creation fails, install it manually."
    fi
fi

# Initialize git submodules (for cloudscraper)
if [ -d ".git" ]; then
    echo "[0/6] Initializing git submodules..."
    git submodule update --init --recursive
    if [ $? -ne 0 ]; then
        echo "WARNING: Failed to initialize git submodules (cloudscraper may not be available)"
    fi
fi

# Remove existing venv if it exists (to avoid permission issues)
if [ -d "venv" ]; then
    echo "[0.5/6] Removing existing venv directory..."
    rm -rf venv
fi

# Create virtual environment
echo "[1/6] Creating virtual environment..."
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to create virtual environment"
    echo ""
    echo "If you're on Debian/Ubuntu, try:"
    echo "  sudo apt install python3-venv"
    echo "Or for specific Python version:"
    echo "  sudo apt install python3.10-venv  # Replace 3.10 with your Python version"
    exit 1
fi

# Activate and upgrade pip
echo "[2/6] Activating virtual environment and upgrading pip..."
source venv/bin/activate
pip install --upgrade pip

# Install dependencies
echo "[3/6] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

# Install cloudscraper from submodule (if available)
if [ -d "cloudscraper" ]; then
    echo "[4/6] Installing cloudscraper from submodule..."
    cd cloudscraper
    pip install -e . 2>/dev/null || pip install . 2>/dev/null || echo "WARNING: Could not install cloudscraper from submodule"
    cd ..
else
    echo "[4/6] cloudscraper submodule not found - skipping"
fi

# Install Playwright browser (Firefox/Camoufox)
echo "[5/6] Installing Playwright Firefox browser..."
playwright install firefox
if [ $? -ne 0 ]; then
    echo "WARNING: Failed to install Playwright browser"
    echo "You can install it later with: playwright install firefox"
fi

# Create necessary directories
echo "[6/6] Creating directories..."
mkdir -p logs exports screenshots browser_data

echo ""
echo "==================================="
echo "✓ Installation complete!"
echo "==================================="
echo ""
echo "Next steps:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Test installation: ./perplexity.sh --help"
echo "  3. Run a search: ./perplexity.sh search \"What is AI?\""
echo ""
