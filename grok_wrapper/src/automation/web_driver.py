"""
Browser automation for Grok.com using Playwright
"""
import logging
import os
import platform
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from .js_utils import (
    verify_deepsearch_enabled_js,
    find_private_button_js,
    verify_private_mode_js
)
from .page_verification import verify_grok_homepage_js
from .popup_handler import close_popups_js

logger = logging.getLogger(__name__)
logging.getLogger("playwright").setLevel(logging.WARNING)
logging.getLogger("camoufox").setLevel(logging.WARNING)

# Removed Camoufox - using Chrome instead (like MCP browser extension)
CAMOUFOX_AVAILABLE = False

PLAYWRIGHT_AVAILABLE = False
if TYPE_CHECKING:
    from playwright.sync_api import Browser, BrowserContext, Page, Playwright

try:
    from playwright.sync_api import (
        Browser,
        BrowserContext,
        Page,
        Playwright,
        sync_playwright,
    )
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    if TYPE_CHECKING:
        Browser = None  # type: ignore
        BrowserContext = None  # type: ignore
        Page = None  # type: ignore
        Playwright = None  # type: ignore


class GrokWebDriver:
    """Browser automation for Grok.com using Playwright"""
    _platform_system = platform.system()

    def __init__(
        self,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        stealth_mode: bool = True,
        debug_mode: bool = False,
    ):
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError(
                "Playwright is not installed. Install it with: pip install playwright && playwright install chromium"
            )

        self.headless = headless
        self.user_data_dir = user_data_dir
        self.stealth_mode = stealth_mode
        self.debug_mode = debug_mode
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._cookies: Optional[Dict[str, str]] = None
        self._is_headless: bool = headless
        
        # Set logging level based on debug mode
        if not debug_mode:
            logger.setLevel(logging.WARNING)

    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """Store cookies to be injected before navigation"""
        self._cookies = cookies

    def start(self, debug_network: bool = False) -> None:
        """Start browser and initialize context"""
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright is not installed")

        logger.debug("🚀 Starting browser...")
        
        # Use actual Chrome browser (not Chromium) with MCP browser extension flags
        self.playwright = sync_playwright().start()

        # Find Chrome executable path (Windows)
        chrome_paths = []
        if platform.system() == "Windows":
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
            ]
        elif platform.system() == "Darwin":  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            ]
        else:  # Linux
            chrome_paths = [
                "/usr/bin/google-chrome",
                "/usr/bin/google-chrome-stable",
                "/usr/bin/chromium-browser",
            ]
        
        chrome_executable = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_executable = path
                logger.debug(f"Found Chrome at: {chrome_executable}")
                break
        
        if not chrome_executable:
            logger.warning("Chrome executable not found, falling back to Chromium")
            chrome_executable = None

        # Chrome launch options (exact flags from MCP browser extension)
        launch_options: Dict[str, Any] = {
            "headless": self.headless,
            "args": [
                "--disable-field-trial-config",
                "--disable-background-networking",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-back-forward-cache",
                "--disable-breakpad",
                "--disable-client-side-phishing-detection",
                "--disable-component-extensions-with-background-pages",
                "--disable-component-update",
                "--no-default-browser-check",
                "--disable-default-apps",
                "--disable-dev-shm-usage",
                "--disable-features=AcceptCHFrame,AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument,OptimizationHints,AutomationControlled",
                "--enable-features=CDPScreenshotNewSurface",
                "--allow-pre-commit-input",
                "--disable-hang-monitor",
                "--disable-ipc-flooding-protection",
                "--disable-popup-blocking",
                "--disable-prompt-on-repost",
                "--disable-renderer-backgrounding",
                "--force-color-profile=srgb",
                "--metrics-recording-only",
                "--no-first-run",
                "--password-store=basic",
                "--use-mock-keychain",
                "--no-service-autorun",
                "--export-tagged-pdf",
                "--disable-search-engine-choice-screen",
                "--unsafely-disable-devtools-self-xss-warnings",
                "--edge-skip-compat-layer-relaunch",
                "--disable-infobars",
                "--disable-search-engine-choice-screen",
                "--disable-sync",
            ],
        }
        
        # Add headless-specific flags for better compatibility
        if self.headless:
            launch_options["args"].extend([
                "--disable-gpu",  # GPU not needed in headless
                "--disable-software-rasterizer",  # Software rasterizer not needed
                "--no-sandbox",  # Required for some headless environments
                "--disable-setuid-sandbox",  # Required for some headless environments
            ])

        # Use actual Chrome executable if found
        if chrome_executable:
            launch_options["executable_path"] = chrome_executable
            logger.debug(f"Using Chrome executable: {chrome_executable}")

        # Note: user_data_dir can cause issues in headless mode on some systems
        # Only use it if not in headless mode, or if explicitly needed
        if self.user_data_dir:
            if self.headless:
                logger.debug("⚠ Using user_data_dir in headless mode - may cause issues on some systems")
            launch_options["user_data_dir"] = self.user_data_dir

        # Launch Chrome (actual Chrome, not Chromium)
        logger.debug(f"Launching Chrome in {'headless' if self.headless else 'headed'} mode")
        try:
            self.browser = self.playwright.chromium.launch(**launch_options)
        except Exception as e:
            if self.headless:
                logger.error(f"Failed to launch Chrome in headless mode: {e}")
                logger.debug("This might be due to missing dependencies or permissions")
                logger.debug("Try running without --headless first to ensure Chrome works")
            raise

        # Create context
        context_options: Dict[str, Any] = {
            "viewport": {"width": 1024, "height": 720},
            "ignore_https_errors": False,
            "java_script_enabled": True,
            "locale": "en-US",
            "timezone_id": "America/New_York",
            "color_scheme": "light",
        }

        # Enhanced stealth mode
        if self.stealth_mode:
            context_options["extra_http_headers"] = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            # Use Chrome user agent (like MCP browser extension)
            context_options["user_agent"] = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
            )

        if not self.browser:
            raise Exception("Browser not initialized")
        
        self.context = self.browser.new_context(**context_options)  # type: ignore

        # Inject stealth JavaScript
        if self.stealth_mode:
            self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Chrome-specific properties (already present in Chrome, but ensure they're correct)
                if (!window.chrome) {
                    window.chrome = { runtime: {} };
                }
                
                // Ensure Chrome-specific navigator properties
                if (!navigator.plugins) {
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5]
                    });
                }
                
                Object.defineProperty(document, 'hidden', {
                    get: () => false,
                    configurable: true
                });
                
                Object.defineProperty(document, 'visibilityState', {
                    get: () => 'visible',
                    configurable: true
                });
            """)

        # Enable network debugging if requested
        if debug_network:
            def log_request(request: Any) -> None:
                logger.debug(f"→ {request.method} {request.url}")

            def log_response(response: Any) -> None:
                logger.debug(f"← {response.status} {response.url}")

            self.context.on("request", log_request)
            self.context.on("response", log_response)

        # CRITICAL: Inject cookies BEFORE creating pages (like Perplexity wrapper)
        # This ensures cookies are available when we navigate
        if self._cookies:
            logger.debug("🍪 Injecting cookies into context (before page creation)...")
            self._inject_cookies()

        # Create main page AFTER cookies are injected
        self.page = self.context.new_page()
        self.page.set_viewport_size({"width": 1024, "height": 720})

    def _inject_cookies(self) -> None:
        """Inject cookies into browser context BEFORE navigation (like Perplexity wrapper)"""
        if not self.context or not self._cookies:
            return

        cookies_list = []
        for name, value in self._cookies.items():
            if not name or not isinstance(value, str) or len(str(value)) > 4000:
                continue
            
            try:
                # Determine which domain this cookie belongs to
                # Grok uses both grok.com and x.ai (for authentication)
                cookie_urls = []
                
                # Check if it's an x.ai cookie (SSO, authentication)
                if any(keyword in name.lower() for keyword in ['sso', 'x-userid', 'x-anonuserid', 'x-challenge', 'x-signature']):
                    cookie_urls.append("https://x.ai")
                    cookie_urls.append("https://accounts.x.ai")
                
                # Always add grok.com
                cookie_urls.append("https://grok.com")
                
                # Use URL-based cookie injection (more reliable than domain/path)
                # This matches how Perplexity wrapper does it
                for url in cookie_urls:
                    cookie_data = {
                        "name": str(name),
                        "value": str(value),
                        "url": url,  # URL-based injection
                        "secure": True,
                        "sameSite": "Lax",
                    }
                    
                    # Handle __Host- prefix (requires path=/ and no domain)
                    if name.startswith("__Host-"):
                        cookie_data["path"] = "/"
                        # Don't set domain for __Host- cookies
                    
                    cookies_list.append(cookie_data)
            except Exception as e:
                logger.debug(f"Failed to format cookie {name}: {e}")
                continue
        
        if cookies_list:
            try:
                self.context.add_cookies(cookies_list)  # type: ignore
                logger.debug(f"✓ Injected {len(cookies_list)} cookies into context (before navigation)")
            except Exception as e:
                logger.warning(f"Failed to inject cookies: {e}, trying individual injection")
                # Fallback: inject individually
                injected = 0
                for cookie in cookies_list:
                    try:
                        self.context.add_cookies([cookie])  # type: ignore
                        injected += 1
                    except Exception:
                        logger.debug(f"Failed to inject cookie: {cookie.get('name')}")
                if injected > 0:
                    logger.debug(f"✓ Injected {injected}/{len(cookies_list)} cookies individually")

    def navigate_to_grok(self, page: Optional[Page] = None) -> None:
        """Navigate to Grok homepage"""
        target_page = page or self.page
        if not target_page:
            raise Exception("Browser not started")

        # Cookies are already injected in start() method - no need to check again

        logger.debug("🌐 Navigating to https://grok.com...")
        nav_start = time.time()
        try:
            target_page.goto(
                "https://grok.com",
                wait_until="domcontentloaded",  # Start with DOM ready
                timeout=5000  # OPTIMIZED: Reduced from 15000ms (15s) to 5000ms (5s)
            )
            nav_time = time.time() - nav_start
            logger.debug(f"✓ Navigated to grok.com (took {nav_time:.2f}s)")
            
            # OPTIMIZED: Removed unnecessary waits - page is already in domcontentloaded state
            # No need to wait for rendering or React/JS - they're already loaded
            
            # Close any popups/modals that appeared
            popup_result = target_page.evaluate(close_popups_js())
            if popup_result and popup_result.get('closed'):
                methods = popup_result.get('methods', [])
                logger.info(f"✓ Closed popup using: {', '.join(methods)}")
                # No wait needed - popup close is instant
            
            # Quick single check if input is ready (no loop)
            verification = target_page.evaluate(verify_grok_homepage_js())
            if verification and verification.get('mainInputVisible'):
                logger.debug("✓ Homepage input ready")
            else:
                logger.debug("⚠ Input check skipped, continuing...")
            
            # Verify cookies are present in the page
            try:
                page_cookies = target_page.context.cookies()
                logger.debug(f"Page has {len(page_cookies)} cookies after navigation")
                
                # Check for key authentication cookies
                auth_cookies = ['sso', 'sso-rw', 'x-userid', 'x-anonuserid', 'x-challenge', 'x-signature']
                found_auth = [c.get('name') for c in page_cookies if c.get('name') in auth_cookies]
                if found_auth:
                    logger.debug(f"✓ Found auth cookies: {found_auth}")
                else:
                    logger.debug("⚠ No authentication cookies found after navigation - cookies may be expired")
                    logger.debug("💡 Try extracting fresh cookies: grok extract-cookies --browser firefox")
                
                # Log all cookie names for debugging
                cookie_names = [c.get('name') for c in page_cookies]
                logger.debug(f"All cookies: {cookie_names[:10]}...")  # First 10
            except Exception as e:
                logger.debug(f"Could not verify cookies: {e}")
        except Exception as e:
            logger.error(f"✗ Failed to navigate to grok.com: {e}")
            raise

    def is_logged_in(self, page: Optional[Page] = None) -> bool:
        """Check if user is logged in"""
        target_page = page or self.page
        if not target_page:
            logger.warning("⚠ Cannot check login: page not available")
            return False

        try:
            logger.debug("🔍 Checking login status...")
            check_start = time.time()
            
            # Wait for page to be fully loaded, especially important in headless mode
            # Cloudflare challenges and React hydration need time to complete
            # First, wait for load state (DOM ready) - reduced timeout
            try:
                target_page.wait_for_load_state("load", timeout=5000)  # Reduced from 8000ms
                logger.debug("✓ Page load state reached")
            except Exception:
                logger.debug("⚠ Load state timeout, continuing...")
            
            # Wait for chat input to appear - this is the most reliable indicator
            # Cloudflare challenges and React hydration must complete before input appears
            # OPTIMIZED: Use single wait_for_selector with visible state (faster than separate attached + visible)
            chat_input_found = False
            selectors_to_try = [
                'textarea[aria-label*="Ask Grok"]',
                'textarea[aria-label*="Ask"]',
                '[contenteditable="true"]',  # Most common, check first
                'textarea'
            ]
            
            # Try to find chat input with optimized timeouts
            for selector in selectors_to_try:
                try:
                    # Wait for element to be visible directly (faster than attached then visible)
                    target_page.wait_for_selector(selector, state="visible", timeout=3000)  # Reduced from 5s+3s
                    chat_input_found = True
                    logger.debug(f"✓ Found chat input with selector: {selector}")
                    break
                except Exception:
                    continue
            
            if not chat_input_found:
                logger.debug("⚠ Chat input not found after waiting - checking URL and other indicators")
            
            # Check URL - if redirected to sign-in, not logged in
            current_url = target_page.url
            logger.debug(f"Current URL: {current_url}")
            
            # Check if we're on a login page
            if 'sign-in' in current_url or 'sign-up' in current_url or 'accounts.x.ai' in current_url:
                logger.debug(f"✗ Not logged in - redirected to: {current_url}")
                return False
            
            # If we're still on grok.com, check for actual login indicators
            if 'grok.com' not in current_url:
                logger.debug(f"Not on grok.com, URL: {current_url}")
                return False
            
            # If chat input was found, we're likely logged in - proceed with verification
            if chat_input_found:
                logger.debug("✓ Chat input found - likely logged in, verifying...")
                # Skip redundant JavaScript check if we already found the input
                # Just verify it's interactive
                try:
                    # Quick verification that input is interactive
                    is_interactive = target_page.evaluate("""
                        () => {
                            const selectors = [
                                'textarea[aria-label*="Ask Grok"]',
                                'textarea[aria-label*="Ask"]',
                                'textarea',
                                '[contenteditable="true"]'
                            ];
                            for (const selector of selectors) {
                                const input = document.querySelector(selector);
                                if (input) {
                                    const rect = input.getBoundingClientRect();
                                    const isVisible = rect.width > 0 && rect.height > 0;
                                    const isEnabled = !input.disabled && !input.readOnly;
                                    if (isVisible && isEnabled) {
                                        return { loggedIn: true, reason: 'has_chat_input_can_interact' };
                                    }
                                }
                            }
                            return { loggedIn: false, reason: 'chat_input_not_interactive' };
                        }
                    """)
                    if is_interactive and is_interactive.get('loggedIn'):
                        logger.debug(f"Login check result: {is_interactive.get('reason')}")
                        check_time = time.time() - check_start
                        logger.debug(f"✓ Logged in (check took {check_time:.2f}s)")
                        return True
                except Exception as e:
                    logger.debug(f"Quick verification failed: {e}, falling back to full check")
            
            # Use JavaScript for more reliable detection with better debugging (only if input not found or quick check failed)
            # Skip this if we already verified login status above
            if not chat_input_found:
                login_status = target_page.evaluate("""
                () => {
                    // Check URL
                    if (window.location.href.includes('sign-in') || 
                        window.location.href.includes('sign-up') || 
                        window.location.href.includes('accounts.x.ai')) {
                        return { loggedIn: false, reason: 'redirected_to_login' };
                    }
                    
                    // Check for chat input - try multiple selectors
                    const selectors = [
                        'textarea[aria-label*="Ask Grok"]',
                        'textarea[aria-label*="Ask"]',
                        'textarea',
                        '[contenteditable="true"]',
                        'input[type="text"]'
                    ];
                    
                    let chatInput = null;
                    let foundSelector = null;
                    for (const selector of selectors) {
                        chatInput = document.querySelector(selector);
                        if (chatInput) {
                            foundSelector = selector;
                            break;
                        }
                    }
                    
                    if (!chatInput) {
                        return { loggedIn: false, reason: 'no_chat_input_found' };
                    }
                    
                    // Check if input is visible and enabled
                    const rect = chatInput.getBoundingClientRect();
                    const isVisible = rect.width > 0 && rect.height > 0;
                    const isEnabled = !chatInput.disabled && !chatInput.readOnly;
                    
                    if (!isVisible) {
                        return { loggedIn: false, reason: 'chat_input_not_visible' };
                    }
                    
                    if (!isEnabled) {
                        return { loggedIn: false, reason: 'chat_input_disabled' };
                    }
                    
                    // Check for visible login buttons in header/nav (not footer)
                    // Be more strict - only count as login button if it's clearly a login button
                    const loginLinks = Array.from(document.querySelectorAll('a[href*="sign-in"], a[href*="login"], button'));
                    const visibleLogin = loginLinks.some(link => {
                        const linkRect = link.getBoundingClientRect();
                        const linkText = (link.textContent || '').toLowerCase().trim();
                        const href = (link.href || '').toLowerCase();
                        
                        // Must be in top portion of page (header area)
                        if (linkRect.top >= 300 || linkRect.height === 0) {
                            return false;
                        }
                        
                        // Must have clear login/sign-in text or href
                        const isLoginButton = (
                            (linkText === 'sign in' || linkText === 'login' || linkText === 'sign up') ||
                            (href.includes('sign-in') || href.includes('/login'))
                        );
                        
                        return isLoginButton;
                    });
                    
                    // Also check if we can actually interact with the chat input
                    // Try to focus it - if we can, we're likely logged in
                    let canInteract = false;
                    try {
                        chatInput.focus();
                        canInteract = document.activeElement === chatInput;
                    } catch (e) {
                        // Can't focus, might not be logged in
                    }
                    
                    // If we have chat input and can interact with it, we're logged in
                    // Even if there are login buttons visible, if we can interact with chat, we're logged in
                    // (Some pages show login buttons even when logged in)
                    // Also check if the input is actually usable (not just present)
                    const isUsable = isVisible && isEnabled && canInteract;
                    const loggedIn = isUsable || (!visibleLogin && chatInput && isVisible && isEnabled);
                    return { 
                        loggedIn: loggedIn, 
                        reason: loggedIn ? 'has_chat_input_can_interact' : (visibleLogin ? 'has_login_buttons' : (isVisible ? 'input_not_enabled' : 'input_not_visible')),
                        foundSelector: foundSelector,
                        hasLoginButtons: visibleLogin,
                        canInteract: canInteract,
                        isVisible: isVisible,
                        isEnabled: isEnabled
                    };
                }
            """)
            
            # Extract login status from result
            if isinstance(login_status, dict):
                is_logged_in = login_status.get('loggedIn', False)
                reason = login_status.get('reason', 'unknown')
                logger.debug(f"Login check result: {reason}")
                if not is_logged_in:
                    logger.debug(f"Login failed: {reason}")
            else:
                # Fallback for old format
                is_logged_in = login_status
                reason = 'legacy_check'
            
            check_time = time.time() - check_start
            if is_logged_in:
                logger.debug(f"✓ Logged in (check took {check_time:.2f}s)")
            else:
                logger.debug(f"✗ Not logged in: {reason} (check took {check_time:.2f}s)")
            return is_logged_in
        except Exception as e:
            logger.warning(f"⚠ Error checking login status: {e}")
            return False

    def wait_for_login(self, timeout: int = 300) -> bool:
        """Wait for user to log in"""
        if not self.page:
            logger.error("✗ Cannot wait for login: page not available")
            return False

        logger.debug(f"⏳ Waiting for login (timeout: {timeout}s)...")
        start_time = time.time()
        check_count = 0
        
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time
            
            if self.is_logged_in():
                logger.debug(f"✓ Login detected after {elapsed:.1f}s ({check_count} checks)")
                return True
            
            # Reduced from 2s to 1s for faster detection
            if check_count % 5 == 0:  # Log every 5 checks
                logger.debug(f"⏳ Still waiting... ({elapsed:.1f}s elapsed, {check_count} checks)")
            time.sleep(0.5)  # OPTIMIZED: Reduced from 1s to 0.5s
        
        elapsed = time.time() - start_time
        logger.warning(f"✗ Login timeout after {elapsed:.1f}s ({check_count} checks)")
        return False

    def get_cookies(self) -> Dict[str, str]:
        """Extract cookies from browser context using CDP"""
        if not self.context or not self.page:
            return {}
        
        cookie_dict = {}
        
        # Use CDP method (most reliable)
        try:
            cdp_session = self.context.new_cdp_session(self.page)
            cookies_response = cdp_session.send(
                "Network.getCookies",
                {"urls": ["https://grok.com", "https://www.grok.com", "https://x.ai", "https://accounts.x.ai"]},
            )
            
            if "cookies" in cookies_response:
                for cookie in cookies_response["cookies"]:
                    cookie_dict[cookie["name"]] = cookie["value"]
            
            if cookie_dict:
                logger.debug(f"Extracted {len(cookie_dict)} cookies via CDP")
                return cookie_dict
        except Exception as e:
            logger.debug(f"CDP extraction failed: {e}")
        
        return cookie_dict

    def close_popups(self) -> bool:
        """
        Close any popups, modals, or advertisements that are currently visible.
        
        Returns:
            True if a popup was closed, False otherwise
        """
        if not self.page:
            return False
        
        try:
            logger.debug("Closing popups/advertisements...")
            popup_result = self.page.evaluate(close_popups_js())
            
            if popup_result and popup_result.get('closed'):
                methods = popup_result.get('methods', [])
                logger.info(f"✓ Closed popup using: {', '.join(methods)}")
                return True
            else:
                logger.debug("No popups found to close")
                return False
        except Exception as e:
            logger.debug(f"Error closing popups: {e}")
            return False

    def enable_deepsearch(self) -> bool:
        """
        Enable DeepSearch mode by clicking the DeepSearch button and verifying it's enabled.
        
        Returns:
            True if DeepSearch was enabled and verified, False otherwise
        """
        if not self.page:
            logger.warning("⚠ Cannot enable DeepSearch: page not available")
            return False
        
        try:
            logger.info("🔍 [DeepSearch] Enabling DeepSearch...")
            
            # Find and click the DeepSearch button using JavaScript
            click_result = self.page.evaluate("""
                            () => {
                    const buttons = Array.from(document.querySelectorAll('button[data-slot="button"]'));
                                for (const btn of buttons) {
                                    const text = (btn.innerText || btn.textContent || '').trim();
                                    if (text === 'DeepSearch' || text.toLowerCase() === 'deepsearch') {
                                        const rect = btn.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {
                                    btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                                    btn.click();
                                return { clicked: true };
                            }
                        }
                    }
                    return { clicked: false };
                }
            """)
            
            if not (click_result and click_result.get('clicked')):
                logger.warning("[DeepSearch] ✗ Could not find or click DeepSearch button")
                return False
            
            logger.info("[DeepSearch] ✓ Clicked button")
            
            # Wait briefly for UI to update
            time.sleep(0.3)  # Trimmed from 0.5s
            
            # Verify DeepSearch is enabled
            verification_result = self.page.evaluate(verify_deepsearch_enabled_js())
            
            if verification_result and verification_result.get('enabled'):
                logger.info("[DeepSearch] ✓ DeepSearch enabled and verified")
                return True
            else:
                logger.warning("[DeepSearch] ⚠ Button clicked but DeepSearch not verified")
                return False
                
        except Exception as e:
            logger.error(f"[DeepSearch] ✗ Error enabling DeepSearch: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(f"[DeepSearch] Traceback: {traceback.format_exc()}")
            return False

    def set_model(self, model: str) -> bool:
        """
        Set the model via UI before sending message
        
        Args:
            model: Model name (auto, fast, expert, grok-4-fast, heavy, grok-4.1, grok-4.1-think, grok-4-1, grok-4-1-think)
        
        Returns:
            True if model was set, False otherwise
        """
        if not self.page:
            return False
        
        model_lower = model.lower().strip()
        logger.debug(f"set_model called with: '{model}' (normalized: '{model_lower}')")
        
        # Handle Grok 4.1 models using the new select_grok_model method
        if model_lower in ['grok-4.1', 'grok-4-1']:
            logger.info(f"🔧 Detected Grok 4.1 model, using select_grok_model()")
            result = self.select_grok_model("Grok 4.1")
            if result:
                logger.info(f"✓ Grok 4.1 selected successfully")
            else:
                logger.warning(f"✗ Failed to select Grok 4.1")
            return result
        elif model_lower in ['grok-4.1-think', 'grok-4-1-think', 'grok-4.1-thinking', 'grok-4-1-thinking']:
            logger.info(f"🔧 Detected Grok 4.1 Thinking model, using select_grok_model()")
            result = self.select_grok_model("Grok 4.1 Thinking")
            if result:
                logger.info(f"✓ Grok 4.1 Thinking selected successfully")
            else:
                logger.warning(f"✗ Failed to select Grok 4.1 Thinking")
            return result
        
        # Map model names to actual menu item text (from HTML structure)
        model_text_map = {
            'auto': 'Auto Chooses Fast or Expert',
            'fast': 'Fast Quick responses',
            'expert': 'Expert Thinks hard',
            'grok-4-fast': 'Grok 4 Fast Beta',
            'heavy': 'Heavy Team of experts'
        }
        
        target_text = model_text_map.get(model_lower)
        if not target_text:
            logger.warning(f"Unknown model: {model}")
            return False
        
        try:
            model_set_start = time.time()
            logger.debug(f"🔧 Setting model to: {model}...")
            
            # Click model selector button using JavaScript
            button_click_start = time.time()
            result = self.page.evaluate("""
                () => {
                    const buttons = document.querySelectorAll('#model-select-trigger, button[aria-label="Model select"]');
                    if (buttons.length > 0) {
                        const button = buttons[0];
                        button.focus();
                        button.click();
                        return { clicked: true };
                    }
                    return { clicked: false };
                }
            """)
            
            if not result.get('clicked'):
                logger.warning("Could not find/click model selector button")
                return False
            
            logger.debug(f"Button click took {time.time() - button_click_start:.2f}s")
            
            # Step 2: Wait for menu to appear - check in document body and any portals
            menu_wait_start = time.time()
            menu_visible = False
            for i in range(8):  # Reduced from 15 to 8 (max 0.8s instead of 3s)
                menu_visible = self.page.evaluate("""
                    () => {
                        // Check for menu in main document
                        let menu = document.querySelector('[role="menu"]');
                        if (menu) {
                            const rect = menu.getBoundingClientRect();
                            const style = window.getComputedStyle(menu);
                            if (rect.width > 0 && rect.height > 0 && 
                                menu.offsetParent !== null &&
                                style.display !== 'none' &&
                                style.visibility !== 'hidden') {
                                return true;
                            }
                        }
                        
                        // Also check in any portals/overlays (Radix UI often uses portals)
                        const portals = document.querySelectorAll('[data-radix-portal], [data-radix-menu-content]');
                        for (const portal of portals) {
                            const menuInPortal = portal.querySelector('[role="menu"]');
                            if (menuInPortal) {
                                const rect = menuInPortal.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    return true;
                                }
                            }
                        }
                        
                        return false;
                    }
                """)
                if menu_visible:
                    menu_wait_time = time.time() - menu_wait_start
                    logger.debug(f"Menu appeared after {menu_wait_time:.2f}s")
                    break
                time.sleep(0.1)  # Reduced from 0.2s to 0.1s
            
            if not menu_visible:
                logger.warning("Menu did not appear after clicking model selector")
                return False
            
            # Minimal wait for menu items to render
            time.sleep(0.1)  # Reduced from 0.2s
            
            # Step 4: Find and click the target menu item using JavaScript (faster than Playwright)
            click_start = time.time()
            model_clicked = self.page.evaluate(f"""
                () => {{
                    // Find all menu items
                    const items = Array.from(document.querySelectorAll('[role="menuitem"]'));
                    
                    // Look for the item with exact matching text
                    let targetItem = null;
                    for (const item of items) {{
                        const text = (item.innerText || item.textContent || '').trim();
                        // Match exact text only
                        if (text === '{target_text}') {{
                            targetItem = item;
                            break;
                        }}
                    }}
                    
                    if (targetItem) {{
                        targetItem.scrollIntoView({{ behavior: 'instant', block: 'center' }});
                        targetItem.click();
                        return true;
                    }}
                    return false;
                }}
            """)
            
            if not model_clicked:
                logger.warning(f"Could not find/click model option: {target_text}")
                return False
            
            click_time = time.time() - click_start
            logger.debug(f"✓ Clicked model option: {target_text} (took {click_time:.2f}s)")
            model_set_time = time.time() - model_set_start
            logger.debug(f"Total model selection took {model_set_time:.2f}s")
            return True
                
        except Exception as e:
            model_set_time = time.time() - model_set_start if 'model_set_start' in locals() else 0
            logger.warning(f"Error setting model: {e} (took {model_set_time:.2f}s)")
            import traceback
            logger.debug(traceback.format_exc())
            return False

    def select_grok_model(self, target_model_name: str = "Grok 4.1 Thinking") -> bool:
        """
        Selects a model from the Grok dropdown.
        
        Args:
            target_model_name: "Grok 4.1" or "Grok 4.1 Thinking"
        
        Returns:
            True if model was selected successfully, False otherwise
        """
        if not self.page:
            logger.warning("⚠ Cannot select model: page not available")
            return False
        
        try:
            logger.info(f"🔧 Selecting Grok model: {target_model_name}...")
            
            # Ensure page is ready (wait for DOM to be stable)
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=1000)  # OPTIMIZED: Reduced from 2000ms
            except Exception:
                pass  # Page might already be loaded
            
            # OPTIMIZED: Removed wait - DOM is already ready after wait_for_load_state
            
            # 1. Open the Main Menu
            # There can be multiple elements with the same ID, so use .first to handle strict mode
            logger.debug("Looking for model selector button (#model-select-trigger)...")
            
            # Use .first to handle multiple elements with same ID (strict mode violation)
            trigger_btn = self.page.locator('#model-select-trigger').first
            
            # Wait for button to exist first (it might be hidden initially)
            trigger_btn.wait_for(state="attached", timeout=1500)
            logger.debug("✓ Model selector button found in DOM")
            
            # Try to wait for visibility, but if it's hidden, use JavaScript click
            try:
                trigger_btn.wait_for(state="visible", timeout=1000)  # OPTIMIZED: Reduced from 2000ms
                logger.debug("✓ Model selector button is visible")
                trigger_btn.scroll_into_view_if_needed()
                trigger_btn.click()
            except Exception:
                # Button exists but is hidden - use JavaScript to click it
                logger.debug("Button is hidden, using JavaScript click with visibility manipulation")
                trigger_btn.evaluate("""
                    (element) => {
                        // Try to make element visible
                        const originalStyle = element.style.cssText;
                        element.style.display = 'block';
                        element.style.visibility = 'visible';
                        element.style.opacity = '1';
                        
                        // Scroll into view
                        element.scrollIntoView({ behavior: 'instant', block: 'center' });
                        
                        // Click using multiple methods
                        element.click();
                        element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        element.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, cancelable: true, pointerId: 1 }));
                        element.dispatchEvent(new PointerEvent('pointerup', { bubbles: true, cancelable: true, pointerId: 1 }));
                        
                        // Restore original style
                        element.style.cssText = originalStyle;
                    }
                """)
            logger.debug("✓ Clicked main menu trigger")
            
            # OPTIMIZED: Removed wait - wait_for() below ensures menu is ready
            # No need for time.sleep since wait_for() already waits for visibility
            
            # 2. Hover over "Models"
            # We strictly look for a 'menuitem' that contains the text "Models".
            # This filters out headers or other labels.
            models_menu_item = self.page.get_by_role("menuitem").filter(has_text="Models").first
            
            # Wait for it to be visible (menu animation) - OPTIMIZED: Reduced from 1500ms to 1000ms
            models_menu_item.wait_for(state="visible", timeout=1000)
            
            # CRITICAL: In headless mode, hover often doesn't work reliably.
            # Use click instead of hover for better headless compatibility.
            if self.headless:
                logger.debug("Headless mode: Using click instead of hover for Models menu")
                models_menu_item.click()
                # In headless mode, submenu may take longer to appear after click
                time.sleep(0.3)  # Wait for submenu to appear after click
            else:
                # In headed mode, hover works better for Radix UI submenus
                models_menu_item.hover()
                logger.debug("Hovered over 'Models' item")
                # OPTIMIZED: Reduced wait - submenu appears quickly after hover
                time.sleep(0.05)  # Minimal wait for submenu animation
            
            # 3. Select the Target Model from submenu
            # Wait for submenu to appear
            self.page.wait_for_selector('menu, [role="menu"]', state="attached", timeout=2000)
            if self.headless:
                time.sleep(0.2)
            
            # Find submenu (second menu after main menu)
            all_menus = self.page.locator('menu, [role="menu"]').all()
            if len(all_menus) < 2:
                logger.error("Submenu not found")
                return False
            
            submenu = all_menus[1]
            logger.debug(f"Found submenu (menu {len(all_menus)} total)")
            
            # Select exact model from submenu
            if target_model_name == "Grok 4.1":
                # Find "Grok 4.1" that's NOT "Grok 4.1 Thinking"
                all_submenu_items = submenu.get_by_role("menuitem").all()
                for item in all_submenu_items:
                    item_text = item.inner_text().lower()
                    if "grok 4.1" in item_text and "thinking" not in item_text:
                        target_option = item
                        break
                else:
                    logger.error("Grok 4.1 option not found in submenu")
                    return False
            else:
                # For "Grok 4.1 Thinking", use exact text match
                target_option = submenu.get_by_role("menuitem").filter(
                    has_text=target_model_name
                ).first
            
            # Wait for the submenu animation to finish and element to be clickable - OPTIMIZED: Reduced from 1500ms to 1000ms
            target_option.wait_for(state="visible", timeout=1000)
            
            target_option.click()
            logger.info(f"✓ Clicked model option: {target_model_name}")
            
            # Wait for UI update
            time.sleep(0.1)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to select model: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
            return False
    
    def verify_model_selection(self, model: str) -> bool:
        """
        Verify that the specified model is currently selected in the UI
        
        Args:
            model: Model name (e.g., "grok-4.1", "expert")
        
        Returns:
            True if the model is selected, False otherwise
        """
        if not self.page:
            return False
        
        try:
            model_lower = model.lower().strip()
            
            # Get current model from UI
            current_model = self.page.locator('#model-select-trigger').first.inner_text()
            logger.debug(f"Verifying model selection: expected '{model}', UI shows '{current_model}'")
            
            # Map model names to what they should show in UI
            if model_lower in ['grok-4.1', 'grok-4-1']:
                # Grok 4.1 should show "Grok 4.1" in the button
                return "grok 4.1" in current_model.lower() and "expert" not in current_model.lower()
            elif model_lower in ['grok-4.1-think', 'grok-4-1-think', 'grok-4.1-thinking', 'grok-4-1-thinking']:
                # Grok 4.1 Thinking should show "Grok 4.1 Thinking"
                return "grok 4.1 thinking" in current_model.lower()
            elif model_lower == 'expert':
                # Expert should show "Expert" but not "Grok 4.1"
                return "expert" in current_model.lower() and "grok 4.1" not in current_model.lower()
            elif model_lower == 'fast':
                return "fast" in current_model.lower()
            elif model_lower == 'auto':
                return "auto" in current_model.lower()
            else:
                # For other models, use simple substring match
                return model_lower in current_model.lower()
        except Exception as e:
            logger.debug(f"Could not verify model selection: {e}")
            return False

    def set_private_mode(self, enable: bool = True) -> bool:
        """
        Enable or disable Private chat mode by clicking the Private button.
        
        Args:
            enable: True to enable private mode, False to disable
        
        Returns:
            True if private mode was set successfully, False otherwise
        """
        if not self.page:
            logger.warning("⚠ Cannot set private mode: page not available")
            return False
        
        try:
            logger.info(f"🔒 [Private] {'Enabling' if enable else 'Disabling'} Private mode...")
            private_start = time.time()
            
            # Step 1: Find the Private button
            logger.debug("[Private] Looking for Private button...")
            button_info = self.page.evaluate(find_private_button_js())
            
            if not button_info or not button_info.get('found'):
                logger.warning("[Private] ✗ Private button not found")
                return False
            
            current_private = button_info.get('isPrivate', False)
            logger.debug(f"[Private] Current state: {'Private' if current_private else 'Default'}")
            
            # Step 2: Check if we need to toggle
            if (enable and current_private) or (not enable and not current_private):
                logger.info(f"[Private] ✓ Already in {'Private' if enable else 'Default'} mode")
                return True
            
            # Click the button to toggle using JavaScript
            logger.debug("[Private] Clicking Private button to toggle...")
            click_result = self.page.evaluate("""
                () => {
                    const selectors = [
                        'a[aria-label*="Switch to Private Chat" i]',
                        'a[aria-label*="Switch to Default Chat" i]',
                        'button[aria-label*="Switch to Private Chat" i]',
                        'button[aria-label*="Switch to Default Chat" i]',
                        'a[href*="#private"]',
                    ];
                    
                    for (const selector of selectors) {
                        const elements = Array.from(document.querySelectorAll(selector));
                        for (const el of elements) {
                            const text = (el.innerText || el.textContent || '').trim();
                            if (text === 'Private' || text.toLowerCase() === 'private') {
                                const rect = el.getBoundingClientRect();
                                if (rect.width > 0 && rect.height > 0) {
                                    el.scrollIntoView({ behavior: 'instant', block: 'center' });
                                    el.click();
                                    return { clicked: true };
                                }
                            }
                        }
                    }
                    return { clicked: false };
                }
            """)
            
            if not (click_result and click_result.get('clicked')):
                logger.warning("[Private] ✗ Could not click Private button")
                return False
            
            logger.info("[Private] ✓ Clicked button")
            
            # Step 4: Wait for UI to update
            time.sleep(0.3)  # OPTIMIZED: Reduced from 0.5s to 0.3s
            
            # Step 5: Verify the state changed
            verification = self.page.evaluate(verify_private_mode_js())
            if verification and verification.get('found'):
                is_private = verification.get('isPrivate', False)
                if (enable and is_private) or (not enable and not is_private):
                    private_time = time.time() - private_start
                    logger.info(f"[Private] ✓ Private mode {'enabled' if enable else 'disabled'} successfully (took {private_time:.2f}s)")
                    return True
                else:
                    logger.warning(f"[Private] ⚠ State verification failed - expected {'Private' if enable else 'Default'}, got {'Private' if is_private else 'Default'}")
                    # Retry verification after a bit more wait
                    time.sleep(0.3)  # Trimmed from 0.5s
                    verification = self.page.evaluate(verify_private_mode_js())
                    if verification:
                        is_private = verification.get('isPrivate', False)
                        if (enable and is_private) or (not enable and not is_private):
                            logger.info("[Private] ✓ Private mode set (verified on retry)")
                            return True
                    return False
            else:
                logger.warning("[Private] ⚠ Could not verify private mode state")
                return False
                
        except Exception as e:
            logger.error(f"[Private] ✗ Error setting private mode: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(f"[Private] Traceback: {traceback.format_exc()}")
            return False

    def enter_message(self, message: str) -> bool:
        """
        Enter a message into the chat input without sending it.
        
        Args:
            message: Message to enter into the input field
        
        Returns:
            True if message was entered successfully, False otherwise
        """
        if not self.page:
            logger.warning("⚠ Cannot enter message: page not available")
            return False
        
        try:
            logger.debug("🔍 Looking for chat input...")
            
            # Find chat input - simplified, no unnecessary waits
            chat_input = self.page.query_selector('textarea[aria-label*="Ask Grok"], textarea[aria-label*="Ask"], input[aria-label*="Ask Grok"]')
            
            if not chat_input:
                chat_input = self.page.query_selector('textarea')
            
            if not chat_input:
                chat_input = self.page.query_selector('[contenteditable="true"]')
            
            if not chat_input:
                logger.warning("⚠ Could not find chat input")
                return False
            
            # Clear and fill message
            try:
                if hasattr(chat_input, 'clear'):
                    chat_input.clear()  # type: ignore
            except Exception:
                pass
            
            chat_input.fill(message)
            logger.debug("✓ Message entered into chat input")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error entering message: {e}")
            if self.debug_mode:
                import traceback
                logger.debug(f"Traceback: {traceback.format_exc()}")
            return False

    def send_message(
        self,
        message: Optional[str] = None,
        wait_for_response: bool = True,
        timeout: int = 120000
    ) -> Optional[str]:
        """
        Submit the message that's already in the chat input and wait for response.
        Assumes message has already been entered via enter_message().
        
        Args:
            message: Optional message to enter (if not already entered). If None, assumes message is already in input.
            wait_for_response: Whether to wait for response
            timeout: Timeout in milliseconds
        
        Returns:
            Response text or None
        """
        if not self.page:
            raise Exception("Browser not started")

        # Find chat input - simplified
        chat_input = self.page.query_selector('textarea[aria-label*="Ask Grok"], textarea[aria-label*="Ask"], input[aria-label*="Ask Grok"]')
        
        if not chat_input:
            chat_input = self.page.query_selector('textarea')
        
        if not chat_input:
            chat_input = self.page.query_selector('[contenteditable="true"]')
            
        if not chat_input:
            raise Exception("Could not find chat input. Make sure you're logged in and on the chat page.")

        # If message provided, enter it (for backward compatibility)
        if message:
            try:
                if hasattr(chat_input, 'clear'):
                    chat_input.clear()  # type: ignore
            except Exception:
                pass
            chat_input.fill(message)

        # Submit message - press Enter
        logger.debug("🔘 Submitting message...")
        try:
            chat_input.press("Enter")
            logger.debug("✓ Submitted via Enter key")
        except Exception as e:
            logger.warning(f"Could not submit message: {e}")
            return None

        if not wait_for_response:
            return None

        # Wait for response
        return self._wait_for_response(timeout, user_message=message or "")

    def _wait_for_response(self, timeout: int = 120000, user_message: str = "") -> Optional[str]:
        """
        Wait for chat response using the stop generation button as indicator.
        The button appears when generation starts and disappears when complete.
        """
        if not self.page:
            return None

        start_time = time.time()
        timeout_seconds = timeout / 1000
        
        # Button selector - this is the stop generation button that appears during response generation
        # Using class list matching since CSS selectors with spaces need special handling
        logger.debug("🔍 Waiting for response generation to complete...")
        
        try:
            # Step 1: Wait for the button to appear (generation started)
            button_appear_start = time.time()
            logger.debug("Waiting for generation button to appear...")
            button_appeared = False
            for i in range(int(timeout_seconds * 2)):  # Check every 0.5s
                if time.time() - start_time > timeout_seconds:
                    break
                    
                button_exists = self.page.evaluate("""
                    () => {
                        // Look for the stop generation button by matching its classes
                        const buttons = document.querySelectorAll('div');
                        for (const btn of buttons) {
                            const classList = btn.classList;
                            if (classList.contains('h-10') && 
                                classList.contains('aspect-square') && 
                                classList.contains('flex') && 
                                classList.contains('flex-col') && 
                                classList.contains('items-center') && 
                                classList.contains('justify-center') && 
                                classList.contains('rounded-full') && 
                                classList.contains('ring-1') && 
                                classList.contains('ring-inset') && 
                                classList.contains('bg-button-filled') && 
                                classList.contains('text-fg-invert')) {
                                // Check if it's visible
                                const rect = btn.getBoundingClientRect();
                                const style = window.getComputedStyle(btn);
                                if (rect.width > 0 && rect.height > 0 && 
                                    btn.offsetParent !== null &&
                                    style.display !== 'none' &&
                                    style.visibility !== 'hidden') {
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                """)
                
                if button_exists:
                    button_appeared = True
                    button_appear_time = time.time() - button_appear_start
                    logger.debug(f"Generation button appeared - response is being generated (took {button_appear_time:.2f}s)")
                    break
                    
                time.sleep(0.2)  # OPTIMIZED: Reduced from 0.3s to 0.2s for faster polling
            
            if not button_appeared:
                button_appear_time = time.time() - button_appear_start
                logger.warning(f"Generation button never appeared - response may have completed immediately (checked for {button_appear_time:.2f}s)")
            
            # Step 2: Wait for the button to disappear (generation complete)
            button_disappear_start = time.time()
            logger.debug("Waiting for generation button to disappear...")
            button_disappeared = False
            
            for i in range(int(timeout_seconds * 2)):  # Check every 0.5s
                if time.time() - start_time > timeout_seconds:
                    logger.warning("Timeout waiting for generation to complete")
                    break
                
                button_exists = self.page.evaluate("""
                    () => {
                        // Look for the stop generation button by matching its classes
                        const buttons = document.querySelectorAll('div');
                        for (const btn of buttons) {
                            const classList = btn.classList;
                            if (classList.contains('h-10') && 
                                classList.contains('aspect-square') && 
                                classList.contains('flex') && 
                                classList.contains('flex-col') && 
                                classList.contains('items-center') && 
                                classList.contains('justify-center') && 
                                classList.contains('rounded-full') && 
                                classList.contains('ring-1') && 
                                classList.contains('ring-inset') && 
                                classList.contains('bg-button-filled') && 
                                classList.contains('text-fg-invert')) {
                                // Check if it's visible
                                const rect = btn.getBoundingClientRect();
                                const style = window.getComputedStyle(btn);
                                if (rect.width > 0 && rect.height > 0 && 
                                    btn.offsetParent !== null &&
                                    style.display !== 'none' &&
                                    style.visibility !== 'hidden') {
                                    return true;
                                }
                            }
                        }
                        return false;
                    }
                """)
                
                if not button_exists:
                    button_disappeared = True
                    button_disappear_time = time.time() - button_disappear_start
                    logger.debug(f"Generation button disappeared - response complete (took {button_disappear_time:.2f}s)")
                    break
                    
                time.sleep(0.2)  # OPTIMIZED: Reduced from 0.3s to 0.2s for faster polling
            
            if not button_disappeared and button_appeared:
                logger.warning("Generation button still visible - may still be generating")
            
            # Step 3: OPTIMIZED: Minimal wait for DOM to settle after button disappears
            # Reduced from 0.5s to 0.2s - response should be ready immediately after button disappears
            time.sleep(0.2)
            
            # Step 4: Extract response immediately (target: <0.5s)
            extract_start = time.time()
            response_text = self.page.evaluate("""
                () => {
                    // Find the main chat container first
                    const main = document.querySelector('main');
                    if (!main) return '';
                    
                    // Look for markdown/prose content (Grok responses are usually in markdown)
                    const markdownContainers = main.querySelectorAll('div[class*="markdown"], pre[class*="markdown"], [class*="prose"]');
                    let bestText = '';
                    
                    for (const md of markdownContainers) {
                        const isInInput = md.closest('form, textarea, [contenteditable="true"]');
                        if (isInInput) continue;
                        
                        const text = (md.innerText || md.textContent || '').trim();
                        if (text.length > 50 && !text.includes('What do you want to know?') && text.length > bestText.length) {
                            bestText = text;
                        }
                    }
                    
                    if (bestText) return bestText;
                    
                    // Fallback: Look for article/role containers
                    const articles = main.querySelectorAll('[role="article"], article');
                    const uiTexts = ['Private', 'Auto', 'DeepSearch', 'Create Image', 'Pick Personas', 'Voice', 'What do you want to know?'];
                    
                    for (const article of articles) {
                        const isInInput = article.closest('form, textarea');
                        if (isInInput) continue;
                        
                        const text = (article.innerText || article.textContent || '').trim();
                        const isUIText = uiTexts.some(ui => text.includes(ui));
                        if (text.length > 50 && !isUIText && text.length > bestText.length) {
                            bestText = text;
                        }
                    }
                    
                    return bestText;
                }
            """)
            
            extract_time = time.time() - extract_start
            if extract_time > 0.5:
                logger.warning(f"Response extraction took {extract_time:.2f}s (target: <0.5s)")
            
            # Filter out user's message
            if response_text:
                response_text_clean = response_text.strip()
                user_msg_clean = user_message.strip() if user_message else ""
                
                # If the extracted text is very similar to the message we sent, it's probably not the response
                if response_text_clean and response_text_clean != user_msg_clean:
                    # Additional check: if it starts with the user message, it might be the user message
                    if not response_text_clean.startswith(user_msg_clean[:50]) or len(response_text_clean) > len(user_msg_clean) * 1.5:
                        result = response_text_clean
                    else:
                        logger.debug("Skipping - looks like user message")
                        result = None
                else:
                    logger.debug("Skipping - extracted text matches user message")
                    result = None
            else:
                result = None
            
            elapsed = time.time() - start_time
            if result:
                logger.debug(f"✓ Response extracted ({len(result)} chars, took {elapsed:.1f}s)")
            else:
                logger.warning(f"✗ No response extracted (took {elapsed:.1f}s)")
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.warning(f"✗ Error waiting for response: {e} (took {elapsed:.1f}s)")
            return None

    def close(self) -> None:
        """Close browser and cleanup with proper error handling for headless mode"""
        errors = []
        
        # Check if resources are already closed before attempting to close
        try:
            if self.page and not self.page.is_closed():
                try:
                    self.page.close()
                except Exception as e:
                    error_msg = str(e)
                    # Ignore "Event loop is closed" errors - resource is already closed (common in headless mode)
                    if "Event loop is closed" not in error_msg and "already stopped" not in error_msg.lower():
                        errors.append(f"page: {e}")
                        if self.debug_mode:  # Only log in debug mode
                            logger.warning(f"Error closing page: {e}")
        except Exception as e:
            # Page might not have is_closed() method or already closed
            pass
        
        try:
            if self.context:
                # Check if context is still valid before closing
                try:
                    # Try to access context to see if it's still valid
                    _ = self.context.pages
                    self.context.close()
                except Exception as e:
                    error_msg = str(e)
                    # Ignore "Event loop is closed" errors - resource is already closed (common in headless mode)
                    if "Event loop is closed" not in error_msg and "already stopped" not in error_msg.lower():
                        errors.append(f"context: {e}")
                        if self.debug_mode:  # Only log in debug mode
                            logger.warning(f"Error closing context: {e}")
        except Exception as e:
            # Context might already be closed
            pass
        
        try:
            if self.browser:
                # Check if browser is still connected before closing
                try:
                    # Try to access browser to see if it's still valid
                    _ = self.browser.contexts
                    self.browser.close()
                except Exception as e:
                    error_msg = str(e)
                    # Ignore "Event loop is closed" errors - resource is already closed (common in headless mode)
                    if "Event loop is closed" not in error_msg and "already stopped" not in error_msg.lower():
                        errors.append(f"browser: {e}")
                        if self.debug_mode:  # Only log in debug mode
                            logger.warning(f"Error closing browser: {e}")
        except Exception as e:
            # Browser might already be closed
            pass
        
        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            error_msg = str(e)
            # Ignore "Event loop is closed" errors - Playwright is already stopped (common in headless mode)
            if "Event loop is closed" not in error_msg and "already stopped" not in error_msg.lower():
                errors.append(f"playwright: {e}")
                if self.debug_mode:  # Only log in debug mode
                    logger.warning(f"Error stopping playwright: {e}")
        
        # Only log errors in debug mode, and suppress "Event loop is closed" warnings
        if errors and self.debug_mode:
            filtered_errors = [e for e in errors if "Event loop is closed" not in str(e) and "already stopped" not in str(e).lower()]
            if filtered_errors:
                logger.debug(f"Cleanup completed with {len(filtered_errors)} error(s): {', '.join(filtered_errors)}")

    def interactive_mode(self) -> None:
        """Keep browser open for interactive use"""
        if not self.page:
            return
        
        logger.info("Browser open for interactive use. Press Ctrl+C to close.")
        try:
            while True:
                time.sleep(0.3)  # OPTIMIZED: Reduced from 0.5s to 0.3s
        except KeyboardInterrupt:
            logger.info("Closing browser...")
            self.close()
