"""
ABOUTME: Browser automation for Perplexity.ai using Playwright
ABOUTME: Coordinates cookie injection, Cloudflare bypass, and search execution
"""
import logging
import sys
import time
import platform
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# Import extracted components
from .tab_manager import TabManager
from .cookie_injector import CookieInjector
from .cloudflare_handler import CloudflareHandler

# Configure logging
logger = logging.getLogger(__name__)

# Suppress noisy third-party loggers
logging.getLogger('playwright').setLevel(logging.WARNING)
logging.getLogger('camoufox').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Try to import camoufox for better Cloudflare evasion
CAMOUFOX_AVAILABLE = False
Camoufox: Optional[Any] = None
try:
    from camoufox.sync_api import Camoufox as _Camoufox
    CAMOUFOX_AVAILABLE = True
    Camoufox = _Camoufox
except ImportError:
    CAMOUFOX_AVAILABLE = False

# Import Playwright types only for type checking
if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright
    from camoufox.sync_api import Camoufox

# Try to import Playwright - only import at runtime, not for type checking
try:
    from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    if TYPE_CHECKING:
        Browser = None  # type: ignore
        BrowserContext = None  # type: ignore
        Page = None  # type: ignore
        Playwright = None  # type: ignore

# Try to import cloudscraper for Cloudflare bypass
CLOUDSCRAPER_AVAILABLE = False
CloudflareBypass: Optional[Any] = None

try:
    import cloudscraper  # noqa: F401
    CLOUDSCRAPER_AVAILABLE = True
except ImportError:
    # Try submodule path
    project_root = Path(__file__).parent.parent.parent
    cloudscraper_path = project_root / 'cloudscraper'
    if cloudscraper_path.exists() and str(cloudscraper_path) not in sys.path:
        sys.path.insert(0, str(cloudscraper_path))
    try:
        import cloudscraper  # noqa: F401
        CLOUDSCRAPER_AVAILABLE = True
    except ImportError:
        CLOUDSCRAPER_AVAILABLE = False

# Try to import CloudflareBypass wrapper
if CLOUDSCRAPER_AVAILABLE:
    try:
        from ..utils.cloudflare_bypass import CloudflareBypass as _CloudflareBypass
        CloudflareBypass = _CloudflareBypass
    except ImportError:
        CloudflareBypass = None


# TabManager is now imported from .tab_manager module
# CookieInjector is now imported from .cookie_injector module
# CloudflareHandler is now imported from .cloudflare_handler module


