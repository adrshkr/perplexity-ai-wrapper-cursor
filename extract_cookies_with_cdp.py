"""
Extract fresh cookies from Perplexity using Playwright CDP (Chrome DevTools Protocol)
and store them in profiles for browser automation.

This script:
1. Opens a browser using Playwright
2. Navigates to Perplexity.ai
3. Waits for user to login (if needed)
4. Extracts cookies using CDP
5. Saves cookies to a profile
6. Tests browser automation with extracted cookies
"""
import json
import time
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("ERROR: Playwright not installed. Run: pip install playwright && playwright install chromium")
    exit(1)

try:
    from src.auth.cookie_manager import CookieManager
    from src.automation.web_driver import PerplexityWebDriver
except ImportError:
    try:
        from auth.cookie_manager import CookieManager
        from automation.web_driver import PerplexityWebDriver
    except ImportError:
        print("ERROR: Could not import required modules. Make sure you're in the project root.")
        exit(1)


def extract_cookies_via_cdp(page: Page, domain: str = "perplexity.ai") -> Dict[str, str]:
    """
    Extract cookies from browser using Chrome DevTools Protocol (CDP)
    
    Args:
        page: Playwright Page object
        domain: Domain to extract cookies for
        
    Returns:
        Dictionary of cookie name -> value
    """
    try:
        # Get CDP session for the page
        cdp_session = page.context.new_cdp_session(page)
        
        # Use CDP Network.getCookies command
        cookies_response = cdp_session.send('Network.getCookies', {
            'urls': [f'https://www.{domain}', f'https://{domain}']
        })
        
        cookie_dict = {}
        if 'cookies' in cookies_response:
            for cookie in cookies_response['cookies']:
                cookie_dict[cookie['name']] = cookie['value']
        
        return cookie_dict
    except Exception as e:
        print(f"Warning: CDP extraction failed: {e}")
        # Fallback: Use Playwright's built-in cookie extraction
        try:
            cookies = page.context.cookies(f'https://www.{domain}')
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            return cookie_dict
        except Exception as e2:
            print(f"Fallback extraction also failed: {e2}")
            return {}


def wait_for_login(page: Page, timeout: int = 300) -> bool:
    """
    Wait for user to login to Perplexity
    
    Args:
        page: Playwright Page object
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if logged in, False otherwise
    """
    print("\n[yellow]Waiting for you to login to Perplexity...[/yellow]")
    print("[cyan]Please login in the browser window. The script will detect when you're logged in.[/cyan]")
    
    start_time = time.time()
    check_interval = 2  # Check every 2 seconds
    
    while (time.time() - start_time) < timeout:
        try:
            # Check if user is logged in by looking for:
            # 1. No login modal
            # 2. Search box is available
            # 3. Session token cookie exists
            
            # Check for login modal
            has_login_modal = page.evaluate("""
                () => {
                    const bodyText = (document.body?.textContent || '').toLowerCase();
                    return bodyText.includes('sign in or create an account') || 
                           bodyText.includes('unlock pro search');
                }
            """)
            
            # Check for search box
            search_box = page.query_selector('#ask-input, [contenteditable="true"], textarea[placeholder*="Ask"]')
            has_search_box = search_box is not None
            
            # Check for session token cookie
            cookies = page.context.cookies('https://www.perplexity.ai')
            has_session_token = any(
                c['name'] in ['__Secure-next-auth.session-token', 'next-auth.session-token']
                for c in cookies
            )
            
            if not has_login_modal and has_search_box and has_session_token:
                print("\n[green]✓ Login detected![/green]")
                return True
            
            # Show progress
            elapsed = int(time.time() - start_time)
            if elapsed % 10 == 0:  # Print every 10 seconds
                print(f"[yellow]Still waiting... ({elapsed}s elapsed)[/yellow]")
            
            time.sleep(check_interval)
            
        except Exception as e:
            print(f"[yellow]Check failed: {e}, continuing...[/yellow]")
            time.sleep(check_interval)
    
    print("\n[yellow]⚠ Timeout waiting for login. Proceeding anyway...[/yellow]")
    return False


