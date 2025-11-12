"""
ABOUTME: Discovery script to find Perplexity's native export/download button.
ABOUTME: Logs selectors and behavior for the built-in export functionality.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def discover_export_button():
    """
    Discover export/download button and its selectors
    """
    print("🔍 Starting export button discovery...")
    print("⚠️  IMPORTANT: This will use your saved cookies or browser profile")
    print("⚠️  You need to perform a search to see the export button\n")
    
    findings = {
        "export_buttons": [],
        "download_buttons": [],
        "share_buttons": [],
        "action_buttons": [],
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
    
    # Use persistent profile for browser-based auth
    profile_dir = project_root / 'browser_data' / 'discovery'
    profile_dir.mkdir(parents=True, exist_ok=True)
    
    async with async_playwright() as p:
        # Launch browser with persistent context
        context = await p.firefox.launch_persistent_context(
            str(profile_dir),
            headless=False,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0'
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        # Inject cookies if available
        if cookies_to_inject:
            print("Injecting saved cookies...")
            try:
                # Convert cookie format for Playwright
                playwright_cookies = []
                for name, value in cookies_to_inject.items():
                    playwright_cookies.append({
                        'name': name,
                        'value': value,
                        'domain': '.perplexity.ai',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True,
                        'sameSite': 'Lax'
                    })
                await context.add_cookies(playwright_cookies)
                print("✓ Cookies injected")
            except Exception as e:
                print(f"Cookie injection failed: {e}")
        
        print("📱 Navigating to Perplexity.ai...")
        await page.goto('https://www.perplexity.ai/', wait_until='networkidle')
        await asyncio.sleep(3)
        
        # Check if logged in
        print("\nChecking login status...")
        try:
            is_logged_in = await page.evaluate("""
                () => {
                    const searchBox = document.querySelector('#ask-input') || 
                                     document.querySelector('[contenteditable="true"]');
                    const loginButtons = document.querySelectorAll('a[href*="login"], button:has-text("Sign in")');
                    return searchBox && loginButtons.length === 0;
                }
            """)
            
            if is_logged_in:
                print("✓ Logged in successfully")
                findings["authentication"]["logged_in"] = True
            else:
                print("⚠️  Not logged in - you may need to login manually")
                findings["authentication"]["logged_in"] = False
        except Exception as e:
            print(f"Could not check login status: {e}")
        
        # Wait for user to perform a search
        print("\n⏸️  INSTRUCTIONS:")
        print("   1. Perform a search so you have results on screen")
        print("   2. Look for Export/Download/Share button near the answer")
        print("   3. Press Enter when you have results visible...\n")
        input()
        
        print("\n🔎 Analyzing page for export/download buttons...")
        
        # Get full page HTML for reference
        page_html = await page.content()
        findings["raw_html"]["full_page"] = page_html[:5000]
        
        # Look for export/download buttons
        print("\n🔍 Searching for export-related buttons...")
        try:
            export_elements = await page.evaluate("""
                () => {
                    const elements = [];
                    
                    // Find all buttons and clickable elements
                    const allButtons = document.querySelectorAll(
                        'button, [role="button"], a[download], [class*="export"], [class*="download"], [class*="share"]'
                    );
                    
                    allButtons.forEach((el, idx) => {
                        const text = el.textContent?.trim() || '';
                        const ariaLabel = el.getAttribute('aria-label') || '';
                        const title = el.getAttribute('title') || '';
                        const className = el.className || '';
                        
                        // Check if this looks like export/download/share
                        const keywords = ['export', 'download', 'share', 'save', 'copy'];
                        const matchesKeyword = keywords.some(kw => 
                            text.toLowerCase().includes(kw) ||
                            ariaLabel.toLowerCase().includes(kw) ||
                            title.toLowerCase().includes(kw) ||
                            className.toLowerCase().includes(kw)
                        );
                        
                        if (matchesKeyword || el.hasAttribute('download')) {
                            // Get icon info if present
                            const svg = el.querySelector('svg');
                            const svgInfo = svg ? {
                                viewBox: svg.getAttribute('viewBox') || '',
                                className: svg.className?.baseVal || '',
                                innerHTML: svg.innerHTML.substring(0, 200)
                            } : null;
                            
                            elements.push({
                                index: idx,
                                tagName: el.tagName,
                                text: text.substring(0, 100),
                                id: el.id || '',
                                className: className,
                                role: el.getAttribute('role') || '',
                                ariaLabel: ariaLabel,
                                title: title,
                                dataTestId: el.getAttribute('data-testid') || '',
                                dataAction: el.getAttribute('data-action') || '',
                                download: el.getAttribute('download') || '',
                                href: el.getAttribute('href') || '',
                                hasSvg: !!svg,
                                svgInfo: svgInfo,
                                html: el.outerHTML.substring(0, 500)
                            });
                        }
                    });
                    
                    return elements;
                }
            """)
            
            findings["export_buttons"] = export_elements
            print(f"   ✓ Found {len(export_elements)} export-related buttons")
            
            # Print details
            for elem in export_elements:
                print(f"\n   Button:")
                print(f"     Text: '{elem['text']}'")
                print(f"     Tag: {elem['tagName']}")
                print(f"     Class: {elem['className'][:100]}")
                print(f"     Aria-label: {elem['ariaLabel']}")
                print(f"     Title: {elem['title']}")
                print(f"     Data-testid: {elem['dataTestId']}")
                print(f"     Has SVG: {elem['hasSvg']}")
                if elem['download']:
                    print(f"     Download attr: {elem['download']}")
                    
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        
        # Look specifically in answer area
        print("\n📝 Extracting HTML around answer area...")
        try:
            answer_area_html = await page.evaluate("""
                () => {
                    // Find answer container - try multiple selectors
                    const answerSelectors = [
                        '[class*="answer"]',
                        '[class*="response"]',
                        '[class*="result"]',
                        'main',
                        '[role="main"]'
                    ];
                    
                    let answerContainer = null;
                    for (const selector of answerSelectors) {
                        const el = document.querySelector(selector);
                        if (el && el.textContent && el.textContent.length > 100) {
                            answerContainer = el;
                            break;
                        }
                    }
                    
                    if (!answerContainer) return null;
                    
                    // Get action buttons in answer area
                    const actionButtons = [];
                    const buttons = answerContainer.querySelectorAll('button, [role="button"], a');
                    
                    buttons.forEach(btn => {
                        actionButtons.push({
                            text: btn.textContent?.trim() || '',
                            className: btn.className || '',
                            ariaLabel: btn.getAttribute('aria-label') || '',
                            html: btn.outerHTML.substring(0, 300)
                        });
                    });
                    
                    return {
                        containerClass: answerContainer.className,
                        containerHtml: answerContainer.outerHTML.substring(0, 3000),
                        actionButtons: actionButtons
                    };
                }
            """)
            
            if answer_area_html:
                findings["raw_html"]["answer_area"] = answer_area_html
                findings["action_buttons"] = answer_area_html.get('actionButtons', [])
                print(f"   ✓ Found {len(answer_area_html.get('actionButtons', []))} action buttons in answer area")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
        
        # Take screenshot
        screenshots_dir = project_root / 'screenshots'
        screenshots_dir.mkdir(exist_ok=True)
        screenshot_path = screenshots_dir / 'export_button_discovery.png'
        await page.screenshot(path=str(screenshot_path), full_page=False)
        print(f"\n📸 Screenshot saved: {screenshot_path}")
        
        # Keep browser open for manual inspection
        print("\n⏸️  Browser kept open for manual inspection.")
        print("   INSTRUCTIONS:")
        print("   1. Look for the Export/Download button in the answer")
        print("   2. Right-click on it and 'Inspect Element'")
        print("   3. Note its exact selector (class, id, data-* attributes)")
        print("   4. Check if clicking it opens a menu or downloads directly")
        print("   5. Press Enter when done to save findings and close...")
        input()
        
        await context.close()
    
    return findings


async def main():
    """Main discovery function"""
    findings = await discover_export_button()
    
    # Save findings
    logs_dir = Path(__file__).parent.parent / 'logs'
    logs_dir.mkdir(exist_ok=True)
    
    output_file = logs_dir / 'export_button_discovery.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(findings, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Discovery complete! Findings saved to: {output_file}")
    print(f"\n📊 Summary:")
    print(f"   - Export-related buttons found: {len(findings['export_buttons'])}")
    print(f"   - Action buttons in answer area: {len(findings['action_buttons'])}")


if __name__ == "__main__":
    asyncio.run(main())
