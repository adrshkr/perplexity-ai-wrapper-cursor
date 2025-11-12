# Thread Actions & Export Validation Report

**Date:** December 19, 2024  
**Method:** Browser MCP - Connected to existing logged-in Chrome instance  
**URL:** https://www.perplexity.ai/search/...

## Summary

Successfully validated the Thread Actions menu and Export as Markdown functionality on Perplexity.ai using browser MCP tools. The export feature works correctly and downloads markdown files.

## Thread Actions Button

### Location
- **Position:** Top right of the page, near the thread title/header
- **Visibility:** Appears after search results are rendered

### Button Details
- **Aria Label:** "Thread actions"
- **Role:** `button`
- **Aria Expanded:** `true` (when menu is open), `false` (when closed)
- **Aria Has Popup:** `menu`
- **Data State:** `open` (when menu is open), `closed` (when menu is closed)

### Selectors
```javascript
// Primary selector (most reliable)
button[aria-label="Thread actions"]

// Alternative (same as primary)
button[aria-label="Thread actions"]
```

## Menu Container

### Details
- **Role:** `menu`
- **Tag Name:** `DIV`
- **Visibility:** Appears after clicking Thread actions button
- **Animation:** Uses slideUpAndFadeIn/slideUpAndFadeOut animations

### Menu Items Structure
The menu contains the following items (in order):
1. **Add to Space** (menuitem)
2. **Export as PDF** (menuitem)
3. **Export as Markdown** (menuitem) ⭐
4. **Export as DOCX** (menuitem)
5. **Delete** (menuitem)

## Export as Markdown

### Menu Item Details
- **Text:** "Export as Markdown"
- **Aria Label:** "Export as Markdown"
- **Role:** `menuitem`
- **Index:** 2 (third item in menu)
- **Tag:** `DIV` (not a button element)

### Selectors

**Primary (Most Reliable):**
```javascript
[role="menuitem"][aria-label="Export as Markdown"]
```

**Alternative:**
```javascript
// Using text content (Playwright)
page.getByRole('menuitem', { name: 'Export as Markdown' })

// Using has-text (if supported)
[role="menuitem"]:has-text("Export as Markdown")
```

**Fallback:**
```javascript
// Find by text content
const menuItems = page.querySelectorAll('[role="menuitem"]');
const markdownItem = Array.from(menuItems).find(item => 
  item.textContent.trim() === 'Export as Markdown'
);
```

### Behavior
- ✅ **Clickable:** Yes
- ✅ **Tested:** Successfully clicked and triggered download
- ✅ **Download:** Creates a markdown file with thread content
- ✅ **File Naming:** Uses thread title (e.g., "What is artificial intelligence_.md")

## Other Export Options

### Export as PDF
- **Selector:** `[role="menuitem"][aria-label="Export as PDF"]`
- **Index:** 1

### Export as DOCX
- **Selector:** `[role="menuitem"][aria-label="Export as DOCX"]`
- **Index:** 3

## Implementation Workflow

### Step-by-Step Process

```python
def export_as_markdown(self, page: Optional[Page] = None) -> Optional[Path]:
    """Export current thread as Markdown file"""
    target_page = page or self.page
    if not target_page:
        raise Exception("Browser not started")
    
    # Step 1: Wait for results to be rendered
    # (Check for presence of answer content or sources)
    target_page.wait_for_timeout(2000)  # Wait for results
    
    # Step 2: Find and click Thread actions button
    thread_actions_btn = target_page.wait_for_selector(
        'button[aria-label="Thread actions"]',
        timeout=5000,
        state="visible"
    )
    
    if not thread_actions_btn:
        raise Exception("Thread actions button not found")
    
    # Step 3: Click to open menu
    thread_actions_btn.click()
    target_page.wait_for_timeout(500)  # Wait for menu animation
    
    # Step 4: Verify menu is open
    menu = target_page.wait_for_selector(
        '[role="menu"]',
        timeout=2000,
        state="visible"
    )
    
    if not menu:
        raise Exception("Thread actions menu did not open")
    
    # Step 5: Find and click Export as Markdown
    markdown_item = target_page.wait_for_selector(
        '[role="menuitem"][aria-label="Export as Markdown"]',
        timeout=2000,
        state="visible"
    )
    
    if not markdown_item:
        raise Exception("Export as Markdown option not found")
    
    # Step 6: Set up download handling
    # Note: Playwright can intercept downloads
    with target_page.expect_download() as download_info:
        markdown_item.click()
    
    download = download_info.value
    
    # Step 7: Save the file
    download_path = Path("exports") / download.suggested_filename
    download_path.parent.mkdir(exist_ok=True)
    download.save_as(download_path)
    
    logger.info(f"Exported thread as Markdown: {download_path}")
    return download_path
```

### Alternative Implementation (Using Playwright's getByRole)

```python
def export_as_markdown_simple(self, page: Optional[Page] = None) -> Optional[Path]:
    """Export current thread as Markdown file (simplified)"""
    target_page = page or self.page
    if not target_page:
        raise Exception("Browser not started")
    
    # Wait for results
    target_page.wait_for_timeout(2000)
    
    # Open Thread actions menu
    target_page.get_by_role('button', name='Thread actions').click()
    target_page.wait_for_timeout(500)
    
    # Click Export as Markdown
    with target_page.expect_download() as download_info:
        target_page.get_by_role('menuitem', name='Export as Markdown').click()
    
    download = download_info.value
    download_path = Path("exports") / download.suggested_filename
    download_path.parent.mkdir(exist_ok=True)
    download.save_as(download_path)
    
    return download_path
```

## Important Notes

1. **Menu Visibility:** The menu only appears after clicking the Thread actions button. Check `aria-expanded="true"` to confirm it's open.

2. **Menu Items are DIVs:** The menu items use `role="menuitem"` but are `DIV` elements, not `BUTTON` elements.

3. **Download Handling:** 
   - Playwright can intercept downloads using `page.expect_download()`
   - Downloads are saved to the browser's download directory by default
   - You can specify a custom path using `download.save_as(path)`

4. **Timing:** 
   - Wait for search results to fully render before attempting to open menu
   - Add small delays after clicking to allow animations to complete

5. **Error Handling:**
   - Check if Thread actions button exists (results may not be rendered yet)
   - Verify menu opened successfully before trying to click menu items
   - Handle download timeouts appropriately

## Validation Results

✅ **Thread Actions Button:** Found and clickable  
✅ **Menu Opens:** Successfully opens after clicking button  
✅ **Export Menu Items:** All 3 export options found  
✅ **Export as Markdown:** Successfully clicked and downloaded file  
✅ **Download Works:** File downloaded correctly  
✅ **Ready for Implementation:** All selectors validated and working

## Next Steps

1. Implement `export_as_markdown()` method in `web_driver.py`
2. Add download handling with proper file paths
3. Optionally implement `export_as_pdf()` and `export_as_docx()` methods
4. Add error handling for cases where menu doesn't open or items aren't found

