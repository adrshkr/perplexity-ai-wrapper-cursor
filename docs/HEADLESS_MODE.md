# Headless Mode Guide

## Overview
The Perplexity AI Wrapper supports headless browser automation, allowing you to run queries without displaying a browser window. This is perfect for:
- Server environments
- Background automation tasks
- CI/CD pipelines
- Terminal-only workflows

## Features

### Platform-Optimized Headless Support
- **Linux**: Uses Camoufox virtual display mode (best stealth)
- **Windows/Mac**: Uses Camoufox regular headless mode
- **Automatic Detection**: Platform is detected automatically

### Logging & Debug Support
All headless operations include comprehensive logging:
- Browser initialization status
- Platform detection
- Headless mode confirmation
- Error handling with detailed messages

## Usage

### PowerShell (Windows)

```powershell
# Basic headless search
.\perplexity.ps1 -Query "your query" -Mode browser -Profile fresh -Headless

# With debug logging
.\perplexity.ps1 -Query "your query" -Mode browser -Profile fresh -Headless -DebugMode

# Headless with output to file
.\perplexity.ps1 -Query "your query" -Mode browser -Profile fresh -Headless > output.txt
```

### Python CLI

```bash
# Basic headless search
python -m src.interfaces.cli browser-search "your query" --profile fresh --headless

# With debug mode
python -m src.interfaces.cli browser-search "your query" --profile fresh --headless --debug

# Headless with persistent profile
python -m src.interfaces.cli browser-search "your query" --persistent --headless
```

### Bash (Linux/Mac)

```bash
# Basic headless search
./perplexity.sh "your query" --mode browser --profile fresh --headless

# With debug output
./perplexity.sh "your query" --mode browser --profile fresh --headless --debug
```

## Technical Details

### Camoufox Integration

The wrapper automatically uses the best headless mode based on your platform:

**Linux (Virtual Display):**
```python
Camoufox(headless="virtual")
```
- Runs browser in Xvfb virtual display
- Best stealth characteristics
- Full rendering capabilities
- Recommended for production servers

**Windows/Mac (Regular Headless):**
```python
Camoufox(headless=True)
```
- Standard headless mode
- Good stealth characteristics
- Lower resource usage
- No display server required

### Logging Levels

**Normal Mode:**
```
Running in headless mode (no browser window)
```

**Debug Mode:**
```
Running in headless mode (no browser window)
Headless mode uses virtual display - browser runs in background
DEBUG: Using Camoufox for better Cloudflare evasion (mode: headless)
INFO: Camoufox running in headless mode (Windows/Mac)
DEBUG: Camoufox instance created successfully with headless=True
DEBUG: Camoufox browser instance acquired
```

## Requirements

### All Platforms
- Camoufox installed: `pip install camoufox`
- Playwright installed: `pip install playwright`

### Linux (for Virtual Display)
Virtual display mode works out-of-the-box on Linux with Camoufox.

### Windows/Mac
Standard headless mode requires no additional dependencies.

## Examples

### Example 1: Simple Headless Query
```powershell
PS> .\perplexity.ps1 -Query "What is quantum computing?" -Mode browser -Headless -Profile fresh

Running in headless mode (no browser window)
✓ Loaded profile: fresh
✓ Browser started successfully
Navigating to Perplexity...

 ANSWER 
Quantum computing is a revolutionary approach to computation...
```

### Example 2: Batch Headless Queries
```bash
# Run multiple queries in headless mode
python -m src.interfaces.cli browser-batch \
  "quantum computing" \
  "artificial intelligence" \
  "machine learning" \
  --profile fresh \
  --headless \
  --max-concurrent 3
```

### Example 3: Headless with Debug
```powershell
PS> .\perplexity.ps1 -Query "test query" -Mode browser -Headless -DebugMode -Profile fresh

Running in headless mode (no browser window)
Headless mode uses virtual display - browser runs in background
DEBUG: Using Camoufox for better Cloudflare evasion (mode: headless)
INFO: Camoufox running in headless mode (Windows/Mac)
...
```

