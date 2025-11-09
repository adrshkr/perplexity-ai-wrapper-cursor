# Cookie Extraction & Browser Automation Guide

This guide explains how to extract fresh cookies from Perplexity and use them for browser automation.

## Overview

The Perplexity wrapper now supports multiple methods for extracting and managing cookies:

1. **Playwright CDP (Chrome DevTools Protocol)** - Direct cookie extraction from browser
2. **Browser MCP (Model Context Protocol)** - Browser automation via MCP extension
3. **Manual extraction** - Using browser_cookie3 library
4. **Automatic extraction** - Built into PerplexityWebDriver

## Methods

### Method 1: Using CDP Extraction Script (Recommended)

The `extract_cookies_with_cdp.py` script uses Playwright's Chrome DevTools Protocol to extract cookies directly from a running browser session.

```bash
# Extract cookies and save to profile
python extract_cookies_with_cdp.py --profile my_account

# Extract and test automation
python extract_cookies_with_cdp.py --profile my_account --test

# Extract with custom test query
python extract_cookies_with_cdp.py --profile my_account --test --test-query "What is AI?"
```

**Features:**
- Uses CDP for reliable cookie extraction
- Waits for user login interactively
- Automatically saves cookies to profile
- Optional testing of browser automation
- Shows important cookies (session tokens, Cloudflare cookies)

### Method 2: Using CLI Cookie Extraction

The CLI also provides cookie extraction functionality:

```bash
# Extract cookies using CLI
python -m src.interfaces.cli cookies extract --profile my_account
```

**Features:**
- Integrated with the main CLI
- Profile management
- Automatic cookie validation

### Method 3: Using PerplexityWebDriver Directly

You can also extract cookies programmatically using the `PerplexityWebDriver` class:

```python
from src.automation.web_driver import PerplexityWebDriver

# Create driver
driver = PerplexityWebDriver(headless=False, stealth_mode=True)
driver.start()

# Navigate and login
driver.navigate_to_perplexity()
# ... login manually ...

# Extract cookies
cookies = driver.extract_cookies()

# Save to profile
driver.save_cookies_to_profile("my_profile")

# Close
driver.close()
```

## Using Extracted Cookies

Once cookies are extracted and saved to a profile, you can use them in several ways:

### 1. Command Line Interface

```bash
# Search with profile
perplexity search "your query" --profile my_account

# Browser mode with profile
perplexity browser --profile my_account

# Headless browser with profile
perplexity search "your query" --profile my_account --headless
```

### 2. Programmatic Usage

```python
from src.auth.cookie_manager import CookieManager
from src.automation.web_driver import PerplexityWebDriver

# Load cookies from profile
cookie_manager = CookieManager()
cookies = cookie_manager.load_cookies(name="my_account")

# Use with browser automation
driver = PerplexityWebDriver(headless=False, stealth_mode=True)
driver.set_cookies(cookies)
driver.start()
driver.navigate_to_perplexity()

# Run search
result = driver.search("What is AI?", structured=True)
print(result['answer'])

driver.close()
```

## Important Cookies

The following cookies are important for Perplexity authentication:

- `__Secure-next-auth.session-token` - Main authentication token
- `next-auth.session-token` - Alternative session token
- `cf_clearance` - Cloudflare clearance cookie
- `__cf_bm` - Cloudflare bot management cookie
- `pplx.default-search-session` - Perplexity search session
- `CF_AppSession` - Cloudflare app session

## Troubleshooting

### No Cookies Extracted

1. **Make sure you're logged in**: Open Perplexity in your browser and verify you're logged in
2. **Close browser completely**: Make sure Chrome/Edge is fully closed (check Task Manager)
3. **Try different browser**: Use Chrome, Edge, or Firefox
4. **Check profile path**: If using custom profile, verify the path is correct

### Cookies Expired

Cookies expire after some time. To refresh:

1. Re-extract cookies using one of the methods above
2. Or use persistent browser context (user_data_dir) which maintains cookies automatically

### Login Modal Appears

If login modal appears when using cookies:

1. Cookies may be expired - extract fresh cookies
2. Session token may be invalid - re-login and extract
3. Try using persistent browser context instead

### Cloudflare Blocking

If Cloudflare is blocking:

1. Use `--stealth-mode` (enabled by default)
2. Use cloudscraper pre-authentication (automatic in PerplexityWebDriver)
3. Extract fresh `cf_clearance` cookie
4. Use persistent browser context

## Best Practices

1. **Use persistent browser context** for long-running sessions:
   ```python
   driver = PerplexityWebDriver(
       headless=False,
       user_data_dir="browser_data/my_account",
       stealth_mode=True
   )
   ```

2. **Extract fresh cookies regularly** - Session tokens expire

3. **Save cookies to named profiles** - Makes it easy to switch accounts

4. **Test after extraction** - Always verify cookies work before using in production

5. **Use headless mode carefully** - Some features require visible browser

## Examples

### Example 1: Extract and Use

```bash
# Step 1: Extract cookies
python extract_cookies_with_cdp.py --profile production

# Step 2: Use in search
perplexity search "What is machine learning?" --profile production
```

### Example 2: Complete Workflow

```bash
# Run complete workflow test
python extract_cookies_with_cdp.py --profile test_account --test

# This will:
# - Extract cookies
# - Save to profile
# - Test automation
# - Verify everything works
```

### Example 3: Programmatic Extraction

```python
from src.automation.web_driver import PerplexityWebDriver

driver = PerplexityWebDriver(headless=False)
driver.start()
driver.navigate_to_perplexity()

# Wait for login (manual)
input("Press Enter after logging in...")

# Extract and save
driver.save_cookies_to_profile("my_account")
driver.close()

# Now use the profile
from src.auth.cookie_manager import CookieManager
cm = CookieManager()
cookies = cm.load_cookies("my_account")
```

## Advanced: Using Browser MCP Extension

If you have the browser MCP extension available, you can use it for automation:

```python
# This would use MCP browser extension if available
# Currently, the scripts use Playwright directly
# MCP integration can be added for enhanced automation
```

## See Also

- `LOGIN_VERIFICATION_FLOW.md` - Detailed login flow documentation
- `docs/ENHANCED_BROWSER_USAGE.md` - Browser automation guide
- `docs/API_STATUS.md` - API and authentication status

