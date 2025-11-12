"""
Discovery script to find download button selectors on Perplexity pages
"""
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

async def discover_download_buttons(headless: bool = False):
    """
    Discover download button selectors on Perplexity pages
    
    Args:
        headless: Run browser in headless mode
    """
    print("="*70)
    print("DOWNLOAD BUTTON SELECTOR DISCOVERY")
    print("="*70)
    print()
    
    playwright = await async_playwright().start()
    
    browser = await playwright.firefox.launch(
        headless=headless,
        args=['--disable-blink-features=AutomationControlled']
    )
    
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
    )
    
    page = await context.new_page()
    
    print("[1/5] Navigating to Perplexity...")
    await page.goto("https://www.perplexity.ai", wait_until="domcontentloaded")
    await asyncio.sleep(2)
    
    # Perform a search to get to a page with download buttons
    print("[2/5] Performing test search to find download buttons...")
    try:
        search_box = await page.wait_for_selector('#ask-input, [contenteditable="true"]', timeout=5000)
        if search_box:
            await search_box.fill("test query for download discovery")
            await search_box.press("Enter")
            print("  Waiting for answer to generate (this may take 30-60 seconds)...")
            # Wait for answer to complete
            await asyncio.sleep(30)
            
            # Check if answer is complete
            for i in range(10):
                submit_button = await page.query_selector('button[type="submit"]')
                stop_button = await page.query_selector('button:has-text("Stop")')
                if submit_button and not stop_button:
                    print("  ✓ Answer complete")
                    break
                await asyncio.sleep(3)
    except Exception as e:
        print(f"  ⚠ Could not perform search: {e}")
        print("  Will search for download buttons on current page...")
    
    print("[3/5] Discovering download buttons...")
    
    # Discover all download-related elements
    download_data = await page.evaluate("""
        () => {
            const elements = [];
            
            // Check all buttons, links, and clickable elements
            const allElements = Array.from(document.querySelectorAll('button, a, [role="button"], [onclick]'));
            
            allElements.forEach(el => {
                const text = (el.innerText || el.textContent || '').trim();
                const ariaLabel = el.getAttribute('aria-label');
                const testId = el.getAttribute('data-testid');
                const href = el.getAttribute('href');
                const className = el.className || '';
                const id = el.id || '';
                
                // Look for download-related text
                const downloadKeywords = ['download', 'export', 'save', 'get', 'html', 'pdf', 'file', 'copy'];
                const textLower = text.toLowerCase();
                const ariaLower = (ariaLabel || '').toLowerCase();
                const classLower = className.toLowerCase();
                const idLower = id.toLowerCase();
                
                if (downloadKeywords.some(keyword => 
                    textLower.includes(keyword) || 
                    ariaLower.includes(keyword) ||
                    classLower.includes(keyword) ||
                    idLower.includes(keyword)
                )) {
                    // Build selector
                    let selector = '';
                    if (testId) {
                        selector = `[data-testid="${testId}"]`;
                    } else if (id) {
                        selector = `#${id}`;
                    } else if (ariaLabel) {
                        selector = `[aria-label="${ariaLabel}"]`;
                    } else if (el.tagName === 'BUTTON' && text) {
                        selector = `button:has-text("${text.substring(0, 30)}")`;
                    } else if (el.tagName === 'A' && href) {
                        selector = `a[href="${href}"]`;
                    } else if (className) {
                        const firstClass = className.split(' ')[0];
                        selector = `${el.tagName.toLowerCase()}.${firstClass}`;
                    } else {
                        selector = el.tagName.toLowerCase();
                    }
                    
                    const rect = el.getBoundingClientRect();
                    elements.push({
                        tagName: el.tagName,
                        text: text,
                        ariaLabel: ariaLabel,
                        testId: testId,
                        id: id,
                        href: href,
                        classes: className,
                        selector: selector,
                        visible: el.offsetParent !== null,
                        boundingRect: {
                            top: rect.top,
                            left: rect.left,
                            width: rect.width,
                            height: rect.height
                        }
                    });
                }
            });
            
            // Also check for download attributes
            const downloadLinks = Array.from(document.querySelectorAll('[download], a[href*="download"], a[href*="export"]'));
            downloadLinks.forEach(el => {
                const text = (el.innerText || el.textContent || '').trim();
                const href = el.getAttribute('href');
                const downloadAttr = el.getAttribute('download');
                
                elements.push({
                    tagName: el.tagName,
                    text: text,
                    href: href,
                    downloadAttr: downloadAttr,
                    selector: downloadAttr ? `[download="${downloadAttr}"]` : `a[href="${href}"]`,
                    visible: el.offsetParent !== null,
                    boundingRect: el.getBoundingClientRect()
                });
            });
            
            // Remove duplicates
            const unique = [];
            const seen = new Set();
            for (const el of elements) {
                const key = `${el.tagName}-${el.selector}`;
                if (!seen.has(key)) {
                    seen.add(key);
                    unique.push(el);
                }
            }
            
            return unique;
        }
    """)
    
    print(f"[4/5] Found {len(download_data)} download-related elements\n")
    
    # Display findings
    results = {
        'timestamp': datetime.now().isoformat(),
        'url': page.url,
        'downloadButtons': download_data
    }
    
    if download_data:
        for i, btn in enumerate(download_data, 1):
            print(f"Element {i}:")
            print(f"  Tag: {btn['tagName']}")
            print(f"  Text: {btn.get('text', 'N/A')[:50]}")
            print(f"  Aria-Label: {btn.get('ariaLabel', 'N/A')}")
            print(f"  TestID: {btn.get('testId', 'N/A')}")
            print(f"  ID: {btn.get('id', 'N/A')}")
            print(f"  Selector: {btn['selector']}")
            print(f"  Visible: {btn['visible']}")
            print()
    else:
        print("⚠ No download-related elements found")
        print("  This might mean:")
        print("  - Answer hasn't finished generating yet")
        print("  - Download buttons only appear in specific modes (Research/Labs)")
        print("  - Selectors have changed")
    
    # Save results
    output_dir = Path(__file__).parent.parent / 'screenshots' / f'discovery_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / 'download_buttons_discovery.json'
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"[5/5] Results saved to: {output_file}")
    
    # Take screenshot if not headless
    if not headless:
        screenshot_file = output_dir / 'download_buttons.png'
        await page.screenshot(path=str(screenshot_file), full_page=True)
        print(f"Screenshot saved to: {screenshot_file}")
    
    await browser.close()
    await playwright.stop()
    
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    if download_data:
        visible_buttons = [btn for btn in download_data if btn['visible']]
        print(f"✓ Found {len(download_data)} download-related elements ({len(visible_buttons)} visible)")
        print("\nRecommended selectors (visible elements only):")
        for btn in visible_buttons:
            print(f"  • {btn.get('text', 'Unknown')[:40]}")
            print(f"    {btn['selector']}")
    else:
        print("⚠ No download buttons found")
        print("\nSuggestions:")
        print("  1. Try running with --no-headless to see the page")
        print("  2. Wait longer for answer to complete")
        print("  3. Try in Research or Labs mode")
    
    return results


async def main():
    """Entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Discover download button selectors")
    parser.add_argument('--no-headless', action='store_true', help='Run with visible browser')
    
    args = parser.parse_args()
    
    try:
        await discover_download_buttons(headless=not args.no_headless)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