def extract_and_save_cookies(profile_name: str = "fresh_cookies", headless: bool = False) -> Dict[str, str]:
    """
    Extract fresh cookies from Perplexity using browser automation
    
    Args:
        profile_name: Name to save cookies as
        headless: Whether to run browser in headless mode
        
    Returns:
        Dictionary of extracted cookies
    """
    print(f"\n[bold cyan]Extracting fresh cookies from Perplexity[/bold cyan]")
    print(f"Profile name: {profile_name}")
    print(f"Headless mode: {headless}\n")
    
    cookie_manager = CookieManager()
    extracted_cookies = {}
    
    with sync_playwright() as p:
        # Launch browser
        print("[cyan]Launching browser...[/cyan]")
        browser = p.chromium.launch(
            headless=headless,
            channel='chrome' if not headless else None
        )
        
        # Create context with realistic settings
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = context.new_page()
        
        try:
            # Navigate to Perplexity
            print("[cyan]Navigating to Perplexity.ai...[/cyan]")
            page.goto('https://www.perplexity.ai', wait_until='domcontentloaded', timeout=30000)
            
            # Wait a bit for page to load
            page.wait_for_timeout(2000)
            
            # Check if we need to wait for login
            print("[cyan]Checking login status...[/cyan]")
            
            # Check for login modal
            has_login_modal = page.evaluate("""
                () => {
                    const bodyText = (document.body?.textContent || '').toLowerCase();
                    return bodyText.includes('sign in or create an account') || 
                           bodyText.includes('unlock pro search');
                }
            """)
            
            # Check for session token
            cookies = page.context.cookies('https://www.perplexity.ai')
            has_session_token = any(
                c['name'] in ['__Secure-next-auth.session-token', 'next-auth.session-token']
                for c in cookies
            )
            
            if has_login_modal or not has_session_token:
                print("[yellow]Not logged in. Waiting for login...[/yellow]")
                if not headless:
                    wait_for_login(page, timeout=300)
                else:
                    print("[red]ERROR: Cannot wait for login in headless mode![/red]")
                    print("[yellow]Please run without --headless to login interactively.[/yellow]")
                    return {}
            
            # Extract cookies using CDP
            print("\n[cyan]Extracting cookies using Chrome DevTools Protocol...[/cyan]")
            extracted_cookies = extract_cookies_via_cdp(page, domain='perplexity.ai')
            
            if not extracted_cookies:
                print("[yellow]⚠ No cookies extracted via CDP, trying fallback method...[/yellow]")
                # Fallback: Use Playwright's cookie API
                cookies = page.context.cookies('https://www.perplexity.ai')
                for cookie in cookies:
                    extracted_cookies[cookie['name']] = cookie['value']
            
            if not extracted_cookies:
                print("[red]✗ Failed to extract cookies![/red]")
                return {}
            
            print(f"[green]✓ Extracted {len(extracted_cookies)} cookies[/green]")
            
            # Show important cookies
            important_cookies = [
                '__Secure-next-auth.session-token',
                'next-auth.session-token',
                'cf_clearance',
                '__cf_bm',
                'pplx.default-search-session',
                'CF_AppSession'
            ]
            
            print("\n[cyan]Important cookies found:[/cyan]")
            for cookie_name in important_cookies:
                if cookie_name in extracted_cookies:
                    value = extracted_cookies[cookie_name]
                    print(f"  ✓ {cookie_name}: {value[:50]}...")
                else:
                    print(f"  ✗ {cookie_name}: Not found")
            
            # Save cookies to profile
            print(f"\n[cyan]Saving cookies to profile: {profile_name}...[/cyan]")
            cookie_manager.save_cookies(extracted_cookies, name=profile_name)
            print(f"[green]✓ Cookies saved successfully![/green]")
            
            # Keep browser open for a moment so user can see
            if not headless:
                print("\n[yellow]Browser will close in 5 seconds...[/yellow]")
                time.sleep(5)
            
        except Exception as e:
            print(f"[red]✗ Error during extraction: {str(e)}[/red]")
            import traceback
            traceback.print_exc()
        finally:
            browser.close()
    
    return extracted_cookies


