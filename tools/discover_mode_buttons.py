"""
ABOUTME: Discovery script to identify Research and Labs mode toggle buttons.
ABOUTME: Logs selectors, attributes, and behavior patterns for mode switching UI.
"""
import json
from pathlib import Path
import sys
import io
import time

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import web driver (uses Camoufox for Cloudflare evasion)
try:
    from src.automation.web_driver import PerplexityWebDriver
except ImportError:
    from automation.web_driver import PerplexityWebDriver


def discover_mode_buttons():
    """
    Discover mode toggle buttons and their selectors
    """
    print("🔍 Starting mode button discovery...")
    print("⚠️  IMPORTANT: This will use your saved cookies or browser profile")
    print("⚠️  Make sure you have cookies extracted or a valid browser profile\n")
    
    findings = {
        "buttons": [],
        "search_area_structure": {},
        "mode_indicators": [],
        "interactions": [],
        "raw_html": {},
        "authentication": {}
    }
    
    # Try to load cookies from saved profiles
    cookies_to_inject = None
    try:
        # Import cookie manager
        try:
            from src.auth.cookie_manager import CookieManager
        except ImportError:
            from auth.cookie_manager import CookieManager
        
        cookie_manager = CookieManager()
        
        # Try to load cookies from default profile or ask user
        print("Looking for saved cookie profiles...")
        profiles = cookie_manager.list_profiles()
        
        if profiles:
            print(f"Found {len(profiles)} profile(s):")
            for i, profile in enumerate(profiles, 1):
                print(f"  {i}. {profile}")
            
            choice = input("\nEnter profile number to use (or press Enter for browser profile): ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(profiles):
                profile_name = profiles[int(choice) - 1]
                cookies_to_inject = cookie_manager.load_cookies(profile_name)
                print(f"✓ Loaded cookies from profile: {profile_name}")
                findings["authentication"]["method"] = "saved_cookies"
                findings["authentication"]["profile"] = profile_name
            else:
                print("Using browser profile authentication")
                findings["authentication"]["method"] = "browser_profile"
        else:
            print("No saved profiles found, using browser profile")
            findings["authentication"]["method"] = "browser_profile"
    except Exception as e:
        print(f"Could not load cookies: {e}")
        print("Will use browser profile authentication")
        findings["authentication"]["method"] = "browser_profile"
    
    # Use web driver (same as main app - includes Camoufox for Cloudflare evasion)
    profile_dir = str(project_root / 'browser_data' / 'discovery')
    
    driver = PerplexityWebDriver(
        headless=False,
        user_data_dir=profile_dir,
        stealth_mode=True
    )
    
    try:
        # Set cookies if available
        if cookies_to_inject:
            print("Setting cookies for authentication...")
            driver.set_cookies(cookies_to_inject)
        
        print("📱 Starting browser (with Camoufox for Cloudflare evasion)...")
        driver.start()
        
        print("📱 Navigating to Perplexity.ai...")
        driver.navigate_to_perplexity()
        time.sleep(3)
        
        # Check if logged in
        print("\nChecking login status...")
        try:
            is_logged_in = driver._verify_logged_in()
            
            if is_logged_in:
                print("✓ Logged in successfully")
                findings["authentication"]["logged_in"] = True
            else:
                print("⚠️  Not logged in - you may need to login manually")
                findings["authentication"]["logged_in"] = False
                print("\n⏸️  Please login in the browser, then press Enter to continue...")
                input()
        except Exception as e:
            print(f"Could not check login status: {e}")
            print("\n⏸️  Please ensure you're logged in, then press Enter to continue...")
            input()
        
        page = driver.page
        
        print("\n🔎 Analyzing search area structure...")
        
        # Get full page HTML for reference
        page_html = page.content()
        findings["raw_html"]["full_page"] = page_html[:5000]  # First 5000 chars
        
        # Find the search input first (as reference point)
        search_input_selectors = [
            '#ask-input',
            'textarea[placeholder*="Ask"]',
            'textarea[placeholder*="anything"]',
            'input[type="text"]',
            'textarea',
            '[data-testid="search-input"]',
            '[contenteditable="true"]'
        ]
        
        search_input = None
        for selector in search_input_selectors:
            try:
                search_input = page.query_selector(selector)
                if search_input and search_input.is_visible():
                    print(f"✓ Found search input: {selector}")
                    findings["search_area_structure"]["input_selector"] = selector
                    break
            except Exception as e:
                continue
        
        if not search_input:
            print("❌ Could not find search input")
            return findings
        
        # Look for buttons near the search input
        print("\n🔘 Searching for mode toggle buttons...")
        
        button_selectors = [
            'button',
            '[role="button"]',
            '[role="tab"]',
            '[role="radio"]',
            'div[class*="toggle"]',
            'div[class*="tab"]',
            'div[class*="mode"]',
            'button[class*="mode"]',
            'button[aria-label*="search"]',
            'button[aria-label*="research"]',
            'button[aria-label*="labs"]',
            'button[aria-label*="Search"]',
            'button[aria-label*="Research"]',
            'button[aria-label*="Labs"]',
            # Based on provided HTML structure
            'div.relative.z-10.flex',
            'div[class*="relative"][class*="z-10"][class*="flex"]'
        ]
        
        for selector in button_selectors:
            try:
                buttons = page.query_selector_all(selector)
                for i, button in enumerate(buttons):
                    try:
                        if not button.is_visible():
                            continue
                            
                        # Get button details
                        text = button.inner_text()
                        aria_label = button.get_attribute('aria-label')
                        classes = button.get_attribute('class')
                        data_attrs = {}
                        
                        # Get all data-* attributes
                        for attr in ['data-mode', 'data-testid', 'data-type', 'data-value']:
                            val = button.get_attribute(attr)
                            if val:
                                data_attrs[attr] = val
                        
                        # Check if this looks like a mode button
                        button_info = {
                            "index": i,
                            "selector": selector,
                            "text": text.strip() if text else "",
                            "aria_label": aria_label,
                            "classes": classes,
                            "data_attributes": data_attrs,
                            "is_visible": button.is_visible(),
                        }
                        
                        # Filter for likely mode buttons
                        keywords = ['search', 'research', 'labs', 'pro', 'mode', 'focus']
                        text_lower = text.lower() if text else ""
                        aria_lower = (aria_label or "").lower()
                        classes_lower = (classes or "").lower()
                        
                        if any(kw in text_lower or kw in aria_lower or kw in classes_lower for kw in keywords):
                            print(f"\n  📍 Found potential mode button:")
                            print(f"     Text: {button_info['text']}")
                            print(f"     Aria: {button_info['aria_label']}")
                            print(f"     Classes: {button_info['classes']}")
                            print(f"     Data: {button_info['data_attributes']}")
                            findings["buttons"].append(button_info)
                    except Exception as e:
                        continue
            except Exception as e:
                continue
        
        # Look for the specific buttons by text content
        print("\n🎯 Looking for specific mode buttons by text...")
        
        for mode_name in ['Search', 'Research', 'Labs', 'Pro', 'Focus']:
            try:
                # Find buttons by text using JavaScript evaluation
                button_elements = page.evaluate(f"""
                    (modeName) => {{
                        const allElements = document.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"], div[class*="flex"][class*="items-center"]');
                        const matches = [];
                        for (const el of allElements) {{
                            const text = (el.textContent || el.innerText || '').trim();
                            if (text.toLowerCase().includes(modeName.toLowerCase()) && 
                                (el.offsetParent !== null || el.style.display !== 'none')) {{
                                matches.push({{
                                    tagName: el.tagName,
                                    text: text,
                                    className: el.className || '',
                                    id: el.id || '',
                                    ariaLabel: el.getAttribute('aria-label') || '',
                                    ariaSelected: el.getAttribute('aria-selected') || '',
                                    ariaPressed: el.getAttribute('aria-pressed') || '',
                                    role: el.getAttribute('role') || '',
                                    parentClass: el.parentElement?.className || '',
                                    html: el.outerHTML.substring(0, 300)
                                }});
                            }}
                        }}
                        return matches;
                    }}
                """, mode_name)
                
                if button_elements:
                    for btn_info in button_elements:
                        print(f"\n  ✓ Found '{mode_name}' button")
                        print(f"     Tag: {btn_info['tagName']}")
                        print(f"     Text: {btn_info['text']}")
                        print(f"     Class: {btn_info['className'][:100]}")
                        print(f"     Aria-label: {btn_info['ariaLabel']}")
                        
                        mode_info = {
                            "mode_name": mode_name,
                            "text_selector": f"text='{mode_name}'",
                            "is_visible": True,
                            "parent_class": btn_info['parentClass'],
                            "button_classes": btn_info['className'],
                            "button_id": btn_info['id'],
                            "aria_label": btn_info['ariaLabel'],
                            "tag_name": btn_info['tagName'],
                            "role": btn_info['role']
                        }
                        findings["mode_indicators"].append(mode_info)
                        
                        # Try to find and click the actual element
                        print(f"     Testing click behavior...")
                        try:
                            # Use JavaScript to find and click the element
                            click_result = page.evaluate(f"""
                                (modeName, btnText) => {{
                                    const allElements = document.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"], div[class*="flex"][class*="items-center"]');
                                    for (const el of allElements) {{
                                        const text = (el.textContent || el.innerText || '').trim();
                                        if (text.toLowerCase().includes(modeName.toLowerCase()) && 
                                            (el.offsetParent !== null || el.style.display !== 'none')) {{
                                            // Get state before click
                                            const beforeState = {{
                                                ariaSelected: el.getAttribute('aria-selected'),
                                                ariaPressed: el.getAttribute('aria-pressed'),
                                                className: el.className || ''
                                            }};
                                            
                                            // Click the element
                                            el.click();
                                            
                                            // Wait a bit for state to update
                                            setTimeout(() => {{
                                                // This won't work in sync context, but we'll check after
                                            }}, 100);
                                            
                                            return {{
                                                clicked: true,
                                                beforeState: beforeState
                                            }};
                                        }}
                                    }}
                                    return {{ clicked: false }};
                                }}
                            """, mode_name, btn_info['text'])
                            
                            if click_result and click_result.get('clicked'):
                                time.sleep(1)  # Wait for state to update
                                
                                # Check state after click by finding element again
                                after_state = page.evaluate(f"""
                                    (modeName) => {{
                                        const allElements = document.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"], div[class*="flex"][class*="items-center"]');
                                        for (const el of allElements) {{
                                            const text = (el.textContent || el.innerText || '').trim();
                                            if (text.toLowerCase().includes(modeName.toLowerCase()) && 
                                                (el.offsetParent !== null || el.style.display !== 'none')) {{
                                                return {{
                                                    ariaSelected: el.getAttribute('aria-selected'),
                                                    ariaPressed: el.getAttribute('aria-pressed'),
                                                    className: el.className || ''
                                                }};
                                            }}
                                        }}
                                        return null;
                                    }}
                                """, mode_name)
                                
                                interaction = {
                                    "mode": mode_name,
                                    "clicked": True,
                                    "aria_selected": after_state.get('ariaSelected') if after_state else None,
                                    "aria_pressed": after_state.get('ariaPressed') if after_state else None,
                                    "classes_after_click": after_state.get('className') if after_state else None,
                                    "classes_before_click": click_result.get('beforeState', {}).get('className')
                                }
                                findings["interactions"].append(interaction)
                                print(f"     State after click: aria-selected={after_state.get('ariaSelected') if after_state else 'N/A'}, aria-pressed={after_state.get('ariaPressed') if after_state else 'N/A'}")
                            else:
                                print(f"     Could not click button (may need manual interaction)")
                        except Exception as e:
                            print(f"     Click failed: {e}")
                        break  # Only test first match
            except Exception as e:
                print(f"     Error searching for {mode_name}: {e}")
                continue
        
        # Look for active/selected state indicators
        print("\n🎨 Checking for active state indicators...")
        
        state_selectors = [
            '[aria-selected="true"]',
            '[aria-pressed="true"]',
            '[data-state="active"]',
            '.active',
            '[class*="active"]',
            '[class*="selected"]'
        ]
        
        for selector in state_selectors:
            try:
                elements = page.query_selector_all(selector)
                for element in elements:
                    if element.is_visible():
                        text = element.inner_text()
                        print(f"  Active element found: {selector} -> '{text[:50]}'")
            except Exception as e:
                continue
        
        # Dump HTML around search area for manual inspection
        print("\n📝 Extracting HTML structure around search input...")
        try:
            search_area_html = page.evaluate("""
                () => {
                    const searchBox = document.querySelector('#ask-input') || 
                                     document.querySelector('[contenteditable="true"]') ||
                                     document.querySelector('textarea');
                    
                    if (!searchBox) return null;
                    
                    // Get parent containers
                    const parent1 = searchBox.parentElement;
                    const parent2 = parent1?.parentElement;
                    const parent3 = parent2?.parentElement;
                    
                    return {
                        searchBox: searchBox.outerHTML,
                        parent1: parent1?.outerHTML.substring(0, 2000),
                        parent2: parent2?.outerHTML.substring(0, 3000),
                        parent3: parent3?.outerHTML.substring(0, 4000)
                    };
                }
            """)
            
            if search_area_html:
                findings["raw_html"]["search_area"] = search_area_html
                print("   ✓ Extracted search area HTML structure")
        except Exception as e:
            print(f"   ✗ Failed to extract HTML: {e}")
        
        # Take screenshot for visual reference
        screenshots_dir = project_root / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / 'mode_buttons_discovery.png'
        page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"\n📸 Screenshot saved: {screenshot_path}")
        
        # Log all clickable elements near search
        print("\n🔍 Logging all buttons/clickable elements near search box...")
        try:
            clickable_elements = page.evaluate("""
                () => {
                    const searchBox = document.querySelector('#ask-input') || 
                                     document.querySelector('[contenteditable="true"]');
                    if (!searchBox) return [];
                    
                    // Get container - look for parent containers with mode buttons
                    // Check multiple levels up
                    let container = searchBox.parentElement;
                    for (let i = 0; i < 5 && container; i++) {
                        if (container.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"]').length > 0) {
                            break;
                        }
                        container = container.parentElement;
                    }
                    
                    if (!container) {
                        // Fallback: get a wider container
                        container = searchBox.closest('div[class*="container"]') || 
                                   searchBox.parentElement?.parentElement?.parentElement;
                    }
                    
                    if (!container) return [];
                    
                    // Find all buttons and clickable elements within container
                    const elements = [];
                    const buttons = container.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"], a, div[class*="flex"][class*="items-center"]');
                    
                    buttons.forEach((el, idx) => {
                        const text = el.textContent?.trim() || '';
                        // Filter out empty or very generic elements
                        if (text.length > 0 || el.tagName === 'BUTTON' || el.getAttribute('role')) {
                            elements.push({
                                index: idx,
                                tagName: el.tagName,
                                text: text,
                                id: el.id || '',
                                className: el.className || '',
                                role: el.getAttribute('role') || '',
                                ariaLabel: el.getAttribute('aria-label') || '',
                                ariaSelected: el.getAttribute('aria-selected') || '',
                                ariaPressed: el.getAttribute('aria-pressed') || '',
                                dataTestId: el.getAttribute('data-testid') || '',
                                dataMode: el.getAttribute('data-mode') || '',
                                html: el.outerHTML.substring(0, 500)
                            });
                        }
                    });
                    
                    return elements;
                }
            """)
            
            findings["clickable_elements"] = clickable_elements
            print(f"   ✓ Found {len(clickable_elements)} clickable elements")
            
            # Print some details
            for elem in clickable_elements[:30]:  # Show first 30
                if elem.get('text') or elem.get('ariaLabel') or elem.get('role'):
                    print(f"\n   Element: '{elem.get('text', '')[:50]}'")
                    print(f"     - Tag: {elem.get('tagName', '')}")
                    print(f"     - Role: {elem.get('role', '')}")
                    print(f"     - Class: {elem.get('className', '')[:100]}")
                    print(f"     - Aria-label: {elem.get('ariaLabel', '')[:50]}")
                    print(f"     - Aria-selected: {elem.get('ariaSelected', '')}")
                    print(f"     - Data-mode: {elem.get('dataMode', '')}")
                    
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser kept open for manual inspection.")
        print("   INSTRUCTIONS:")
        print("   1. Look at the browser - can you see Search/Research/Labs buttons?")
        print("   2. Right-click on them and 'Inspect Element'")
        print("   3. Note their exact selectors (class, id, data-* attributes)")
        print("   4. Press Enter when done to save findings and close...")
        input()
    
    except Exception as e:
        print(f"\n❌ Error during discovery: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up
        try:
            driver.close()
        except Exception as e:
            print(f"⚠️  Error closing browser: {e}")
    
    return findings


def main():
    """Main discovery function"""
    findings = discover_mode_buttons()
    
    # Save findings
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    output_file = logs_dir / 'mode_discovery.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Discovery complete! Findings saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Buttons found: {len(findings['buttons'])}")
    print(f"   - Mode indicators: {len(findings['mode_indicators'])}")
    print(f"   - Interactions tested: {len(findings['interactions'])}")
    print(f"   - Clickable elements: {len(findings.get('clickable_elements', []))}")


if __name__ == "__main__":
    main()
