"""
ABOUTME: Simplified discovery script for export/download button using PerplexityWebDriver.
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


def discover_export_button():
    """
    Discover export/download button using PerplexityWebDriver
    """
    print("🔍 Export Button Discovery")
    print("=" * 60)
    print("Uses same browser setup as main app (Camoufox for Cloudflare)\n")
    
    findings = {
        "export_buttons_found": [],
        "all_action_buttons": [],
        "authentication": {},
        "instructions": "Perform a search, then look for Export/Download button"
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
        
        # Wait for user to perform a search
        print("\n" + "=" * 60)
        print("INSTRUCTIONS:")
        print("1. Perform a search in the browser")
        print("2. Wait for results to appear")
        print("3. You have 60 seconds to do this...")
        print("=" * 60)
        
        for i in range(60, 0, -1):
            print(f"\rTime remaining: {i}s ", end='', flush=True)
            time.sleep(1)
        print("\n")
        
        # Get all buttons that might be export/download
        print("\n🔍 Analyzing buttons in answer area...")
        page = driver.page
        
        try:
            buttons_info = page.evaluate("""
                () => {
                    const buttons = [];
                    const keywords = ['export', 'download', 'share', 'save', 'copy'];
                    
                    // Find all button-like elements
                    const elements = document.querySelectorAll('button, [role="button"], a[download]');
                    
                    elements.forEach((el, idx) => {
                        const text = (el.textContent || '').trim().toLowerCase();
                        const ariaLabel = (el.getAttribute('aria-label') || '').toLowerCase();
                        const title = (el.getAttribute('title') || '').toLowerCase();
                        
                        // Check if matches export/download keywords
                        const matchesKeyword = keywords.some(kw => 
                            text.includes(kw) || ariaLabel.includes(kw) || title.includes(kw)
                        );
                        
                        if (matchesKeyword || el.hasAttribute('download')) {
                            buttons.push({
                                index: idx,
                                text: (el.textContent || '').trim(),
                                tagName: el.tagName,
                                id: el.id || '',
                                className: el.className || '',
                                role: el.getAttribute('role') || '',
                                ariaLabel: el.getAttribute('aria-label') || '',
                                title: el.getAttribute('title') || '',
                                dataTestId: el.getAttribute('data-testid') || '',
                                download: el.getAttribute('download') || '',
                                isVisible: el.offsetParent !== null,
                                hasSvg: el.querySelector('svg') !== null
                            });
                        }
                    });
                    
                    return buttons;
                }
            """)
            
            findings["all_action_buttons"] = buttons_info
            findings["export_buttons_found"] = buttons_info  # All are relevant
            print(f"Found {len(buttons_info)} export-related buttons\n")
            
            # Print details
            for btn in buttons_info:
                print(f"📍 Export-related button:")
                print(f"   Text: '{btn['text']}'")
                print(f"   Tag: {btn['tagName']}")
                print(f"   ID: {btn['id']}")
                print(f"   Class: {btn['className'][:80]}")
                print(f"   Role: {btn['role']}")
                print(f"   Aria-label: {btn['ariaLabel']}")
                print(f"   Title: {btn['title']}")
                print(f"   Data-testid: {btn['dataTestId']}")
                print(f"   Has SVG: {btn['hasSvg']}")
                print()
            
        except Exception as e:
            print(f"Error analyzing buttons: {e}")
        
        # Take screenshot
        screenshots_dir = project_root / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / 'export_button_discovery.png'
        driver.save_screenshot(str(screenshot_path))
        print(f"📸 Screenshot saved: {screenshot_path}")
        
        # Manual inspection
        print("\n" + "=" * 60)
        print("MANUAL INSPECTION:")
        print("1. Look for the Export/Download button in the answer")
        print("2. Right-click → Inspect Element")
        print("3. Note the selector (id, class, data-testid, aria-label)")
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
    findings = discover_export_button()
    
    # Save findings
    logs_dir = project_root / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    output_file = logs_dir / 'export_button_discovery.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Findings saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Export buttons found: {len(findings['export_buttons_found'])}")
    
    if findings['export_buttons_found']:
        print("\n💡 Suggested selectors to try:")
        for btn in findings['export_buttons_found']:
            if btn['dataTestId']:
                print(f"   - '[data-testid=\"{btn['dataTestId']}\"]'")
            elif btn['ariaLabel']:
                print(f"   - 'button[aria-label=\"{btn['ariaLabel']}\"]'")
            elif btn['id']:
                print(f"   - '#{btn['id']}'")
            elif btn['hasSvg']:
                print(f"   - 'button:has(svg)'  // {btn['text'] or 'Icon button'}")


if __name__ == "__main__":
    main()
