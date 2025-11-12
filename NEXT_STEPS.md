# Next Steps: Finding Selectors for Mode Buttons and Export Button

> **⚠️ IMPORTANT:** Use the `_simple.py` versions of discovery scripts:
> - `tools/discover_mode_buttons_simple.py`  
> - `tools/discover_export_button_simple.py`  
> 
> These use `PerplexityWebDriver` with **Camoufox for Cloudflare bypass** (same as main app).

## Current Status

The Research and Labs mode implementation is **INCOMPLETE**. Both the mode selection logic and native export button require **actual selectors** from the Perplexity UI, which must be discovered using the provided tools.

## Why Selectors Are Not Included

I initially attempted to guess selectors based on common patterns, which was **incorrect**. Instead of guessing, we need to:

1. Run the discovery tool with a logged-in session
2. Inspect the actual HTML elements
3. Get exact selectors (class names, IDs, data attributes)
4. Update `web_driver.py` with those exact selectors

## How to Find the Selectors

### Part A: Mode Toggle Buttons (Search/Research/Labs)

#### Step 1: Run the Mode Discovery Script

```bash
# Activate virtual environment
.\venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Run discovery tool
python tools/discover_mode_buttons.py
```

### Step 2: What the Script Does

**Authentication:**
- Checks for saved cookie profiles and lets you choose one
- Automatically injects cookies for seamless login
- Falls back to browser profile if no cookies available

**Discovery:**
1. Opens Firefox and injects authentication cookies
2. Navigates to Perplexity.ai (already logged in if cookies valid)
3. Automatically checks login status
4. Extracts HTML structure around the search box
5. Lists all clickable elements (buttons, tabs, etc.)
6. Saves findings to `logs/mode_discovery.json`
7. Takes a screenshot to `screenshots/mode_buttons_discovery.png`

### Step 3: Manual Inspection

While the browser is open:

1. Look for the mode toggle buttons (Search / Research / Labs)
2. Right-click on each button → "Inspect Element"
3. Note the exact selector for each:
   - Look for `id` attribute (e.g., `id="research-button"`)
   - Look for `class` names (e.g., `class="mode-toggle active"`)
   - Look for `data-*` attributes (e.g., `data-testid="research-mode"`)
   - Look for `role` attribute (e.g., `role="tab"`)

### Step 4: Check the Output

After the script completes, check:

1. **Terminal output** - shows all buttons found near search
2. **`logs/mode_discovery.json`** - full data dump with HTML
3. **`screenshots/mode_buttons_discovery.png`** - visual reference

#### Step 5: Update the Code for Mode Buttons

Open `src/automation/web_driver.py` and find this section (around line 1171):

```python
mode_selectors = {
    'search': None,  # TODO: Add actual selector from discovery
    'research': None,  # TODO: Add actual selector from discovery  
    'labs': None  # TODO: Add actual selector from discovery
}
```

Replace `None` with the actual selectors you found. Examples:

```python
# Example 1: Using ID
mode_selectors = {
    'search': '#search-mode-button',
    'research': '#research-mode-button',
    'labs': '#labs-mode-button'
}

# Example 2: Using class
mode_selectors = {
    'search': 'button.mode-toggle[data-mode="search"]',
    'research': 'button.mode-toggle[data-mode="research"]',
    'labs': 'button.mode-toggle[data-mode="labs"]'
}

# Example 3: Using role + text (if unique)
mode_selectors = {
    'search': '[role="tab"]:has-text("Search")',
    'research': '[role="tab"]:has-text("Research")',
    'labs': '[role="tab"]:has-text("Labs")'
}
```

### Part B: Native Export Button

#### Step 1: Run the Export Button Discovery Script

```bash
# Activate virtual environment (if not already)
.\venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Run discovery tool
python tools/discover_export_button.py
```

#### Step 2: What the Script Does

**Authentication:**
- Checks for saved cookie profiles and lets you choose one
- Automatically injects cookies for seamless login
- Falls back to browser profile if no cookies available

**Discovery:**
1. Opens Firefox and injects authentication cookies
2. Navigates to Perplexity.ai (already logged in if cookies valid)
3. Automatically checks login status
4. **Waits for you to perform a search** (you need results on screen)
5. Extracts all export/download/share buttons
6. Shows button details in terminal
7. Saves findings to `logs/export_button_discovery.json`
8. Takes screenshot to `screenshots/export_button_discovery.png`

#### Step 3: Manual Inspection

While the browser is open **with search results visible**:

1. Look for the Export/Download button (usually near the answer)
2. Right-click on it → "Inspect Element"
3. Note the exact selector:
   - Look for `id` attribute
   - Look for `class` names
   - Look for `data-testid` or similar
   - Look for `aria-label`
   - Check if it's inside a specific container

#### Step 4: Check the Output

After completing:

1. **Terminal output** - shows all export-related buttons found
2. **`logs/export_button_discovery.json`** - full data dump
3. **`screenshots/export_button_discovery.png`** - visual reference

#### Step 5: Update the Code for Export Button

Open `src/automation/web_driver.py` and find this section (around line 2664):

```python
# Selector for Perplexity's export button - PLACEHOLDER
export_button_selector = None  # TODO: Add actual selector from discovery
```

Replace with the actual selector you found. Examples:

```python
# Example 1: Using data-testid (best if available)
export_button_selector = '[data-testid="export-button"]'

# Example 2: Using aria-label
export_button_selector = 'button[aria-label="Export"]'

# Example 3: Using class and text
export_button_selector = 'button.export-btn:has-text("Export")'

# Example 4: SVG-based button
export_button_selector = 'button:has(svg[class*="download"])'
```

#### Step 6: Test Native Export

```bash
# Test with native export button
perplexity search "test query" --use-native-export --verbose

# Or combine with mode
perplexity search "test query" --mode research --use-native-export
```

## What If Buttons Don't Exist?

If the mode toggle buttons don't exist in the UI:

1. **Check your account type** - Research/Labs might be Pro-only features
2. **Check the URL** - Make sure you're on the main Perplexity homepage
3. **Share the screenshot** - So we can see what the actual UI looks like
4. **Check the JSON output** - See what buttons were actually found

## Example: What Good Selectors Look Like

```json
{
  "text": "Research",
  "tagName": "BUTTON",
  "role": "tab",
  "className": "TabButton_tab__xyz active",
  "dataTestId": "research-mode-tab",
  "ariaSelected": "true"
}
```

From this, good selectors would be:
- `[data-testid="research-mode-tab"]` ← **BEST** (unique, stable)
- `button[role="tab"][aria-label*="Research"]` ← **GOOD** (semantic)
- `.TabButton_tab__xyz:has-text("Research")` ← **OK** (might break on updates)

## Testing After Update

Once selectors are added:

```bash
# Test mode selection
python test_modes.py

# Or test via CLI
perplexity search "test query" --mode research --verbose
```

## Need Help?

If you encounter issues:

1. Share the contents of `logs/mode_discovery.json`
2. Share the screenshot `screenshots/mode_buttons_discovery.png`
3. Describe what you see in the browser vs what you expect

I can then help identify the correct selectors to use.