class PerplexityWebDriver:
    """Browser automation for Perplexity.ai using Playwright"""
    
    def __init__(
        self,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        stealth_mode: bool = True
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed. Install it with: pip install playwright && playwright install firefox")
        
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.stealth_mode = stealth_mode
        
        # Browser components
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.tab_manager: Optional[TabManager] = None
        self._camoufox: Optional[Any] = None
        
        # Extracted components for cleaner architecture
        self.cookie_injector = CookieInjector()
        self.cloudflare_handler = CloudflareHandler()
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Store cookies to be injected before navigation"""
        self.cookie_injector.set_login_cookies(cookies)
    
    # Method _should_inject_cookies moved to CookieInjector class
    # Method _inject_cookies_into_context moved to CookieInjector class
    # Method _pre_authenticate_with_cloudscraper moved to CloudflareHandler class
    
    def start(self, debug_network: bool = False) -> None:
        """Start browser and initialize context - optimized with proper wait strategies"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed")
        
        # Pre-authenticate with cloudscraper to get fresh Cloudflare cookies
        # Skip if using persistent context (cookies persist) OR if we have login cookies (browser will handle Cloudflare)
        # Only use cloudscraper if we have no cookies and no persistent context
        if not self.user_data_dir and not self.cookie_injector.get_current_cookies():
            try:
                cookies = self.cloudflare_handler.solve_challenge()
                self.cookie_injector.set_cloudscraper_cookies(cookies)
            except Exception as e:
                logger.warning(f"Cloudscraper pre-authentication failed: {e}")
                logger.warning("Continuing with browser - it will handle Cloudflare challenge directly")
        
        # Use Camoufox if available (better Cloudflare evasion), otherwise fall back to Firefox
        # According to https://camoufox.com/python/usage/, Camoufox is used as a context manager
        # but we can also use it directly and access the browser
        if CAMOUFOX_AVAILABLE and Camoufox is not None:
            # Detect platform for headless mode selection
            import platform
            is_linux = platform.system() == 'Linux'
            
            mode_str = "headless (virtual display)" if self.headless and is_linux else "headless" if self.headless else "headed"
            logger.debug(f"Using Camoufox for better Cloudflare evasion (mode: {mode_str})")
            # Create Camoufox instance - it manages its own Playwright instance
            # We'll use it as a context manager but keep it alive by storing it
            # Use headless="virtual" for Linux (virtual display - best stealth)
            # Use headless=True for Windows/Mac (regular headless)
            # See: https://camoufox.com/python/virtual-display/
            try:
                # Virtual display only works on Linux
                # On Windows/Mac, use regular headless mode
                headless_mode: Union[str, bool]
                if self.headless:
                    if is_linux:
                        headless_mode = "virtual"  # Virtual display (Linux only)
                        logger.info("Camoufox running in virtual display mode (Linux)")
                    else:
                        headless_mode = True  # Regular headless
                        logger.info("Camoufox running in headless mode (Windows/Mac)")
                else:
                    headless_mode = False  # Normal windowed mode
                    logger.debug("Camoufox running with visible browser window")
                
                self._camoufox = Camoufox(headless=headless_mode)
                logger.debug(f"Camoufox instance created successfully with headless={headless_mode}")
            except Exception as e:
                logger.warning(f"Failed to create Camoufox instance: {e}")
                logger.debug("Falling back to regular Playwright Firefox")
                self._camoufox = None
                
            # Enter the context to get the browser
            if self._camoufox is not None:
                self._camoufox.__enter__()
                self.browser = self._camoufox.browser  # Get the browser instance
                logger.debug("Camoufox browser instance acquired")
                # Camoufox manages its own playwright, we don't need to access it directly
                # The browser object has all we need
                self.playwright = None  # Camoufox manages playwright internally
        else:
            # Fallback to regular Playwright Firefox
            mode_str = "headless" if self.headless else "headed"
            logger.debug(f"Using regular Firefox (Camoufox not available) in {mode_str} mode")
            self.playwright = sync_playwright().start()
            
            # Firefox-specific arguments (minimal, as Firefox is less detectable)
            args: List[str] = []
            if self.stealth_mode:
                # Firefox doesn't need as many stealth flags
                logger.debug("Stealth mode enabled for Firefox")
            
            # Browser launch options for Firefox
            launch_options: Dict[str, Any] = {
                'headless': self.headless,
                'args': args,
            }
            
            if self.headless:
                logger.info("Launching Firefox in headless mode (no browser window)")
            else:
                logger.debug("Launching Firefox with visible window")
            
            if self.user_data_dir:
                launch_options['user_data_dir'] = self.user_data_dir
            
            self.browser = self.playwright.firefox.launch(**launch_options)
        
        # Create context with cloudscraper's user agent to match fingerprint
        context_options: Dict[str, Any] = {
            'viewport': {'width': 1920, 'height': 1080},
            'ignore_https_errors': False,  # Don't ignore HTTPS errors (more secure)
            'java_script_enabled': True,
            'accept_downloads': False,  # Don't auto-accept downloads
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': [],
            'color_scheme': 'light',
        }
        
        # Enhanced stealth mode - add more realistic browser fingerprinting
        if self.stealth_mode:
            # Add extra headers to look more like a real browser
            context_options['extra_http_headers'] = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0',
            }
        
        # Use cloudscraper's user agent if available (matches browser emulation)
        cloudscraper_ua = self.cloudflare_handler.get_user_agent()
        if cloudscraper_ua:
            context_options['user_agent'] = cloudscraper_ua
            logger.debug("Using cloudscraper's user agent in Playwright context")
        else:
            # Fallback to default Firefox user agent (matches Camoufox)
            context_options['user_agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0'
        
        if not self.browser:
            raise Exception("Browser not initialized")
        self.context = self.browser.new_context(**context_options)  # type: ignore
        
        # Inject stealth JavaScript to hide automation indicators
        if self.stealth_mode:
            self.context.add_init_script("""
                // Override navigator.webdriver
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override browser runtime (for compatibility)
                if (!window.chrome) {
                    window.chrome = {
                        runtime: {}
                    };
                }
                
                // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                // Override languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                
                // Override platform
                Object.defineProperty(navigator, 'platform', {
                    get: () => 'Win32'
                });
                
                // Firefox-specific overrides
                if (navigator.userAgent.includes('Firefox')) {
                    // Ensure Firefox-specific properties are present
                    if (!navigator.mimeTypes) {
                        Object.defineProperty(navigator, 'mimeTypes', {
                            get: () => []
                        });
                    }
                }
            """)
            logger.debug("Stealth mode enabled - automation indicators hidden")
        
        # Enable network debugging if requested
        if debug_network:
            def log_request(request: Any) -> None:
                logger.debug(f"→ {request.method} {request.url}")
            def log_response(response: Any) -> None:
                logger.debug(f"← {response.status} {response.url}")
            self.context.on("request", log_request)
            self.context.on("response", log_response)
        
        # Inject cookies into context BEFORE creating pages - only if needed
        self.cookie_injector.inject_cookies_into_context(self.context, self.user_data_dir)
        
        # No need to wait after cookie injection - context.add_cookies is synchronous
        
        # Create main page (always create, regardless of cookie injection)
        self.page = self.context.new_page()
        
        # Initialize tab manager
        self.tab_manager = TabManager(self.context, max_tabs=5)
    
    def navigate_to_perplexity(self, page: Optional[Page] = None) -> None:
        """
        Navigate to Perplexity homepage with optimal wait strategies
        Uses Playwright's built-in wait strategies - no fixed timeouts
        """
        target_page = page or self.page
        if not target_page:
            raise Exception("Browser not started")
        
        # Inject cookies if needed (only if not using persistent context)
        if self.context:
            self.cookie_injector.inject_cookies_into_context(self.context, self.user_data_dir)
        
        # Navigate with fast wait strategy - use domcontentloaded for speed
        # Total wait time should be 2-3 seconds max
        try:
            target_page.goto(
                "https://www.perplexity.ai",
                wait_until="domcontentloaded",  # Faster than 'load'
                timeout=15000  # Increased to 15 seconds to allow Cloudflare challenge
            )
            
            # Wait for Cloudflare challenge to complete if present
            try:
                # Check if Cloudflare challenge is present
                has_challenge = target_page.evaluate("""
                    () => {
                        const bodyText = document.body.textContent || '';
                        return bodyText.includes('just a moment') || 
                               bodyText.includes('checking your browser') ||
                               bodyText.includes('Enable JavaScript and cookies') ||
                               bodyText.includes('Please wait');
                    }
                """)
                
                if has_challenge:
                    logger.warning("Cloudflare challenge detected, waiting for it to complete")
                    # Wait for challenge to disappear (up to 10 seconds)
                    target_page.wait_for_function(
                        "() => !document.body.textContent.includes('just a moment') && !document.body.textContent.includes('checking your browser') && !document.body.textContent.includes('Enable JavaScript and cookies')",
                        timeout=10000
                    )
                    logger.debug("Cloudflare challenge completed")
                    # Wait a bit more for page to fully load after challenge
                    target_page.wait_for_timeout(1000)
            except Exception:
                # Challenge might have already completed or wasn't present
                pass
        except Exception as e:
            # If domcontentloaded times out, check if we're at least on the page
            current_url = target_page.url
            if 'perplexity.ai' not in current_url.lower():
                raise Exception(f"Failed to navigate to Perplexity. Current URL: {current_url}. Error: {str(e)}")
        
        # Check for Cloudflare challenge and wait for it to complete
        # Playwright should handle this automatically, but we need to wait
        cloudflare_detected = target_page.evaluate("""
            () => {
                const bodyText = (document.body?.textContent || '').toLowerCase();
                return bodyText.includes('just a moment') || 
                       bodyText.includes('checking your browser') ||
                       bodyText.includes('please wait');
            }
        """)
        
        if cloudflare_detected:
            # Wait for Cloudflare challenge to complete (max 10 seconds)
            logger.warning("Cloudflare challenge detected, waiting for completion")
            try:
                # Wait for the challenge page to disappear
                target_page.wait_for_function(
                    "() => !document.body?.textContent?.toLowerCase().includes('just a moment') && !document.body?.textContent?.toLowerCase().includes('checking your browser')",
                    timeout=10000
                )
                logger.debug("Cloudflare challenge completed")
            except Exception:
                # If timeout, continue anyway - might have passed
                logger.warning("Cloudflare challenge wait timed out, continuing")
        
        # Small wait for page to settle (reduced from networkidle)
        target_page.wait_for_timeout(500)  # 0.5 second wait
        
        # Verify we're on Perplexity (not redirected)
        current_url = target_page.url
        if 'perplexity.ai' not in current_url.lower():
            raise Exception(f"Not on Perplexity domain. Current URL: {current_url}")
        
        # Refresh/validate session by checking auth status and refreshing if needed
        # This helps refresh expired cookies and ensures session is active
        try:
            logger.debug("Checking session status")
            target_page.wait_for_timeout(1000)  # Wait for page to fully load
            
            # Check auth session status via API
            try:
                response = target_page.request.get('https://www.perplexity.ai/api/auth/session', timeout=5000)
                if response.status == 200:
                    session_data = response.json()
                    if session_data and session_data.get('user'):
                        logger.debug("Session is valid and user is authenticated")
                    else:
                        # Session API returned empty - cookies are expired or invalid
                        logger.warning("Session API returned no user - cookies may be expired, attempting refresh")
                        
                        # Make a request that requires auth - this might refresh cookies
                        # Try accessing a protected endpoint or making a search request
                        try:
                            # Make a request to refresh the session
                            target_page.request.get('https://www.perplexity.ai/api/auth/csrf', timeout=5000)
                            # Reload to pick up any new cookies
                            target_page.reload(wait_until="domcontentloaded", timeout=5000)
                            target_page.wait_for_timeout(1000)
                            
                            # Re-inject cookies after refresh
                            if self.context:
                                logger.debug("Re-injecting cookies after refresh attempt")
                                self.cookie_injector.inject_cookies_into_context(self.context, self.user_data_dir)
                        except Exception as e:
                            logger.warning(f"Could not refresh session: {e}")
                else:
                    logger.warning(f"Session check returned status {response.status}")
            except Exception as e:
                logger.warning(f"Could not check session: {e}")
        except Exception as e:
            logger.warning(f"Session refresh failed: {e}")
            # Continue anyway - might still work
        
        # Wait for search input to be visible - reduced timeout for speed
        # Based on actual page structure: textbox with "Ask anything" text
        search_selectors = [
            '#ask-input',  # Exact ID - fastest
            'textbox',  # Primary selector - Playwright identifies it as textbox
            '[contenteditable="true"]',
        ]
        
        search_box_found = False
        for selector in search_selectors:
            try:
                # Reduced timeout to 2 seconds per selector (max 2-3 seconds total)
                target_page.wait_for_selector(selector, timeout=2000, state="visible")
                search_box_found = True
                break
            except Exception:
                continue
        
        if not search_box_found:
            # Get diagnostic info
            page_url = target_page.url
            page_title = target_page.title()
            
            # Check if we're on a login/redirect page
            if 'login' in page_url.lower() or 'sign' in page_url.lower():
                raise Exception(
                    f"Redirected to login page. URL: {page_url}, Title: {page_title}. "
                    "If using persistent context, make sure you're logged in. "
                    "If using cookies, make sure they're valid."
                )
            
            raise Exception(
                f"Search box not found. URL: {page_url}, Title: {page_title}. "
                "Page may not have loaded correctly or you may need to login."
            )
        
        # Verify cookies are present in browser after navigation
        browser_cookies = target_page.context.cookies()
        browser_cf_cookies = [c.get('name') for c in browser_cookies if 'cf' in c.get('name', '').lower() or c.get('name', '').startswith('__cf')]
        if browser_cf_cookies:
            logger.debug(f"Cloudflare cookies present in browser: {browser_cf_cookies}")
        else:
            logger.warning("No Cloudflare cookies found in browser after navigation")
        
        # Check specifically for cf_clearance
        cf_clearance_in_browser = any(c.get('name') == 'cf_clearance' for c in browser_cookies)
        if cf_clearance_in_browser:
            logger.debug("cf_clearance cookie verified in browser")
        else:
            logger.warning("cf_clearance cookie not found in browser - may be blocked by Cloudflare")
        
        # Check for login modal - this is the real blocker, not Cloudflare
        login_modal_detected = target_page.evaluate("""
            () => {
                // Check for login modal text
                const bodyText = (document.body?.textContent || '').toLowerCase();
                const hasLoginText = bodyText.includes('sign in or create an account') || 
                                    bodyText.includes('unlock pro search');
                
                // Check for login modal element
                const loginModal = Array.from(document.querySelectorAll('*')).find(el => {
                    const text = (el.textContent || '').toLowerCase();
                    return (text.includes('sign in or create an account') || 
                           text.includes('continue with google') ||
                           text.includes('continue with apple')) &&
                           el.offsetParent !== null; // Element is visible
                });
                
                return {
                    hasLoginModal: loginModal !== undefined,
                    hasLoginText: hasLoginText,
                    modalVisible: loginModal !== undefined
                };
            }
        """)
        
        if login_modal_detected.get('modalVisible') or login_modal_detected.get('hasLoginText'):
            # Check if we have auth cookies
            browser_cookies = target_page.context.cookies()
            has_auth_token = any(
                c.get('name') == '__Secure-next-auth.session-token' or 
                c.get('name') == 'next-auth.session-token'
                for c in browser_cookies
            )
            
            if not has_auth_token:
                # Check session API to confirm cookies are expired
                try:
                    session_response = target_page.request.get('https://www.perplexity.ai/api/auth/session', timeout=3000)
                    if session_response.status == 200:
                        session_data = session_response.json()
                        if not session_data or not session_data.get('user'):
                            raise Exception(
                                "Cookies are expired or invalid. Session API returned no user. "
                                "Please extract fresh cookies from your browser while logged into Perplexity. "
                                "Use: perplexity cookies extract --profile <name>"
                            )
                except Exception as api_error:
                    if "expired" in str(api_error).lower() or "invalid" in str(api_error).lower():
                        raise
                
                raise Exception(
                    "Login modal detected and no authentication token cookie found. "
                    "Please ensure you have valid login cookies with '__Secure-next-auth.session-token'. "
                    "Extract fresh cookies from your browser while logged in: "
                    "perplexity cookies extract --profile <name>"
                )
            else:
                logger.debug("Login modal detected but auth token present - modal may be transient")
        else:
            logger.debug("No login modal detected - user appears to be logged in")
    
    def _verify_logged_in(self, page: Optional[Page] = None) -> bool:
        """
        Verify if user is logged in by checking for login modal/prompt
        Returns True if logged in, False otherwise
        """
        target_page = page or self.page
        if not target_page:
            return False
        
        try:
            login_status = target_page.evaluate("""
                () => {
                    // Check for login modal/prompt
                    const loginModal = document.querySelector('[class*="modal"], [class*="dialog"], [class*="popup"]');
                    const loginText = Array.from(document.querySelectorAll('*')).find(el => {
                        const text = (el.textContent || '').toLowerCase();
                        return text.includes('sign in or create an account') || 
                               text.includes('unlock pro search') ||
                               (text.includes('sign in') && el.closest('button, a'));
                    });
                    
                    // Check for user profile/account indicator (logged in)
                    const userProfile = document.querySelector('[class*="avatar"], [class*="profile"], [class*="user"]');
                    const accountButton = Array.from(document.querySelectorAll('button, a')).find(el => {
                        const text = (el.textContent || '').toLowerCase();
                        return text === 'account' || text.includes('profile') || text.includes('settings');
                    });
                    
                    // Check for prominent login buttons in header
                    const prominentLogin = Array.from(document.querySelectorAll('a, button')).filter(el => {
                        const text = (el.textContent || '').toLowerCase();
                        const href = (el.getAttribute('href') || '').toLowerCase();
                        const parent = el.closest('header, nav, [class*="header"], [class*="nav"]');
                        if (!parent) return false;
                        return (text.includes('sign in') || text.includes('log in') || 
                               href.includes('login') || href.includes('sign'));
                    });
                    
                    // Logged in if:
                    // 1. No login modal visible
                    // 2. No prominent login buttons
                    // 3. (Optional) User profile/account indicator present
                    const hasLoginModal = loginModal && loginModal.offsetParent !== null;
                    const hasLoginPrompt = loginText !== undefined;
                    const hasProminentLogin = prominentLogin.length > 0;
                    const hasUserProfile = userProfile !== null || accountButton !== undefined;
                    
                    return {
                        logged_in: !hasLoginModal && !hasLoginPrompt && !hasProminentLogin,
                        hasLoginModal: hasLoginModal,
                        hasLoginPrompt: hasLoginPrompt,
                        hasProminentLogin: hasProminentLogin.length > 0,
                        hasUserProfile: hasUserProfile,
                        details: {
                            loginModalFound: hasLoginModal,
                            loginTextFound: hasLoginPrompt,
                            prominentLoginCount: prominentLogin.length,
                            userProfileFound: hasUserProfile
                        }
                    };
                }
            """)
            
            return login_status.get('logged_in', False)
        except Exception:
            # If check fails, assume not logged in to be safe
            return False
    
    def search(
        self,
        query: str,
        wait_for_response: bool = True,
        timeout: int = 60000,
        extract_images: bool = False,
        image_dir: Optional[str] = None,
        structured: bool = False,
        page: Optional[Page] = None
    ) -> Union[str, Dict[str, Any]]:
        """Execute search query"""
        target_page = page or self.page
        if not target_page:
            raise Exception("Browser not started")
        
        # Find search box - using exact selectors based on actual page structure
        search_box = None
        search_selectors = [
            '#ask-input',  # Exact ID from page
            '[contenteditable="true"]',  # Fallback for contenteditable div
            'textarea[placeholder*="Ask"]',  # Fallback for textarea
            'textarea'  # Last resort
        ]
        
        for selector in search_selectors:
            try:
                search_box = target_page.wait_for_selector(selector, timeout=3000, state="visible")
                if search_box:
                    break
            except Exception:
                continue
        
        if not search_box:
            raise Exception("Could not find search input. Make sure you're logged in.")
        
        # Clear any existing text and enter query
        # Use Playwright's fill() method which works well with contenteditable divs
        try:
            search_box.click()  # Focus the element
            target_page.wait_for_timeout(200)  # Increased wait for focus (more human-like)
            
            # Use fill() method - works with contenteditable divs
            # But add a small delay to simulate human typing
            search_box.fill(query)
            
            # Wait longer to ensure input is processed and looks more human
            target_page.wait_for_timeout(500)  # Increased from 100ms to 500ms
            
        except Exception as e:
            # Fallback: try type() method if fill() fails
            try:
                target_page.keyboard.press('Control+A')  # Select all
                target_page.wait_for_timeout(50)
                search_box.type(query, delay=10)
                target_page.wait_for_timeout(100)
            except Exception:
                # Last resort: JavaScript method
                try:
                    target_page.evaluate("""
                        (query) => {
                            const el = document.querySelector('#ask-input') || 
                                      document.querySelector('[contenteditable="true"]');
                        if (el) {
                            el.focus();
                                const p = el.querySelector('p');
                                if (p) {
                                    p.textContent = query;
                                } else {
                            el.textContent = query;
                                }
                            el.dispatchEvent(new Event('input', { bubbles: true }));
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    """, query)
                    target_page.wait_for_timeout(100)
                except Exception:
                    raise Exception(f"Failed to enter query into search box: {str(e)}")
        
        # Submit - try clicking submit button first, fallback to Enter
        # Add a small delay before submitting to look more human
        target_page.wait_for_timeout(300)  # Wait before submitting
        
        try:
            # Look for submit button
            submit_button = target_page.query_selector('button[data-testid="submit-button"], button:has-text("Submit")')
            if submit_button and submit_button.is_visible():
                submit_button.click()
            else:
                # Fallback: press Enter
                search_box.press('Enter')
        except Exception:
            # Fallback: press Enter
            search_box.press('Enter')
        
        # Wait a moment after submitting before checking for response
        target_page.wait_for_timeout(1000)  # Wait 1 second after submit
        
        # Capture the state BEFORE the new search to identify which answer is new
        # This helps when multiple queries are on the same page
        answer_containers_before = []
        try:
            answer_containers_before = target_page.evaluate("""
                () => {
                    const main = document.querySelector('main');
                    if (!main) return [];
                    
                    // Find all answer containers (sections that look like answers)
                    const containers = main.querySelectorAll('div, section, article');
                    const answerSections = [];
                    
                    for (const container of containers) {
                        const text = (container.innerText || container.textContent || '').trim();
                        // Skip UI elements and very short containers
                        if (text.length > 200 && 
                            !text.toLowerCase().includes('source') && 
                            !text.toLowerCase().includes('related question') &&
                            !text.toLowerCase().includes('ask a follow-up')) {
                            // Get a unique identifier for this container
                            const rect = container.getBoundingClientRect();
                            answerSections.push({
                                top: rect.top,
                                textLength: text.length,
                                firstWords: text.substring(0, 50)
                            });
                        }
                    }
                    
                    return answerSections;
                }
            """)
        except Exception:
            pass
        
        if wait_for_response:
            # Wait for response using optimized strategy
            # First, wait for URL to change to search page (indicates search started)
            # Add initial delay to let the request start
            target_page.wait_for_timeout(500)  # Wait 500ms before checking URL
            
            try:
                # Wait for URL to change to /search/ pattern
                target_page.wait_for_function(
                    "() => window.location.pathname.startsWith('/search/')",
                    timeout=10000
                )
                logger.debug("Search initiated - URL changed to search page")
                # Wait for main element to be present before starting content checks
                target_page.wait_for_selector('main', timeout=5000)
                target_page.wait_for_timeout(800)  # Brief wait for content to start loading
            except Exception:
                # Fallback: wait for any URL change or content
                try:
                    target_page.wait_for_function(
                        "() => window.location.pathname !== '/' || document.querySelector('main')?.textContent?.length > 100",
                        timeout=5000
                    )
                except Exception:
                    pass  # Continue even if URL doesn't change
            
            # Wait for response using adaptive polling with Playwright's wait_for_function
            max_wait_time = min(timeout / 1000, 40)  # Cap at 40 seconds max - allow time for comprehensive answers
            start_time = time.time()
            response_text = ""
            check_interval = 0.3  # Start with fast polling (300ms)
            stable_count = 0
            previous_length = 0
            no_progress_count = 0
            max_no_progress = 100  # Allow up to 30 seconds (100 checks * 0.3s avg) for answer generation
            
            # Track answer completion using button state
            answer_complete = False  # Track if answer is complete
            
            while (time.time() - start_time) < max_wait_time:
                try:
                    current_url = target_page.url
                    if 'perplexity.ai' not in current_url.lower():
                        raise Exception(f"Redirected away from Perplexity: {current_url}")
                    
                    # Check for Cloudflare challenge during search
                    try:
                        has_cloudflare = target_page.evaluate("""
                            () => {
                                const bodyText = document.body.textContent || '';
                                return bodyText.includes('just a moment') || 
                                       bodyText.includes('checking your browser') ||
                                       bodyText.includes('Please wait');
                            }
                        """)
                        if has_cloudflare:
                            logger.debug("Cloudflare challenge detected during search, waiting...")
                            target_page.wait_for_timeout(2000)
                            continue
                    except Exception:
                        pass
                    
                    # OPTIMIZED: Check button state AND content in ONE evaluate() call
                    try:
                        page_state = target_page.evaluate("""
                            () => {
                                // Check buttons (most reliable completion indicator)
                                const stopButton = document.querySelector('button[data-testid="stop-generating-response-button"]');
                                const submitButton = document.querySelector('button[data-testid="submit-button"]');
                                
                                // Check for content in parallel
                                const main = document.querySelector('main');
                                let hasContent = false;
                                if (main) {
                                    const paragraphs = main.querySelectorAll('p');
                                    for (const p of paragraphs) {
                                        const text = (p.innerText || p.textContent || '').trim();
                                        if (text.length > 100 && !text.includes('Sign in or create')) {
                                            hasContent = true;
                                            break;
                                        }
                                    }
                                }
                                
                                return {
                                    isGenerating: stopButton !== null,
                                    isComplete: submitButton !== null && stopButton === null,
                                    hasContent: hasContent
                                };
                            }
                        """)
                        
                        is_generating = page_state.get('isGenerating', False)
                        is_complete = page_state.get('isComplete', False)
                        has_content = page_state.get('hasContent', False)
                        
                        if is_complete:
                            logger.info("✓ Answer complete detected - submit button visible, stop button gone")
                            answer_complete = True
                            # Wait briefly to ensure DOM is fully updated
                            target_page.wait_for_timeout(300)  # Reduced from 500ms
                            logger.debug("Waited 300ms for DOM to settle after completion")
                            # Answer is complete - break out of loop immediately
                            break
                        elif is_generating:
                            logger.debug("⏳ Answer still generating - stop button visible")
                            answer_complete = False
                            if has_content:
                                logger.debug("Found content while generating")
                        else:
                            # No buttons yet, might be initial loading
                            answer_complete = False
                            
                    except Exception as e:
                        logger.debug(f"Page state check error: {str(e)[:100]}")
                        # Fallback: assume no content
                        has_content = False
                        answer_complete = False
                    
                    if has_content:
                        # Extract text - but only for the NEW answer (not previous ones)
                        original_page = self.page
                        self.page = target_page
                        # Pass the query and previous answer info to extract only the new answer
                        current_text = self.get_response_text(
                            extract_images=extract_images, 
                            image_dir=image_dir,
                            query=query,
                            previous_answers=answer_containers_before
                        )
                        self.page = original_page
                        
                        current_length = len(current_text) if current_text else 0
                        
                        if current_text:
                            # Check if we got actual answer content, not just query text
                            query_lower = query.lower()
                            text_lower = current_text.lower()
                            is_just_query = (text_lower.startswith(query_lower[:50]) and 
                                           current_length < len(query) + 200)
                            
                            if is_just_query:
                                # This is just the query, not the answer - wait for actual answer
                                no_progress_count += 1
                                check_interval = 0.5  # Slower when waiting for first content
                            elif current_length > previous_length:
                                # OPTIMIZATION: Answer is growing - poll aggressively
                                response_text = current_text
                                previous_length = current_length
                                stable_count = 0
                                no_progress_count = 0
                                check_interval = 0.15  # Fast polling when actively generating (150ms)
                            elif current_text == response_text:
                                stable_count += 1
                                no_progress_count = 0
                                check_interval = 0.8  # Slower when content is stable
                                # If answer is complete (button state), break immediately
                                if answer_complete:
                                    logger.info("Answer complete and stable - breaking immediately")
                                    break
                                # DON'T break on stability alone - wait for button state to confirm completion
                                # The old logic here was breaking too early
                                if stable_count >= 10:  # Only break after 5 seconds of no change (10 * 0.5s)
                                    logger.warning(f"Content stable for {stable_count} checks but answer_complete={answer_complete}")
                                    # Still don't break - let button state be authoritative
                            else:
                                response_text = current_text
                                previous_length = current_length
                                stable_count = 0
                                no_progress_count = 0
                        else:
                            no_progress_count += 1
                            # Don't break on no progress - could be slow generation or network delay
                            # Let the button state be authoritative
                            if no_progress_count >= max_no_progress:
                                logger.debug(f"No progress for {no_progress_count} checks, but continuing to wait for button state")
                    else:
                        no_progress_count += 1
                        # Don't break here either - wait for button state confirmation
                        if no_progress_count >= max_no_progress and response_text:
                            logger.debug(f"Content appears stable after {no_progress_count} checks, but waiting for button state confirmation")
                        
                except Exception as e:
                    if "Redirected away" in str(e):
                        raise
                    # Log other exceptions but continue
                    if "Target page" not in str(e) and "closed" not in str(e).lower():
                        logger.debug(f"Warning during search wait: {str(e)[:100]}")
                    pass
                
                # Adaptive sleep based on state
                target_page.wait_for_timeout(int(check_interval * 1000))
            
            # Final check: Verify answer is complete using button state
            if response_text:
                logger.info(f"Answer detected with {len(response_text)} characters, verifying completion...")
                try:
                    # One final button check to ensure answer is complete
                    button_state = target_page.evaluate("""
                        () => {
                            const stopButton = document.querySelector('button[data-testid="stop-generating-response-button"]');
                            const submitButton = document.querySelector('button[data-testid="submit-button"]');
                            return {
                                isGenerating: stopButton !== null,
                                isComplete: submitButton !== null && stopButton === null,
                                hasStopButton: stopButton !== null,
                                hasSubmitButton: submitButton !== null
                            };
                        }
                    """)
                    
                    logger.debug(f"Button state: {button_state}")
                    is_complete = button_state.get('isComplete', False)
                    is_generating = button_state.get('isGenerating', False)
                    
                    if is_generating and not is_complete:
                        # Answer is STILL generating - we exited loop too early (timeout?)
                        logger.warning("⚠ Answer still generating! Waiting for completion...")
                        logger.info(f"Current answer length: {len(response_text)}, waiting up to 30 more seconds...")
                        
                        # Wait for generation to complete (up to 30 seconds)
                        additional_wait = 30
                        for i in range(additional_wait * 2):  # Check every 0.5 seconds
                            target_page.wait_for_timeout(500)
                            button_state = target_page.evaluate("""
                                () => {
                                    const stopButton = document.querySelector('button[data-testid="stop-generating-response-button"]');
                                    const submitButton = document.querySelector('button[data-testid="submit-button"]');
                                    return {
                                        isGenerating: stopButton !== null,
                                        isComplete: submitButton !== null && stopButton === null
                                    };
                                }
                            """)
                            if button_state.get('isComplete', False):
                                logger.info(f"✓ Answer completed after {(i+1)*0.5} additional seconds")
                                is_complete = True
                                break
                        
                        if not is_complete:
                            logger.error("Answer still generating after 30 additional seconds - returning partial answer")
                    
                    if is_complete:
                        logger.info("✓ Final check confirms answer is complete")
                        # Wait a bit more to ensure everything is rendered
                        target_page.wait_for_timeout(1000)
                        logger.debug("Waited 1s for final rendering")
                        # Extract final version
                        original_page = self.page
                        self.page = target_page
                        final_text = self.get_response_text(
                            extract_images=extract_images, 
                            image_dir=image_dir,
                            query=query,
                            previous_answers=answer_containers_before
                        )
                        self.page = original_page
                        if final_text and len(final_text) > len(response_text):
                            logger.info(f"Final extraction improved: {len(response_text)} -> {len(final_text)} characters")
                            response_text = final_text
                        else:
                            logger.debug(f"Final extraction didn't improve length: {len(final_text)} vs {len(response_text)}")
                        logger.info(f"✓ Final answer length: {len(response_text)} characters")
                    else:
                        logger.error(f"❌ Answer incomplete - returning partial result: {button_state}")
                except Exception as e:
                    logger.error(f"Final check error: {str(e)[:100]}")
            
            # Final check: if we have a search URL but no content, wait a bit more
            if not response_text:
                current_url = target_page.url
                if '/search/' in current_url:
                    logger.debug("On search page but no content detected, waiting 5 more seconds...")
                    target_page.wait_for_timeout(5000)
                    # Try one more extraction
                    try:
                        original_page = self.page
                        self.page = target_page
                        current_text = self.get_response_text(
                            extract_images=extract_images, 
                            image_dir=image_dir,
                            query=query,
                            previous_answers=answer_containers_before
                        )
                        self.page = original_page
                        if current_text and len(current_text) > 50:
                            response_text = current_text
                    except Exception:
                        pass
            
            # Extract final response
            if response_text:
                logger.info(f"search: Extracting final response (structured={structured}), response_text length: {len(response_text)}")
                original_page = self.page
                self.page = target_page
                
                if structured:
                    logger.debug("search: Calling get_structured_response...")
                    result: Dict[str, Any] = self.get_structured_response(
                        query, 
                        extract_images=extract_images, 
                        image_dir=image_dir,
                        previous_answers=answer_containers_before
                    )
                    logger.info(f"search: Got structured result with answer length: {len(result.get('answer', ''))}")
                else:
                    result = response_text  # type: ignore
                    logger.info(f"search: Returning plain text result, length: {len(result)}")
                
                self.page = original_page
                logger.info("search: Returning result to caller")
                return result
            else:
                logger.warning("search: No response_text extracted, returning empty result")
            
            empty_result = "" if not structured else {
                'query': query,
                'answer': '',
                'sources': [],
                'related_questions': [],
                'mode': 'auto',
                'model': None
            }
            logger.warning(f"search: Returning empty result (structured={structured})")
            return empty_result
        
        logger.warning("search: wait_for_response=False, returning empty result")
        return "" if not structured else {
            'query': query,
            'answer': '',
            'sources': [],
            'related_questions': [],
            'mode': 'auto',
            'model': None
        }
    
    def get_response_text(
        self, 
        extract_images: bool = False, 
        image_dir: Optional[str] = None,
        query: Optional[str] = None,
        previous_answers: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Extract response text matching the direct API method logic.
        The API looks for answer content in specific structures:
        - Main answer paragraphs (not sources, not related questions)
        - Text content from answer sections
        - Joins chunks appropriately
        
        Args:
            extract_images: Whether to extract images
            image_dir: Directory to save images
            query: The current query being searched (to identify the correct answer)
            previous_answers: List of previous answer containers to exclude
        """
        if not self.page:
            logger.warning("get_response_text: page is None")
            return ""
        
        logger.debug(f"get_response_text: Starting extraction for query: {query[:50] if query else 'None'}...")
        
        try:
            # Pass previous answers and query as a single argument object
            eval_args = {
                'previousAnswers': previous_answers or [],
                'queryText': query or ''
            }
            result = self.page.evaluate("""
                (args) => {
                    const previousAnswers = args.previousAnswers || [];
                    const queryText = args.queryText || '';
                    const main = document.querySelector('main');
                    if (!main) {
                        console.log('[ERROR] main element not found');
                        return '';  // Return empty string instead of null
                    }
                    console.log('[DEBUG] main element found, extracting content...');
                    
                    // Find the main answer section - look for the answer content area
                    // This should match how the API extracts from 'chunks' or 'structured_answer'
                    let answerParts = [];
                    
                    // Strategy 1: Look for answer paragraphs (main content, not sources)
                    // Find paragraphs that are part of the answer, not sources or related questions
                    const allParagraphs = main.querySelectorAll('p');
                    const answerParagraphs = [];
                    
                    for (const p of allParagraphs) {
                        const text = (p.innerText || p.textContent || '').trim();
                        // Skip very short paragraphs (likely UI elements)
                        if (text.length < 50) continue;
                        
                        // Skip paragraphs that are clearly in sources or related sections
                        let parent = p.parentElement;
                        let isSourceOrRelated = false;
                        while (parent && parent !== main) {
                            const parentText = (parent.textContent || '').toLowerCase();
                            const parentClass = (parent.className || '').toLowerCase();
                            if (parentText.includes('source') || parentText.includes('related') ||
                                parentClass.includes('source') || parentClass.includes('related')) {
                                isSourceOrRelated = true;
                                break;
                            }
                            parent = parent.parentElement;
                        }
                        
                        if (!isSourceOrRelated && text.length > 50) {
                            answerParagraphs.push(text);
                        }
                    }
                    
                    // Strategy 2: Collect ALL answer containers - GET EVERYTHING, filter later
                    // Don't filter aggressively - capture all content first
                    // Only skip obvious UI states, not content
                    const containers = main.querySelectorAll('div, section, article');
                    let allAnswerContainers = [];
                    let answerContainer = null;
                    let maxTextLength = 0;
                    let newestContainer = null;
                    let newestTop = -1;
                    
                    for (const container of containers) {
                        const text = (container.innerText || container.textContent || '').trim();
                        const containerText = text.toLowerCase();
                        
                        // Only skip obvious UI states (thinking, searching)
                        if (containerText.includes('thinking...') || 
                            (containerText === 'searching' && text.length < 50) ||
                            (containerText === 'exploring' && text.length < 50)) {
                            continue;
                        }
                        
                        // Skip if it's just a single word or very short (likely UI label)
                        if (text.split(/\\s+/).length <= 1 && text.length < 20) continue;
                        
                        // Get container position first
                        const rect = container.getBoundingClientRect();
                        const containerTop = rect.top;
                        const firstWords = text.substring(0, 50);
                        
                        // Check if this is a previous answer (skip it)
                        let isPreviousAnswer = false;
                        for (const prev of previousAnswers) {
                            // If the first words match and position is similar, it's likely the same answer
                            // Use a more lenient check - if position is close and text length is similar
                            const positionDiff = Math.abs(containerTop - prev.top);
                            const lengthDiff = Math.abs(text.length - prev.textLength);
                            
                            if (positionDiff < 200 && 
                                (firstWords === prev.firstWords || lengthDiff < 100)) {
                                isPreviousAnswer = true;
                                break;
                            }
                        }
                        
                        if (isPreviousAnswer) continue;
                        
                        // Check if container contains query-related content (define before use)
                        const containsQuery = queryText && text.toLowerCase().includes(queryText.toLowerCase().substring(0, 20));
                        
                        // GET EVERYTHING - minimal filtering, just collect all substantial containers
                        // Only skip if it's clearly not answer content
                        const textLines = text.split('\\n').filter(l => l.trim().length > 0);
                        
                        // Skip containers that are ONLY questions (related questions section)
                        const questionLines = textLines.filter(l => l.trim().endsWith('?')).length;
                        if (questionLines > 3 && questionLines / textLines.length > 0.8 && text.length < 500) {
                            continue; // This is likely just related questions, skip it
                        }
                        
                        // Collect ALL containers with substantial content - don't filter too much
                        // Lower threshold to capture everything
                        if (text.length > 100) {
                            // Store container with its position and metadata
                            allAnswerContainers.push({
                                container: container,
                                text: text,
                                top: containerTop,
                                length: text.length,
                                containsQuery: containsQuery || false
                            });
                            
                            // Also track for backward compatibility
                            if (text.length > maxTextLength) {
                                maxTextLength = text.length;
                                answerContainer = container;
                            }
                        }
                        
                        // Track containers by position - newest answers appear lower on the page
                        
                        // Prefer containers that:
                        // 1. Are not previous answers
                        // 2. Are lower on the page (newer)
                        // 3. Contain substantial content (including tables, lists, etc.)
                        // 4. Optionally contain query-related keywords
                        if (containerTop > newestTop && text.length > 200) {
                            newestTop = containerTop;
                            newestContainer = container;
                        }
                        
                        // If this container contains query keywords and has substantial content, prefer it
                        if (containsQuery && text.length > 200 && (!answerContainer || containsQuery)) {
                            answerContainer = container;
                            maxTextLength = text.length;
                        }
                    }
                    
                    // Log container discovery for debugging
                    console.log(`[TELEMETRY] Found ${allAnswerContainers.length} potential answer containers`);
                    for (let i = 0; i < Math.min(5, allAnswerContainers.length); i++) {
                        const c = allAnswerContainers[i];
                        console.log(`[TELEMETRY] Container ${i+1}: position=${Math.round(c.top)}, length=${c.length}, containsQuery=${c.containsQuery}, preview="${c.text.substring(0, 80).replace(/\\n/g, ' ')}..."`);
                    }
                    
                    // Filter and sort all answer containers
                    // Remove duplicates (containers that are parents/children of each other)
                    const uniqueContainers = [];
                    for (let i = 0; i < allAnswerContainers.length; i++) {
                        const candidate = allAnswerContainers[i];
                        let isDuplicate = false;
                        
                        // Check if this container is a child of another container we've already added
                        for (let j = 0; j < uniqueContainers.length; j++) {
                            const existing = uniqueContainers[j];
                            if (existing.container.contains(candidate.container)) {
                                // Candidate is a child of existing - skip it (existing has more content)
                                isDuplicate = true;
                                break;
                            }
                            if (candidate.container.contains(existing.container)) {
                                // Existing is a child of candidate - replace it with candidate
                                uniqueContainers[j] = candidate;
                                isDuplicate = true;
                                break;
                            }
                        }
                        
                        if (!isDuplicate) {
                            uniqueContainers.push(candidate);
                        }
                    }
                    
                    // Sort by position (top to bottom) to maintain answer order
                    uniqueContainers.sort((a, b) => a.top - b.top);
                    
                    console.log(`[TELEMETRY] After deduplication: ${uniqueContainers.length} unique containers`);
                    
                    // Filter to only include containers that are part of the current answer
                    // Exclude containers that are too far apart (likely different answers)
                    // But be more lenient to capture comprehensive answers
                    const filteredContainers = [];
                    if (uniqueContainers.length > 0) {
                        // If we have containers, include them all if they're reasonably close
                        // Start with the first container (or one containing query keywords)
                        let startIndex = 0;
                        for (let i = 0; i < uniqueContainers.length; i++) {
                            if (uniqueContainers[i].containsQuery) {
                                startIndex = i;
                                break;
                            }
                        }
                        
                        filteredContainers.push(uniqueContainers[startIndex]);
                        let lastTop = uniqueContainers[startIndex].top;
                        
                        // Add subsequent containers that are close enough (within 3000px vertically - more lenient)
                        // This captures all parts of the same answer
                        for (let i = startIndex + 1; i < uniqueContainers.length; i++) {
                            const container = uniqueContainers[i];
                            // If container is close to previous ones (same answer section)
                            // OR if it has substantial content (even if further apart)
                            // Be more lenient to capture comprehensive answers
                            if (container.top - lastTop < 3000 || 
                                (container.length > 300 && container.top - lastTop < 8000) ||
                                (i < startIndex + 5)) { // Include at least first 5 containers
                                filteredContainers.push(container);
                                lastTop = container.top;
                            } else if (container.length > 1000) {
                                // Very large containers should be included even if further apart
                                filteredContainers.push(container);
                                lastTop = container.top;
                            }
                        }
                    }
                
                // Convert to markdown preserving links, filtering out UI elements
                // Define UI labels to skip - comprehensive list to remove bloat
                const uiLabels = [
                    'home', 'discover', 'library', 'pro', 'sign in', 'sign up', 
                    'answer', 'images', 'sources', 'related', 'ask a follow-up', 
                    'share', 'more', 'save', 'delete', 'edit', 'account', 'upgrade', 
                    'install', 'download comet', 'deep dive on perplexity finance',
                    'follow', 'price alert', 'prev close', '24h volume', 'high', 'open',
                    'low', 'year high', 'year low', 'market cap'
                ];
                
                // Define this function outside so it can be used in fallbacks too
                const nodeToMarkdown = (node, depth = 0) => {
                            // Skip UI labels and navigation elements
                            if (node.nodeType === Node.ELEMENT_NODE) {
                                const nodeText = (node.innerText || node.textContent || '').trim().toLowerCase();
                                for (const label of uiLabels) {
                                    if (nodeText === label || (nodeText.length < 50 && nodeText.includes(label))) {
                                        return '';
                                    }
                                }
                                // Skip if it's just a single word that's a common UI label
                                if (nodeText.split(/\\s+/).length === 1 && nodeText.length < 20 && 
                                    (nodeText === 'answer' || nodeText === 'images' || nodeText === 'sources')) {
                                    return '';
                                }
                            }
                            if (node.nodeType === Node.TEXT_NODE) {
                                return node.textContent || '';
                            }
                            if (node.nodeType !== Node.ELEMENT_NODE) {
                                return '';
                            }
                            const tagName = node.tagName.toLowerCase();
                            
                            if (tagName === 'a') {
                                const href = node.getAttribute('href');
                                const text = (node.innerText || node.textContent || '').trim();
                                if (href && text) {
                                    let url = href;
                                    if (url.startsWith('//')) {
                                        url = 'https:' + url;
                                    } else if (url.startsWith('/') && !url.startsWith('//')) {
                                        if (url.includes('http')) {
                                            url = 'https://www.perplexity.ai' + url;
                                        } else {
                                            return text;
                                        }
                                    }
                                    if (url.startsWith('http') && !url.includes('perplexity.ai')) {
                                        return `[${text}](${url})`;
                                    }
                                    return text;
                                }
                                return text || '';
                            }
                            
                            if (tagName === 'p') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child);
                                }
                                return content + '\\n\\n';
                            }
                            
                            if (tagName === 'div') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child, depth + 1);
                                }
                                // Only convert to heading if it's substantial content, not a UI label
                                const text = (node.innerText || node.textContent || '').trim();
                                const textLower = text.toLowerCase();
                                // Skip if it's a UI label
                                if (uiLabels.some(label => textLower === label || textLower.startsWith(label + ' '))) {
                                    return content;
                                }
                                // Only make it a heading if it's substantial and looks like a real section
                                if (text.length > 20 && text.length < 100 && text.endsWith(':')) {
                                    return '\\n### ' + content.trim() + '\\n\\n';
                                }
                                return content + '\\n\\n';
                            }
                            
                            if (tagName === 'h1' || tagName === 'h2' || tagName === 'h3' || tagName === 'h4') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child, depth + 1);
                                }
                                const text = content.trim().toLowerCase();
                                // Skip headings that are just UI labels
                                if (uiLabels.some(label => text === label || text.startsWith(label + ' '))) {
                                    return '';
                                }
                                // Only include if it's substantial content
                                if (content.trim().length > 10) {
                                    const level = parseInt(tagName.charAt(1));
                                    const hashes = '#'.repeat(level + 2);  // h1 -> ###, h2 -> ####, etc.
                                    return '\\n' + hashes + ' ' + content.trim() + '\\n\\n';
                                }
                                return '';
                            }
                            
                            if (tagName === 'ul' || tagName === 'ol') {
                                let content = '';
                                let index = 1;
                                for (const child of Array.from(node.childNodes)) {
                                    if (child.tagName && child.tagName.toLowerCase() === 'li') {
                                        const liContent = nodeToMarkdown(child);
                                        if (tagName === 'ol') {
                                            content += index + '. ' + liContent.trim() + '\\n';
                                            index++;
                                        } else {
                                            content += '- ' + liContent.trim() + '\\n';
                                        }
                                    }
                                }
                                return content + '\\n';
                            }
                            
                            if (tagName === 'li') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child);
                                }
                                return content.trim();
                            }
                            
                            if (tagName === 'table') {
                                let content = '';
                                const rows = node.querySelectorAll('tr');
                                for (const row of rows) {
                                    const cells = row.querySelectorAll('td, th');
                                    const rowContent = Array.from(cells).map(cell => {
                                        const cellText = (cell.innerText || cell.textContent || '').trim();
                                        return cellText;
                                    }).filter(t => t.length > 0).join(' | ');
                                    if (rowContent) {
                                        content += rowContent + '\\n';
                                        // Add separator after header row
                                        if (row.querySelector('th')) {
                                            content += Array.from(cells).map(() => '---').join(' | ') + '\\n';
                                        }
                                    }
                                }
                                return content + '\\n';
                            }
                            
                            if (tagName === 'tr') {
                                let content = '';
                                const cells = node.querySelectorAll('td, th');
                                const rowContent = Array.from(cells).map(cell => {
                                    const cellText = (cell.innerText || cell.textContent || '').trim();
                                    return cellText;
                                }).filter(t => t.length > 0).join(' | ');
                                return rowContent + '\\n';
                            }
                            
                            if (tagName === 'td' || tagName === 'th') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child);
                                }
                                return content.trim();
                            }
                            
                            if (tagName === 'br') {
                                return '\\n';
                            }
                            
                            if (tagName === 'strong' || tagName === 'b') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child);
                                }
                                return `**${content}**`;
                            }
                            
                            if (tagName === 'em' || tagName === 'i') {
                                let content = '';
                                for (const child of Array.from(node.childNodes)) {
                                    content += nodeToMarkdown(child);
                                }
                                return `*${content}*`;
                            }
                            
                            let content = '';
                            for (const child of Array.from(node.childNodes)) {
                                content += nodeToMarkdown(child);
                            }
                            return content;
                        };
                
                // Extract text from ALL answer containers (comprehensive extraction)
                // This ensures we capture the entire answer, not just one container
                if (filteredContainers.length > 0) {
                    // Combine content from all containers in order
                    const allTextParts = [];
                    
                    // Extract text from ALL containers and combine them
                    for (const containerInfo of filteredContainers) {
                        const container = containerInfo.container;
                        let containerText = nodeToMarkdown(container);
                        
                        // Clean up the text
                        containerText = containerText.replace(/\\n{3,}/g, '\\n\\n').trim();
                        
                        // Remove citation markers (like "source+1", "example.com+2")
                        containerText = containerText.replace(/[a-zA-Z0-9.-]+\\+\\d+[^\\w\\s]*/g, '').trim();
                        
                        // Remove zero-width spaces and other problematic characters
                        containerText = containerText.replace(/\\u200b/g, '').replace(/\\u200c/g, '').replace(/\\u200d/g, '');
                        
                        // GET EVERYTHING - but skip query text at the start
                        const lines = containerText.split('\\n').filter(l => l.trim().length > 0);
                        
                        // Find where actual answer starts (skip query text and UI elements)
                        let startIndex = 0;
                        const queryStart = queryText ? queryText.toLowerCase().substring(0, 30) : '';
                        
                        for (let i = 0; i < Math.min(20, lines.length); i++) {
                            const line = lines[i].trim().toLowerCase();
                            
                            // Skip if it's the query text
                            if (queryStart && line.includes(queryStart) && line.length < 300) {
                                continue;
                            }
                            
                            // Skip obvious single-word UI labels
                            const obviousUI = ['home', 'discover', 'spaces', 'finance', 'share', 'answer'];
                            if (obviousUI.includes(line) && line.length < 20) {
                                continue;
                            }
                            
                            // If we find substantial content that's not the query, start from here
                            if (line.length > 80 && (!queryStart || !line.includes(queryStart))) {
                                startIndex = i;
                                break;
                            }
                            
                            // If we find answer markers, start from there
                            if (line.includes('here is a') || 
                                line.includes('latest cryptocurrency') ||
                                line.includes('major news') ||
                                line.includes('upcoming events') ||
                                line.includes('market sentiment')) {
                                startIndex = i;
                                break;
                            }
                        }
                        
                        // Get all content from startIndex onwards - don't filter aggressively
                        const cleanedText = lines.slice(startIndex).join('\\n').trim();
                        
                        // Additional cleanup: remove query text if it appears at the start
                        let finalText = cleanedText;
                        if (queryText && finalText.toLowerCase().startsWith(queryText.toLowerCase().substring(0, 50))) {
                            // Find where the actual answer starts (after the query)
                            const queryLines = queryText.toLowerCase().split('\\n');
                            const firstQueryLine = queryLines[0].substring(0, Math.min(50, queryLines[0].length));
                            const textLines = finalText.split('\\n');
                            let answerStartIndex = 0;
                            for (let i = 0; i < Math.min(10, textLines.length); i++) {
                                const line = textLines[i].toLowerCase();
                                // Skip lines that contain query text
                                if (line.includes(firstQueryLine.substring(0, 30))) {
                                    answerStartIndex = i + 1;
                                } else if (answerStartIndex > 0 && line.length > 50) {
                                    // Found first real content line after query
                                    break;
                                }
                            }
                            if (answerStartIndex > 0) {
                                finalText = textLines.slice(answerStartIndex).join('\\n').trim();
                            }
                        }
                        
                        if (finalText.length > 100) {
                            allTextParts.push(finalText);
                        }
                    }
                    
                    console.log(`[TELEMETRY] Combining ${allTextParts.length} text parts into final answer`);
                    for (let i = 0; i < allTextParts.length; i++) {
                        console.log(`[TELEMETRY] Part ${i+1}: ${allTextParts[i].length} chars, preview="${allTextParts[i].substring(0, 80).replace(/\\n/g, ' ')}..."`);
                    }
                    
                    // Combine all parts with proper spacing - GET EVERYTHING
                    let combinedText = allTextParts.join('\\n\\n').trim();
                    
                    console.log(`[TELEMETRY] Combined text length: ${combinedText.length} characters`);
                    
                    // Minimal cleanup: just remove excessive newlines, keep all content
                    combinedText = combinedText.replace(/\\n{4,}/g, '\\n\\n\\n').trim();
                    
                    // Remove duplicate content only if it's exact duplicates (containers overlap)
                    const lines = combinedText.split('\\n');
                    const finalLines = [];
                    const seenExactLines = new Set();
                    for (const line of lines) {
                        const lineTrimmed = line.trim();
                        // Only skip if it's an exact duplicate of a previous line
                        if (lineTrimmed.length > 0) {
                            if (!seenExactLines.has(lineTrimmed.toLowerCase())) {
                                seenExactLines.add(lineTrimmed.toLowerCase());
                                finalLines.push(line);
                            } else if (lineTrimmed.length > 200) {
                                // Keep long lines even if similar (might be important)
                                finalLines.push(line);
                            }
                        }
                    }
                    
                    return finalLines.join('\\n').replace(/\\n{3,}/g, '\\n\\n').trim();
                }
                
                // Fallback to single container if filteredContainers didn't work
                // GET EVERYTHING - minimal filtering
                if (answerContainer) {
                    // Use the same nodeToMarkdown function (defined above)
                    let allText = nodeToMarkdown(answerContainer);
                    allText = allText.replace(/\\n{3,}/g, '\\n\\n').trim();
                    allText = allText.replace(/[a-zA-Z0-9.-]+\\+\\d+[^\\w\\s]*/g, '').trim();
                    allText = allText.replace(/\\u200b/g, '').replace(/\\u200c/g, '').replace(/\\u200d/g, '');
                    // Keep everything - just remove excessive newlines
                    return allText.replace(/\\n{4,}/g, '\\n\\n\\n').trim();
                }
                
                // Fallback: If no container found, try to get all substantial content from main
                // This handles cases where the answer is spread across multiple containers
                if (!answerContainer && answerParagraphs.length > 0) {
                    // Join paragraphs with double newlines for better formatting
                    return answerParagraphs.join('\\n\\n').trim();
                }
                
                // Last resort: Get all text from main, excluding sources and UI
                if (!answerContainer) {
                    const allText = (main.innerText || main.textContent || '').trim();
                    // Filter out sources and related sections
                    const lines = allText.split('\\n');
                    const filteredLines = [];
                    let inSourceSection = false;
                    for (const line of lines) {
                        const lineLower = line.toLowerCase().trim();
                        if (lineLower.includes('source') || lineLower.includes('related question') ||
                            lineLower.includes('ask a follow-up')) {
                            inSourceSection = true;
                            continue;
                        }
                        if (inSourceSection && line.trim().length < 50) {
                            continue;
                        }
                        if (line.trim().length > 20) {
                            filteredLines.push(line);
                            inSourceSection = false;
                        }
                    }
                    const finalText = filteredLines.join('\\n').trim();
                    if (finalText.length > 200) {
                        return finalText;
                    }
                }
                
                return '';
                }
            """, eval_args)
            
            if result:
                logger.debug(f"get_response_text: Extracted {len(result)} characters")
                # Show first 200 chars of result for debugging
                preview = result[:200].replace('\n', ' ')
                logger.debug(f"get_response_text: Preview: {preview}...")
                return result
            else:
                logger.warning("get_response_text: JavaScript evaluation returned None or empty")
        except Exception as e:
            logger.error(f"Error extracting response text: {str(e)}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            pass
        
        logger.warning("get_response_text: Returning empty string")
        return ""
    
    def get_structured_response(
        self,
        query: str,
        extract_images: bool = False,
        image_dir: Optional[str] = None,
        previous_answers: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Extract structured response matching SearchResponse format.
        Uses the same answer extraction logic as get_response_text (matching direct API method).
        """
        logger.debug(f"get_structured_response: Starting for query: {query[:50]}...")
        
        if not self.page:
            logger.warning("get_structured_response: page is None")
            return {
                'query': query,
                'answer': '',
                'sources': [],
                'related_questions': [],
                'mode': 'auto',
                'model': None
            }
        
        # First, get the answer text using the improved extraction method
        logger.debug("get_structured_response: Calling get_response_text...")
        answer_text = self.get_response_text(
            extract_images=extract_images, 
            image_dir=image_dir,
            query=query,
            previous_answers=previous_answers
        )
        
        logger.debug(f"get_structured_response: Got answer_text length: {len(answer_text) if answer_text else 0}")
        
        try:
            structured_data = self.page.evaluate("""
                () => {
                    const main = document.querySelector('main');
                    if (!main) return null;
                    
                    // Extract sources
                    const sources = [];
                    const seenUrls = new Set();
                    const allLinks = main.querySelectorAll('a[href]');
                    
                    console.log(`[TELEMETRY] Found ${allLinks.length} total links in page`);
                    
                    allLinks.forEach(link => {
                        let href = link.getAttribute('href');
                        if (!href) return;
                        
                        let url = href;
                        // Normalize URL format
                        if (url.startsWith('//')) {
                            url = 'https:' + url;
                        } else if (url.startsWith('/') && !url.startsWith('//')) {
                            // Relative URL - could be internal perplexity link, skip those
                            // But keep if it's a redirect or external link indicator
                            if (url.startsWith('/search') || url.startsWith('/thread')) {
                                return; // Skip internal perplexity navigation
                            }
                            // Check if it's actually an external URL embedded in path
                            if (url.includes('http')) {
                                // Extract embedded URL
                                const urlMatch = url.match(/https?:\\/\\/[^\\s\\)]+/);
                                if (urlMatch) {
                                    url = urlMatch[0];
                                } else {
                                    return; // Not a valid external URL
                                }
                            } else {
                                return; // Skip other relative paths
                            }
                        }
                        
                        // Only include external URLs (not perplexity.ai itself)
                        if (url.startsWith('http') && !url.includes('perplexity.ai') && !seenUrls.has(url)) {
                            seenUrls.add(url);
                            let title = (link.innerText || link.textContent || link.getAttribute('title') || '').trim();
                            
                            // If no title or very short title, use domain as title
                            if (!title || title.length < 2) {
                                try {
                                    const urlObj = new URL(url);
                                    title = urlObj.hostname.replace('www.', '');
                                } catch(e) {
                                    title = url;
                                }
                            }
                            
                            // Be more lenient with title length - accept any reasonable length
                            // Only filter out obviously invalid ones (empty or extremely long)
                            if (title && title.length >= 1 && title.length < 500) {
                                sources.push({
                                    title: title.replace(/\\s+/g, ' ').trim(),
                                    url: url,
                                    snippet: '',
                                    citation: title
                                });
                            }
                        }
                    });
                    
                    console.log(`[TELEMETRY] Extracted ${sources.length} external source URLs (deduplicated)`);
                    
                    // Extract related questions
                    const relatedQuestions = [];
                    const relatedSection = Array.from(main.querySelectorAll('*')).find(el => {
                        const text = (el.innerText || el.textContent || '').trim();
                        return text === 'Related' || text.startsWith('Related');
                    });
                    
                    if (relatedSection) {
                        const container = relatedSection.closest('div, section, article') || relatedSection.parentElement;
                                if (container) {
                            const buttons = container.querySelectorAll('button');
                            buttons.forEach(btn => {
                                const text = (btn.innerText || btn.textContent || '').trim();
                                if (text && text.length > 15 && text.length < 200) {
                                    if (text.endsWith('?') || text.includes('How') || text.includes('What') || text.includes('Explain')) {
                                        if (!relatedQuestions.includes(text)) {
                                            relatedQuestions.push(text);
                                        }
                                    }
                                }
                            });
                        }
                    }
                    
                    return {
                        sources: sources,
                        related_questions: relatedQuestions,
                        mode: 'auto',
                        model: null
                    };
                }
            """)
            
            if structured_data:
                logger.debug(f"get_structured_response: Got structured data with {len(structured_data.get('sources', []))} sources")
                result = {
                    'query': query,
                    'answer': answer_text,  # Use the improved answer extraction
                    'sources': structured_data.get('sources', []),
                    'related_questions': structured_data.get('related_questions', []),
                    'mode': structured_data.get('mode', 'auto'),
                    'model': structured_data.get('model'),
                    'timestamp': datetime.now().isoformat()
                }
                logger.info(f"get_structured_response: Returning result with answer length: {len(result.get('answer', ''))}")
                return result
            else:
                logger.warning("get_structured_response: structured_data is None or empty")
        except Exception as e:
            logger.error(f"Error extracting structured data: {str(e)}")
            import traceback
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            pass
        
        # Fallback - return with answer text we already extracted
        logger.info(f"get_structured_response: Using fallback with answer length: {len(answer_text)}")
        return {
            'query': query,
            'answer': answer_text,
            'sources': [],
            'related_questions': [],
            'mode': 'auto',
            'model': None,
            'timestamp': datetime.now().isoformat()
        }
    
    
    def get_page_content(self) -> str:
        """Get full page content"""
        if not self.page:
            return ""
        try:
            return self.page.content()
        except Exception:
            return ""
    
    def save_screenshot(self, filepath: str) -> None:
        """Save screenshot of current page"""
        if not self.page:
            return
        try:
            self.page.screenshot(path=filepath, full_page=True)
        except Exception:
            pass
    
    def extract_cookies(self, domain: str = "perplexity.ai") -> Dict[str, str]:
        """
        Extract cookies from current browser context using CDP
        
        Args:
            domain: Domain to extract cookies for
            
        Returns:
            Dictionary of cookie name -> value
        """
        if not self.context:
            raise Exception("Browser context not available")
        
        try:
            # Try CDP method first (more reliable)
            if self.page:
                try:
                    cdp_session = self.context.new_cdp_session(self.page)
                    cookies_response = cdp_session.send('Network.getCookies', {
                        'urls': [f'https://www.{domain}', f'https://{domain}']
                    })
                    
                    cookie_dict = {}
                    if 'cookies' in cookies_response:
                        for cookie in cookies_response['cookies']:
                            cookie_dict[cookie['name']] = cookie['value']
                    
                    if cookie_dict:
                        return cookie_dict
                except Exception as e:
                    print(f"CDP extraction failed: {e}, using fallback")
            
            # Fallback: Use Playwright's cookie API
            cookies = self.context.cookies(f'https://www.{domain}')
            cookie_dict = {}
            for cookie in cookies:
                cookie_dict[cookie['name']] = cookie['value']
            
            return cookie_dict
        except Exception as e:
            raise Exception(f"Failed to extract cookies: {str(e)}")
    
    def save_cookies_to_profile(self, profile_name: str, domain: str = "perplexity.ai") -> bool:
        """
        Extract cookies from current browser session and save to profile
        
        Args:
            profile_name: Profile name to save cookies as
            domain: Domain to extract cookies for
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from ..auth.cookie_manager import CookieManager  # type: ignore
        except ImportError:
            try:
                from auth.cookie_manager import CookieManager  # type: ignore
            except ImportError:
                raise ImportError("CookieManager not available")
        
        cookies = self.extract_cookies(domain=domain)
        
        if not cookies:
            logger.warning("No cookies extracted")
            return False
        
        cookie_manager = CookieManager()
        cookie_manager.save_cookies(cookies, name=profile_name)
        logger.info(f"Saved {len(cookies)} cookies to profile: {profile_name}")
        return True
    
    def close(self) -> None:
        """Close browser and cleanup - suppress all errors"""
        # Suppress warnings and stderr output during cleanup
        import warnings
        import sys
        import os
        
        warnings.filterwarnings('ignore')
        
        # Redirect stderr to devnull to suppress Playwright/Camoufox cleanup errors
        old_stderr = sys.stderr
        try:
            sys.stderr = open(os.devnull, 'w')
        except Exception:
            pass
        
        try:
            if self.tab_manager:
                self.tab_manager.close_all()
                self.tab_manager = None
        except Exception:
            pass
        
        try:
            if self.page:
                try:
                    if not self.page.is_closed():
                        self.page.close()
                except Exception:
                    pass
                self.page = None
        except Exception:
            pass
        
        try:
            if self.context:
                self.context.close()
                self.context = None
        except Exception:
            pass
        
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
        except Exception:
            pass
        
        try:
            # If using Camoufox, exit the context manager properly
            if self._camoufox:
                try:
                    self._camoufox.__exit__(None, None, None)
                except Exception:
                    pass
                self._camoufox = None
            elif self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None
        except Exception:
            pass
        
        # Small delay to ensure cleanup completes
        try:
            import time
            time.sleep(0.1)
        except Exception:
            pass
        finally:
            # Restore stderr
            try:
                if sys.stderr != old_stderr:
                    sys.stderr.close()
                sys.stderr = old_stderr
            except Exception:
                pass
