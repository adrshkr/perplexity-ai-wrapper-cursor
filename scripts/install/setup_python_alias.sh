#!/bin/bash
# Setup script to alias python3 as python in WSL2
# This makes WSL2 consistent with PowerShell where 'python' works

echo "Setting up python alias for WSL2..."

# Check if python3 exists
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3 first."
    exit 1
fi

# Get the shell config file
if [ -f ~/.bashrc ]; then
    CONFIG_FILE=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    CONFIG_FILE=~/.bash_profile
elif [ -f ~/.zshrc ]; then
    CONFIG_FILE=~/.zshrc
else
    CONFIG_FILE=~/.bashrc
    touch "$CONFIG_FILE"
fi

# Check if alias already exists
if grep -q "alias python=" "$CONFIG_FILE" 2>/dev/null; then
    echo "Python alias already exists in $CONFIG_FILE"
    echo "Current alias:"
    grep "alias python=" "$CONFIG_FILE"
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Remove old alias
        sed -i '/alias python=/d' "$CONFIG_FILE"
    else
        echo "Keeping existing alias. Exiting."
        exit 0
    fi
fi

# Add alias to config file
echo "" >> "$CONFIG_FILE"
echo "# Alias python to python3 (added by perplexity-ai-wrapper setup)" >> "$CONFIG_FILE"
echo "alias python='python3'" >> "$CONFIG_FILE"
echo "alias pip='pip3'" >> "$CONFIG_FILE"

echo "✓ Added python alias to $CONFIG_FILE"
echo ""
echo "To use the alias immediately, run:"
echo "  source $CONFIG_FILE"
echo ""
echo "Or start a new terminal session."
echo ""
echo "You can now use 'python' instead of 'python3' in WSL2!"
echo ""
echo "IMPORTANT: Start a NEW terminal session for the alias to take effect."
echo "Or run: source $CONFIG_FILE"

