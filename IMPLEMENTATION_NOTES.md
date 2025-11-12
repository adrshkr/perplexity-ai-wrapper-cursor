# Implementation Notes: Browser Mode Flag and Fixes

## Changes Made (To Re-implement After Revert)

### 1. Add --browser Flag to Force Browser Automation

**File: `src/interfaces/cli.py`**

Add the `--browser` / `-b` flag to the search command:

```python
@click.option('--browser', '-b', is_flag=True, help='Force browser automation mode (skip API, use browser)')
```

Add `browser` parameter to function signature:
```python
def search(query, simple, research, deep, labs, mode, model, sources, stream, output, format, profile, no_auto, verbose, browser, headless, keep_browser_open, no_cloudflare_bypass, proxy):
```

Add logic to force browser automation when flag is set (place BEFORE the API client setup):
```python
# Force browser automation if --browser flag is used
if browser:
    if verbose:
        console.print("[dim]Browser automation mode explicitly requested[/dim]\n")
    
    _smart_browser_search(
        query=query,
        search_mode_str=search_mode_str,
        mode=mode,
        model=model,
        sources=sources,
        stream=stream,
        output=output,
        format=format,
        profile=profile,
        verbose=verbose,
        headless=headless,
        keep_browser_open=keep_browser_open,
        browser_mode=browser_mode
    )
    return
```

**File: `perplexity.ps1`**

Add parameter:
```powershell
[switch]$Browser,            # Force browser automation mode
```

Add to help text:
```
-Browser             Force browser automation mode (skip API)
```

Add to command args building:
```powershell
if ($Browser) { $cmdArgs += "--browser" }
```

### 2. Fix Duplicate Markdown Import (UnboundLocalError)

**File: `src/interfaces/cli.py`**

Remove duplicate `from rich.markdown import Markdown` imports at:
- Line ~981 (inside function)
- Line ~1869 (inside function)

Keep only the global import at line 32.

### 3. Fix JavaScript Ternary Operator Syntax

**File: `tools/discover_download_buttons.py`**

Change Python-style ternary to JavaScript:
```javascript
// WRONG (Python syntax):
selector: `[download="${downloadAttr}"]` if downloadAttr else `a[href="${href}"]`

// CORRECT (JavaScript syntax):
selector: downloadAttr ? `[download="${downloadAttr}"]` : `a[href="${href}"]`
```

### 4. Fix PowerShell Parameter Conflict

**File: `perplexity.ps1`**

Rename `-Verbose` to `-ShowDetails` (PowerShell has built-in `-Verbose` parameter that conflicts)

Change all occurrences:
```powershell
# Parameter definition
[switch]$ShowDetails,        # Show detailed connection attempts

# Help text
-ShowDetails         Show detailed connection attempts

# Example
.\perplexity.ps1 "Query" -Profile my_account -ShowDetails

# Args building
if ($ShowDetails) { $cmdArgs += "--verbose" }
```

## What NOT to Change

### DO NOT REMOVE Progress Spinners
The Progress spinners are part of the 2c423b0 formatting. Keep them as is.

### DO NOT Change Output Formatting
The current formatting with:
- `[bold white on blue] ANSWER [/bold white on blue]`
- Custom markdown theme
- REFERENCES section
- Metadata footer

...is correct and matches 2c423b0. Do not modify.

## Mode Implementation Already Complete

The Labs and Research mode implementation is ALREADY COMPLETE in commit be17ed3:
- Mode parameter added to `PerplexityWebDriver.search()`
- Mode switching via button clicks
- CLI flags `--research` / `-r` and `--labs` / `-l`
- Browser mode parameter passed through `_smart_browser_search()`

No changes needed to mode implementation itself.

## Summary

Only re-implement:
1. `--browser` flag (new feature)
2. Markdown import fix (bug fix)
3. JavaScript syntax fix (bug fix)  
4. PowerShell `-Verbose` rename (bug fix)

Do NOT touch:
- Progress spinners
- Output formatting
- Mode implementation (already done)
