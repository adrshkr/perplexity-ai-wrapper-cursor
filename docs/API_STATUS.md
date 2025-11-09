# API Status & Cloudflare Protection

## Current Status

### ✅ Working
- **Browser Automation**: Fully functional with persistent context
- **Direct API Calls with Cloudscraper**: Now working reliably with automatic Cloudflare bypass
- **Endpoint Discovered**: `/rest/sse/perplexity_ask` (confirmed working)
- **Cloudflare Bypass**: Integrated cloudscraper for automatic challenge solving

### ⚠️ Limited/Unreliable
- **Direct API Calls without Cloudscraper**: Still blocked by Cloudflare protection
- **Cookie-Based Authentication**: Cookies expire quickly (`cf_clearance` expires in 30min-2hrs)

## Why API Calls Are Blocked

Cloudflare uses advanced detection that checks:
1. **Browser Fingerprint**: TLS fingerprint, HTTP/2 fingerprint, TLS version
2. **Behavioral Patterns**: Request timing, header order, connection patterns
3. **Cookie Freshness**: `cf_clearance` cookies expire quickly
4. **JavaScript Challenge**: May require solving challenges that browsers handle automatically

**Direct HTTP requests from Python `requests` library cannot fully mimic browser behavior**, which is why Cloudflare blocks them.

## Solutions

### ✅ Option 1: Direct API with Cloudscraper (Recommended - Fast)

**Direct API calls now work reliably** with cloudscraper integration:

```bash
# Automatic cloudflare bypass (default)
perplexity search "your query"

# With proxy rotation for better reliability
perplexity search "your query" --proxy http://proxy1:8080

# Disable cloudflare bypass (if needed)
perplexity search "your query" --no-cloudflare-bypass
```

**Benefits:**
- ✅ Fast (no browser overhead)
- ✅ Automatic Cloudflare challenge solving
- ✅ Stealth mode reduces detection
- ✅ Proxy rotation support
- ✅ Works reliably in most cases

**How it works:**
- Uses `cloudscraper` library to solve Cloudflare challenges automatically
- Emulates browser behavior (TLS fingerprint, headers, timing)
- Handles v1, v2, v3, and Turnstile challenges
- Extracts and manages `cf_clearance` cookies automatically

### ✅ Option 2: Use Browser Automation (Most Reliable)

**Browser automation works perfectly** because it uses a real browser:

```bash
# Persistent context (recommended)
.\perplexity.bat browser --persistent

# Or with profile
.\perplexity.bat browser --profile my_account

# Headless mode with cloudscraper pre-authentication
perplexity search "your query" --headless
```

**Benefits:**
- ✅ Always works (bypasses Cloudflare)
- ✅ Cookies persist automatically
- ✅ No Cloudflare challenges
- ✅ Most reliable method
- ✅ Enhanced with cloudscraper pre-authentication for headless mode

### ⚠️ Option 3: Direct API without Cloudscraper (Unreliable)

Direct API calls **may work temporarily** with very fresh cookies (only if cloudscraper is disabled):

```bash
# 1. Extract VERY fresh cookies (just logged in)
.\perplexity.bat cookies extract --browser chrome --profile fresh

# 2. Use immediately (within minutes) without cloudscraper
perplexity search "your query" --profile fresh --no-cloudflare-bypass
```

**Limitations:**
- ❌ Cookies expire quickly (30min-2hrs)
- ❌ Cloudflare may still block even with fresh cookies
- ❌ Requires frequent cookie refresh
- ❌ Not reliable for production use
- ⚠️ **Not recommended** - use cloudscraper instead

## Recommendations

### For Development/Testing
✅ **Use direct API with cloudscraper** - Fast and reliable

### For Production
✅ **Use direct API with cloudscraper** - Fast, reliable, and efficient
✅ **Fallback to browser automation** - If cloudscraper fails or for maximum reliability

### For API Integration
✅ **Use cloudscraper integration** - Automatic Cloudflare bypass
✅ **Enable proxy rotation** - For better reliability and IP rotation
✅ **Use stealth mode** - Reduces detection (enabled by default)

## Technical Details

### Required Cookies
- `cf_clearance` - Cloudflare challenge cookie (expires quickly)
- `__cf_bm` - Cloudflare bot management cookie
- `__Secure-next-auth.session-token` - Perplexity session token

### Required Headers
- `User-Agent`: Must match browser
- `Accept`: `text/event-stream` for SSE
- `Origin`: `https://www.perplexity.ai`
- `Referer`: `https://www.perplexity.ai/`
- `Sec-Fetch-*` headers: Must match browser patterns

### Why It Fails
Even with all correct headers and cookies, Cloudflare checks:
- TLS fingerprint (Python requests ≠ Chrome TLS)
- HTTP/2 fingerprint (connection patterns)
- Request timing (automation patterns detectable)
- JavaScript execution (challenges require JS)

## Cloudscraper Integration

The wrapper now includes **cloudscraper** integration for automatic Cloudflare bypass:

### Features
- **Automatic Challenge Solving**: Handles Cloudflare v1, v2, v3, and Turnstile challenges
- **Stealth Mode**: Human-like delays, header randomization, browser quirks
- **Proxy Rotation**: Support for rotating proxies to avoid IP blocks
- **Session Management**: Automatic session refresh on 403 errors
- **Cookie Extraction**: Extracts `cf_clearance` and other Cloudflare cookies automatically

### Configuration

Configure in `config.yaml`:
```yaml
cloudflare_bypass:
  enabled: true
  stealth_mode: true
  interpreter: js2py  # Options: js2py, nodejs, native
  auto_refresh_on_403: true
  max_403_retries: 3
  proxy_rotation: []  # Optional list of proxy URLs
```

### Updating Cloudscraper

Keep cloudscraper updated for latest bypass techniques:
```bash
python scripts/update_cloudscraper.py
# Or manually:
git submodule update --remote cloudscraper
```

## Conclusion

**Direct API calls with cloudscraper are now the recommended solution** because:
1. ✅ Fast (no browser overhead)
2. ✅ Automatic Cloudflare bypass
3. ✅ Reliable in most cases
4. ✅ Stealth mode reduces detection
5. ✅ Proxy rotation support

**Browser automation remains the most reliable fallback** for:
- Maximum reliability when cloudscraper fails
- Complex scenarios requiring full browser interaction
- When you need persistent sessions with manual login

