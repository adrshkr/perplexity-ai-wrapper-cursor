"""
ABOUTME: Simplified discovery script for mode toggle buttons using PerplexityWebDriver.
ABOUTME: Uses same browser automation as main app (Camoufox) to avoid Cloudflare.
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

# Import web driver
try:
    from src.automation.web_driver import PerplexityWebDriver
    from src.auth.cookie_manager import CookieManager
except ImportError:
    from automation.web_driver import PerplexityWebDriver
    from auth.cookie_manager import CookieManager


def discover_mode_buttons():
    """
    Discover mode toggle buttons using PerplexityWebDriver
    """
    print("🔍 Mode Button Discovery")
    print("=" * 60)
    print("Uses same browser setup as main app (Camoufox for Cloudflare)\n")
    
    findings = {
        "buttons_found": [],
        "all_clickable_elements": [],
        "authentication": {},
        "instructions": "Look for Search/Research/Labs buttons in the browser"
    }
    
    # Load cookies
    cookies_to_inject = None
    try:
        cookie_manager = CookieManager()
        profiles = cookie_manager.list_profiles()
        
        if profiles:
            print(f"Found {len(profiles)} cookie profile(s):")
            for i, profile in enumerate(profiles, 1):
                print(f"  {i}. {profile}")
            
            try:
                choice = input("\nEnter profile number (or press Enter to skip): ").strip()
                if choice.isdigit() and 1 <= int(choice) <= len(profiles):
                    profile_name = profiles[int(choice) - 1]
                    cookies_to_inject = cookie_manager.load_cookies(profile_name)
                    print(f"✓ Loaded cookies from: {profile_name}")
                    findings["authentication"]["profile"] = profile_name
            except (EOFError, KeyboardInterrupt):
                print("\nSkipping cookie selection...")
        else:
            print("No cookie profiles found - using browser profile")
    except Exception as e:
        print(f"Cookie loading skipped: {e}")
    
    # Initialize web driver
    profile_dir = str(project_root / 'browser_data' / 'discovery')
    driver = PerplexityWebDriver(
        headless=False,
        user_data_dir=profile_dir,
        stealth_mode=True
    )
    
    try:
        # Set cookies
        if cookies_to_inject:
            driver.set_cookies(cookies_to_inject)
        
        print("\n📱 Starting browser (Camoufox with Cloudflare evasion)...")
        driver.start()
        
        print("📱 Navigating to Perplexity...")
        # Use direct navigation to avoid strict cookie validation
        # We'll login manually if needed
        driver.page.goto('https://www.perplexity.ai/', wait_until='domcontentloaded')
        time.sleep(3)  # Wait for page to fully load
        
        # Check login
        is_logged_in = driver._verify_logged_in()
        print(f"Login status: {'✓ Logged in' if is_logged_in else '✗ Not logged in'}")
        findings["authentication"]["logged_in"] = is_logged_in
        
        if not is_logged_in:
            print("\n⚠️  Not logged in - you have 60 seconds to login...")
            for i in range(60, 0, -1):
                print(f"\rTime remaining: {i}s ", end='', flush=True)
                time.sleep(1)
            print("\n")
        
        # Get all buttons near search area
        print("\n🔍 Analyzing buttons near search box...")
        page = driver.page
        
        try:
            buttons_info = page.evaluate("""
                () => {
                    const buttons = [];
                    // Find all button-like elements
                    const elements = document.querySelectorAll('button, [role="button"], [role="tab"], [role="radio"]');
                    
                    elements.forEach((el, idx) => {
                        const text = (el.textContent || '').trim();
                        // Focus on buttons with short text (likely mode toggles)
                        if (text && text.length > 0 && text.length < 20) {
                            buttons.push({
                                index: idx,
                                text: text,
                                tagName: el.tagName,
                                id: el.id || '',
                                className: el.className || '',
                                role: el.getAttribute('role') || '',
                                ariaLabel: el.getAttribute('aria-label') || '',
                                ariaSelected: el.getAttribute('aria-selected') || '',
                                dataTestId: el.getAttribute('data-testid') || '',
                                isVisible: el.offsetParent !== null
                            });
                        }
                    });
                    
                    return buttons;
                }
            """)
            
            findings["all_clickable_elements"] = buttons_info
            print(f"Found {len(buttons_info)} button elements\n")
            
            # Filter for likely mode buttons
            mode_keywords = ['search', 'research', 'labs', 'pro', 'focus']
            for btn in buttons_info:
                text_lower = btn['text'].lower()
                if any(kw in text_lower for kw in mode_keywords) and btn['isVisible']:
                    findings["buttons_found"].append(btn)
                    print(f"📍 Potential mode button:")
                    print(f"   Text: '{btn['text']}'")
                    print(f"   Tag: {btn['tagName']}")
                    print(f"   ID: {btn['id']}")
                    print(f"   Class: {btn['className'][:80]}")
                    print(f"   Role: {btn['role']}")
                    print(f"   Aria-selected: {btn['ariaSelected']}")
                    print(f"   Data-testid: {btn['dataTestId']}")
                    print()
            
        except Exception as e:
            print(f"Error analyzing buttons: {e}")
        
        # Take screenshot
        screenshots_dir = project_root / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / 'mode_buttons_discovery.png'
        driver.save_screenshot(str(screenshot_path))
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Manual inspection
        print("\n" + "=" * 60)
        print("MANUAL INSPECTION:")
        print("1. Look at the browser for Search/Research/Labs buttons")
        print("2. Right-click → Inspect Element on each button")
        print("3. Note the selector (id, class, data-testid)")
        print("4. You have 120 seconds to inspect...")
        print("=" * 60)
        
        for i in range(120, 0, -1):
            print(f"\rTime remaining: {i}s ", end='', flush=True)
            time.sleep(1)
        print("\n")
        
    finally:
        print("\nClosing browser...")
        driver.close()
    
    return findings


def main():
    """Main function"""
    findings = discover_mode_buttons()
    
    # Save findings
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    output_file = logs_dir / 'mode_discovery.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Findings saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Likely mode buttons: {len(findings['buttons_found'])}")
    print(f"   - Total buttons analyzed: {len(findings['all_clickable_elements'])}")
    
    if findings['buttons_found']:
        print("\n💡 Suggested selectors to try:")
        for btn in findings['buttons_found']:
            if btn['dataTestId']:
                print(f"   - '[data-testid=\"{btn['dataTestId']}\"]'  // {btn['text']}")
            elif btn['id']:
                print(f"   - '#{btn['id']}'  // {btn['text']}")
            elif btn['role']:
                print(f"   - '[role=\"{btn['role']}\"]:has-text(\"{btn['text']}\")'")


if __name__ == "__main__":
    main()