## Best Practices

### 1. Use Persistent Profiles
For repeated headless usage, use persistent profiles to avoid re-authenticating:

```powershell
# First run (login once)
.\perplexity.ps1 -Query "test" -Mode browser -Profile myprofile

# Subsequent runs (headless)
.\perplexity.ps1 -Query "your query" -Mode browser -Profile myprofile -Headless
```

### 2. Enable Debug Mode When Troubleshooting
If headless mode isn't working, use `-DebugMode` to see detailed logs:

```powershell
.\perplexity.ps1 -Query "test" -Mode browser -Headless -DebugMode -Profile fresh
```

### 3. Combine with Output Redirection
For automation scripts:

```powershell
.\perplexity.ps1 -Query "market analysis" -Mode browser -Headless -Profile fresh > report.txt
```

### 4. Use in CI/CD Pipelines
Example GitHub Actions workflow:

```yaml
- name: Run Perplexity Query
  run: |
    python -m src.interfaces.cli browser-search \
      "latest tech news" \
      --profile ci_profile \
      --headless \
      --output results.txt
```

## Troubleshooting

### Issue: "Virtual display is only supported on Linux"
**Solution**: This is expected on Windows/Mac. The wrapper automatically falls back to regular headless mode.

### Issue: Browser window still appears
**Verify flag is set:**
```powershell
# Correct
.\perplexity.ps1 -Query "test" -Mode browser -Headless

# Wrong (missing -Headless)
.\perplexity.ps1 -Query "test" -Mode browser
```

### Issue: Headless mode fails to start
**Check Camoufox installation:**
```bash
pip install --upgrade camoufox
python -c "from camoufox.sync_api import Camoufox; print('OK')"
```

### Issue: Can't login in headless mode
**Solution**: Login first without headless, then use headless mode:
```powershell
# Step 1: Login (browser visible)
.\perplexity.ps1 -Query "test" -Mode browser -Profile myprofile

# Step 2: Use headless (login persisted)
.\perplexity.ps1 -Query "real query" -Mode browser -Profile myprofile -Headless
```

## Performance

Headless mode offers several benefits:

| Metric | Headed Mode | Headless Mode | Improvement |
|--------|-------------|---------------|-------------|
| **Memory Usage** | ~300-400 MB | ~200-300 MB | 25-33% less |
| **CPU Usage** | Higher (rendering) | Lower (no rendering) | 20-30% less |
| **Startup Time** | Same | Same | No difference |
| **Query Speed** | Same | Same | No difference |

**Note**: Startup time is dominated by Cloudflare challenge solving (~5-10s), not browser initialization.

## Limitations

1. **No Visual Debugging**: Can't see what's happening (use debug logs instead)
2. **Login Challenges**: Can't handle interactive login (use persistent profiles)
3. **Screenshot Issues**: Screenshots not available in true headless mode
4. **Platform Differences**: Virtual display only works on Linux

## Comparison

| Feature | Headed Mode | Headless Mode |
|---------|-------------|---------------|
| Browser Window | ✅ Visible | ❌ No window |
| Debug Visibility | ✅ Can see page | ❌ Logs only |
| Resource Usage | ⚠️ Higher | ✅ Lower |
| Server Suitable | ❌ No | ✅ Yes |
| Interactive Login | ✅ Yes | ❌ No |
| CI/CD Ready | ❌ No | ✅ Yes |
| Stealth (Linux) | ⚠️ Good | ✅ Excellent |

## See Also

- [Camoufox Virtual Display Documentation](https://camoufox.com/python/virtual-display/)
- [Performance Optimizations](PERFORMANCE_OPTIMIZATIONS.md)
- Main README for general usage

---

*Last Updated: 2025-11-09*
*Camoufox Version: Latest*