def test_browser_automation(profile_name: str, test_query: str = "What is artificial intelligence?") -> bool:
    """
    Test browser automation with extracted cookies
    
    Args:
        profile_name: Profile name to load cookies from
        test_query: Test query to run
        
    Returns:
        True if test successful, False otherwise
    """
    print(f"\n[bold cyan]Testing browser automation with profile: {profile_name}[/bold cyan]")
    
    cookie_manager = CookieManager()
    cookies = cookie_manager.load_cookies(name=profile_name)
    
    if not cookies:
        print(f"[red]✗ Profile '{profile_name}' not found![/red]")
        return False
    
    print(f"[green]✓ Loaded {len(cookies)} cookies from profile[/green]")
    
    try:
        # Create web driver with cookies
        driver = PerplexityWebDriver(
            headless=False,  # Show browser for testing
            stealth_mode=True
        )
        
        # Set cookies
        driver.set_cookies(cookies)
        
        # Start browser
        print("[cyan]Starting browser...[/cyan]")
        driver.start()
        
        # Navigate to Perplexity
        print("[cyan]Navigating to Perplexity...[/cyan]")
        driver.navigate_to_perplexity()
        
        # Verify login
        print("[cyan]Verifying login status...[/cyan]")
        is_logged_in = driver._verify_logged_in()
        
        if not is_logged_in:
            print("[yellow]⚠ Login verification failed, but continuing test...[/yellow]")
        
        # Run test query
        print(f"[cyan]Running test query: {test_query}[/cyan]")
        result = driver.search(
            query=test_query,
            wait_for_response=True,
            timeout=60000,
            structured=True
        )
        
        if isinstance(result, dict) and result.get('answer'):
            answer_length = len(result.get('answer', ''))
            print(f"\n[green]✓ Test successful![/green]")
            print(f"[green]✓ Answer length: {answer_length} characters[/green]")
            print(f"[green]✓ Sources found: {len(result.get('sources', []))}[/green]")
            print(f"\n[cyan]Answer preview:[/cyan]")
            print(result.get('answer', '')[:200] + "...")
            
            # Keep browser open for inspection
            print("\n[yellow]Browser will stay open for 30 seconds for inspection...[/yellow]")
            print("[yellow]Press Ctrl+C to close early.[/yellow]")
            try:
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n[yellow]Closing browser...[/yellow]")
            
            driver.close()
            return True
        else:
            print("[red]✗ Test failed: No answer received[/red]")
            driver.close()
            return False
            
    except Exception as e:
        print(f"[red]✗ Test failed: {str(e)}[/red]")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Extract fresh cookies from Perplexity using Playwright CDP'
    )
    parser.add_argument(
        '--profile', '-p',
        type=str,
        default='fresh_cookies',
        help='Profile name to save cookies as (default: fresh_cookies)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (not recommended for login)'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test browser automation after extracting cookies'
    )
    parser.add_argument(
        '--test-query',
        type=str,
        default='What is artificial intelligence?',
        help='Test query to run (default: What is artificial intelligence?)'
    )
    parser.add_argument(
        '--extract-only',
        action='store_true',
        help='Only extract cookies, do not test'
    )
    
    args = parser.parse_args()
    
    # Extract cookies
    cookies = extract_and_save_cookies(
        profile_name=args.profile,
        headless=args.headless
    )
    
    if not cookies:
        print("\n[red]✗ Cookie extraction failed![/red]")
        return 1
    
    print(f"\n[green]✓ Cookie extraction completed successfully![/green]")
    print(f"[cyan]Profile '{args.profile}' is ready to use.[/cyan]")
    print(f"\n[bold]Usage:[/bold]")
    print(f"  perplexity search \"your query\" --profile {args.profile}")
    print(f"  perplexity browser --profile {args.profile}")
    
    # Test if requested
    if args.test and not args.extract_only:
        print("\n" + "="*60)
        success = test_browser_automation(
            profile_name=args.profile,
            test_query=args.test_query
        )
        
        if success:
            print("\n[green]✓ All tests passed![/green]")
            return 0
        else:
            print("\n[yellow]⚠ Tests completed with warnings[/yellow]")
            return 1
    
    return 0


if __name__ == '__main__':
    try:
        from rich.console import Console
        from rich import print as rprint
        console = Console()
        # Use rich print for better formatting
        import builtins
        builtins.print = rprint
    except ImportError:
        pass  # Continue without rich formatting
    
    exit(main())

