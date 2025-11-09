# Platform Setup Guide

Complete setup instructions for Windows PowerShell and Ubuntu/WSL2.

## Windows PowerShell Setup

### Installation
```powershell
# Run installer
.\install.bat
```

### Usage
```powershell
# Use wrapper scripts (recommended)
.\perplexity.ps1 search "your query"
.\perplexity.ps1 search "your query" --interactive
.\perplexity.ps1 search "your query" --headless

# Or use batch script
.\perplexity.bat search "your query"

# Direct Python command (if venv activated)
python -m src.interfaces.cli search "your query"
```

### Install as Global Command (Optional)
```powershell
# Activate venv
.\venv\Scripts\Activate.ps1

# Install in development mode
pip install -e .

# Now you can use 'perplexity' directly
perplexity search "your query"
```

## Ubuntu/WSL2 Setup

### Installation
```bash
# Run installer
bash install.sh
```

### Install Google Chrome

**Method 1: Add Repository (Recommended)**
```bash
# Download and add Google's signing key
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -

# Add Google Chrome repository
echo 'deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main' | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Update package list
sudo apt-get update

# Install Google Chrome
sudo apt-get install google-chrome-stable
```

**Method 2: Download and Install Manually**
```bash
# Download Chrome .deb package
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb

# Install the package
sudo apt install ./google-chrome-stable_current_amd64.deb

# Clean up
rm google-chrome-stable_current_amd64.deb
```

**Method 3: Use Chromium (Fallback)**
```bash
sudo apt-get install chromium-browser
```
*Note: System automatically falls back to Chromium if Chrome is not available.*

### Python Alias Setup (Optional)

To use `python` instead of `python3` (consistent with PowerShell):
```bash
# Run setup script
bash setup_python_alias.sh

# Or manually add to ~/.bashrc
echo "alias python='python3'" >> ~/.bashrc
echo "alias pip='pip3'" >> ~/.bashrc
source ~/.bashrc
```

### Usage
```bash
# Use wrapper script (recommended)
./perplexity.sh search "your query"
./perplexity.sh search "your query" --interactive
./perplexity.sh search "your query" --headless

# Direct Python command (if venv activated)
python -m src.interfaces.cli search "your query"
# Or if alias is set up:
python -m src.interfaces.cli search "your query"
```

### Install as Global Command (Optional)
```bash
# Activate venv
source venv/bin/activate

# Install in development mode
pip install -e .

# Now you can use 'perplexity' directly
perplexity search "your query"
```

## Browser Modes

### Default Mode
```bash
# Shows browser if login needed, closes after search
perplexity search "your query"
```

### Headless Mode (Terminal Only)
```bash
# No browser window, only terminal output
# Requires login first (use default mode once to login)
perplexity search "your query" --headless
```

### Interactive Mode (Browser Stays Open)
```bash
# Browser visible, stays open after search
perplexity search "your query" --interactive
# Or
perplexity search "your query" --keep-browser-open
```

## Troubleshooting

### PowerShell: "perplexity not recognized"
- Use `.\perplexity.ps1` or `.\perplexity.bat` instead
- Or install globally: `pip install -e .` (after activating venv)

### Ubuntu: "permission denied"
```bash
chmod +x perplexity.sh
./perplexity.sh search "query"
```

### Chrome not found
- Install Google Chrome (see above)
- System will automatically fallback to Chromium

### WSL2: "E: Unable to locate package google-chrome-stable"
- Use Method 1 to add the repository first
- Or use Method 2 (manual download)
- Or use Method 3 (Chromium)

### WSL2 Display Issues
- Chrome needs X11 display server: `sudo apt-get install xvfb`
- Or use headless mode: `--headless` flag
