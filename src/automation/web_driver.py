"""
Perplexity AI Wrapper - Web Automation Driver
File: src/automation/web_driver.py
"""
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, ElementHandle
from playwright.async_api import async_playwright
import json
import time
from typing import Optional, Dict, List, Callable
from pathlib import Path


class PerplexityWebDriver:
    """
    Browser automation for Perplexity using Playwright
    """
    
    def __init__(
        self,
        headless: bool = False,
        user_data_dir: Optional[str] = None,
        stealth_mode: bool = True
    ):
        """
        Initialize web driver
        
        Args:
            headless: Run browser in headless mode
            user_data_dir: Chrome user data directory
            stealth_mode: Enable stealth features
        """
        self.headless = headless
        self.user_data_dir = user_data_dir
        self.stealth_mode = stealth_mode
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.debug_network = False
        self.network_requests = []
    
    def start(self, port: Optional[int] = None, debug_network: bool = False) -> None:
        """
        Start browser session
        
        Args:
            port: Remote debugging port (connects to existing Chrome)
            debug_network: Enable network request/response logging for debugging
        """
        self.playwright = sync_playwright().start()
        self.debug_network = debug_network
        self.network_requests = []  # Store network requests for debugging
        
        if port:
            # Connect to existing Chrome instance
            self.browser = self.playwright.chromium.connect_over_cdp(
                f"http://localhost:{port}"
            )
            self.context = self.browser.contexts[0] if self.browser.contexts else self.browser.new_context()
        else:
            # Launch new browser
            # REMOVED --disable-web-security as it triggers "unsafe browser" warnings
            launch_options = {
                'headless': self.headless,
                'args': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--no-default-browser-check'
                ]
            }
            
            if self.user_data_dir:
                # Use launch_persistent_context for persistent sessions
                # IMPORTANT: Remove --disable-web-security as it triggers security warnings
                persistent_args = [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--no-first-run',
                    '--no-default-browser-check',
                    '--disable-setuid-sandbox'
                ]
                self.browser = self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    args=persistent_args,
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/New_York',
                    ignore_https_errors=False
                )
                # Persistent context already creates a context, so we get it
                self.context = self.browser  # launch_persistent_context returns BrowserContext
            else:
                # Regular launch for non-persistent sessions
                self.browser = self.playwright.chromium.launch(**launch_options)
            
            if not self.user_data_dir:
                # Create context for regular launch
                self.context = self.browser.new_context(
                    viewport={'width': 1280, 'height': 720},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
        
        # Get page from context (persistent context already has one, or create new)
        if self.user_data_dir:
            # Persistent context - get existing pages or create new
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = self.context.new_page()
        else:
            # Regular context - create new page
            self.page = self.context.new_page() if self.context else self.browser.new_page()
        
        # Set up network monitoring if enabled
        if debug_network:
            self._setup_network_monitoring()
        
        # Apply stealth mode BEFORE navigating (critical for detection avoidance)
        if self.stealth_mode:
            self._apply_stealth()
        
        print("✓ Browser started")
    
    def _setup_network_monitoring(self) -> None:
        """Set up network request/response monitoring for debugging"""
        if not self.page:
            return
        
        def on_request(request):
            """Log outgoing requests"""
            url = request.url
            if 'perplexity.ai' in url:
                self.network_requests.append({
                    'type': 'request',
                    'url': url,
                    'method': request.method,
                    'timestamp': time.time()
                })
                if self.debug_network:
                    print(f"  [NETWORK] → {request.method} {url[:80]}...", flush=True)
        
        def on_response(response):
            """Log incoming responses"""
            url = response.url
            if 'perplexity.ai' in url:
                status = response.status
                self.network_requests.append({
                    'type': 'response',
                    'url': url,
                    'status': status,
                    'timestamp': time.time()
                })
                if self.debug_network:
                    print(f"  [NETWORK] ← {status} {url[:80]}...", flush=True)
        
        self.page.on("request", on_request)
        self.page.on("response", on_response)
    
    def _apply_stealth(self) -> None:
        """Apply stealth techniques to avoid detection"""
        if not self.page:
            return
        
        # Enhanced stealth script to avoid detection
        self.page.add_init_script("""
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Chrome runtime (important for detection)
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override getBattery
            if (navigator.getBattery) {
                navigator.getBattery = () => Promise.resolve({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                });
            }
            
            // Override webdriver in navigator
            delete navigator.__proto__.webdriver;
            
            // Canvas fingerprinting protection
            const getImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function() {
                const imageData = getImageData.apply(this, arguments);
                for (let i = 0; i < imageData.data.length; i += 4) {
                    imageData.data[i] += Math.floor(Math.random() * 10) - 5;
                }
                return imageData;
            };
        """)
    
    def set_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Set cookies in browser context
        
        Args:
            cookies: Dictionary of cookie name-value pairs
        """
        if not self.context:
            raise Exception("Browser context not initialized")
        
        # Navigate to the domain first (required for Playwright)
        if not self.page:
            self.page = self.context.new_page()
        
        # Navigate to domain to set cookies
        self.page.goto("https://www.perplexity.ai", wait_until="domcontentloaded")
        
        # Convert to Playwright cookie format
        # Playwright requires 'url' OR both 'domain' and 'path'
        playwright_cookies = []
        for name, value in cookies.items():
            # Skip invalid cookies
            if not name or not isinstance(value, str):
                continue
            
            # Playwright has cookie size limits (4096 bytes)
            if len(str(value)) > 4000:
                print(f"⚠ Skipping cookie '{name}' - value too long")
                continue
            
            try:
                cookie_obj = {
                    'name': str(name),
                    'value': str(value),
                    'url': 'https://www.perplexity.ai',  # Use url instead of domain+path
                }
                playwright_cookies.append(cookie_obj)
            except Exception as e:
                print(f"⚠ Skipping cookie '{name}' - {e}")
                continue
        
        if playwright_cookies:
            try:
                self.context.add_cookies(playwright_cookies)
                print(f"✓ Set {len(playwright_cookies)} cookies")
            except Exception as e:
                print(f"⚠ Error setting cookies: {e}")
                print("  Some cookies may be invalid or expired")
                # Try setting cookies one by one
                success_count = 0
                for cookie in playwright_cookies:
                    try:
                        self.context.add_cookies([cookie])
                        success_count += 1
                    except:
                        pass
                print(f"✓ Set {success_count}/{len(playwright_cookies)} cookies")
    
    def navigate_to_perplexity(self) -> None:
        """Navigate to Perplexity homepage"""
        if not self.page:
            raise Exception("Browser not started")
        
        print("Navigating to Perplexity...")
        # Use domcontentloaded for faster initial load, then wait for search input
        self.page.goto(
            "https://www.perplexity.ai", 
            wait_until="domcontentloaded",
            timeout=30000
        )
        # Wait for search input to be ready (more efficient than fixed sleep)
        try:
            self.page.wait_for_selector('[contenteditable="true"], textarea', timeout=5000, state="visible")
        except:
            pass  # Continue even if not found immediately
        print("✓ Loaded Perplexity")
    
    def search(
        self,
        query: str,
        wait_for_response: bool = True,
        timeout: int = 60000
    ) -> str:
        """
        Execute search via UI
        
        Args:
            query: Search query
            wait_for_response: Wait for AI response
            timeout: Timeout in milliseconds
        
        Returns:
            Response text
        """
        if not self.page:
            raise Exception("Browser not started")
        
        print(f"Searching: {query}", flush=True)
        
        # Ensure page is interactive (minimal wait)
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=2000)
        except:
            pass
        
        # Use JavaScript to find the search input more reliably
        # This handles both textarea and contenteditable div cases
        print("  Using JavaScript to find search input...", flush=True)
        search_box = None
        last_error = None
        
        try:
            # JavaScript function to find search input
            # Handles both textarea and contenteditable div elements
            search_element_info = self.page.evaluate("""
                () => {
                    // Function to check if element is visible
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        return style.display !== 'none' && 
                               style.visibility !== 'hidden' && 
                               style.opacity !== '0' &&
                               el.offsetWidth > 0 && 
                               el.offsetHeight > 0;
                    };
                    
                    // Try textareas first
                    const textareas = Array.from(document.querySelectorAll('textarea'));
                    for (const textarea of textareas) {
                        if (isVisible(textarea)) {
                            const placeholder = textarea.getAttribute('placeholder') || '';
                            const text = textarea.textContent || '';
                            if (placeholder.toLowerCase().includes('ask') || 
                                placeholder.toLowerCase().includes('anything') ||
                                text.toLowerCase().includes('ask anything')) {
                                return {
                                    type: 'textarea',
                                    tag: 'textarea',
                                    placeholder: placeholder,
                                    className: textarea.className,
                                    id: textarea.id || '',
                                    selector: 'textarea' + (textarea.id ? '#' + textarea.id : '') + 
                                              (textarea.className ? '.' + textarea.className.split(' ')[0] : '')
                                };
                            }
                        }
                    }
                    
                    // Try contenteditable divs (modern UI)
                    const contenteditables = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                    for (const div of contenteditables) {
                        if (isVisible(div)) {
                            const text = div.textContent || '';
                            const innerHTML = div.innerHTML || '';
                            const placeholder = div.getAttribute('placeholder') || 
                                              div.getAttribute('data-placeholder') || '';
                            
                            // Check if it contains "Ask anything" or similar
                            if (text.toLowerCase().includes('ask anything') ||
                                text.toLowerCase().includes('ask') ||
                                innerHTML.toLowerCase().includes('ask anything') ||
                                placeholder.toLowerCase().includes('ask')) {
                                return {
                                    type: 'contenteditable',
                                    tag: 'div',
                                    placeholder: placeholder,
                                    text: text.substring(0, 100),
                                    className: div.className,
                                    id: div.id || '',
                                    selector: (div.id ? '#' + div.id : '') + 
                                              (div.className ? '.' + div.className.split(' ').filter(c => c).join('.') : '')
                                };
                            }
                        }
                    }
                    
                    // Fallback: any visible textarea or contenteditable
                    for (const textarea of textareas) {
                        if (isVisible(textarea) && !textarea.disabled) {
                            return {
                                type: 'textarea',
                                tag: 'textarea',
                                placeholder: textarea.getAttribute('placeholder') || '',
                                className: textarea.className,
                                id: textarea.id || '',
                                selector: 'textarea'
                            };
                        }
                    }
                    
                    for (const div of contenteditables) {
                        if (isVisible(div)) {
                            return {
                                type: 'contenteditable',
                                tag: 'div',
                                placeholder: div.getAttribute('placeholder') || '',
                                text: div.textContent.substring(0, 100),
                                className: div.className,
                                id: div.id || '',
                                selector: '[contenteditable="true"]'
                            };
                        }
                    }
                    
                    return null;
                }
            """)
            
            if search_element_info:
                print(f"  ✓ Found search element:", flush=True)
                print(f"    Type: {search_element_info.get('type')}", flush=True)
                print(f"    Tag: {search_element_info.get('tag')}", flush=True)
                print(f"    Placeholder: {search_element_info.get('placeholder', '')[:80]}", flush=True)
                print(f"    Selector: {search_element_info.get('selector', '')}", flush=True)
                
                # Now try to get the element using the found selector
                selector = search_element_info.get('selector', '')
                if selector:
                    try:
                        # Try exact selector first
                        search_box = self.page.query_selector(selector)
                        if not search_box or not search_box.is_visible():
                            # Try with more specific selector
                            if search_element_info.get('id'):
                                search_box = self.page.query_selector(f"#{search_element_info['id']}")
                            elif search_element_info.get('className'):
                                classes = search_element_info['className'].split(' ')[:2]  # First 2 classes
                                class_selector = '.' + '.'.join([c for c in classes if c])
                                search_box = self.page.query_selector(class_selector)
                    except:
                        pass
                
                # If still not found, use JavaScript to get element directly via selector
                if not search_box and search_element_info:
                    # Try to construct a better selector from the info we got
                    element_id = search_element_info.get('id')
                    element_classes = search_element_info.get('className', '').split()
                    
                    if element_id:
                        try:
                            search_box = self.page.query_selector(f"#{element_id}")
                        except:
                            pass
                    
                    if not search_box and element_classes:
                        # Try with first few classes
                        for cls in element_classes[:3]:
                            if cls:
                                try:
                                    potential = self.page.query_selector(f".{cls}")
                                    if potential and potential.is_visible():
                                        # Verify it matches our criteria
                                        text = potential.inner_text() or ''
                                        placeholder = potential.get_attribute('placeholder') or ''
                                        if 'ask' in text.lower() or 'ask' in placeholder.lower():
                                            search_box = potential
                                            break
                                except:
                                    continue
                    
                    # Last resort: use evaluate_handle to get element directly
                    if not search_box:
                        try:
                            js_handle = self.page.evaluate_handle("""
                                () => {
                                    const isVisible = (el) => {
                                        if (!el) return false;
                                        const style = window.getComputedStyle(el);
                                        return style.display !== 'none' && 
                                               style.visibility !== 'hidden' && 
                                               el.offsetWidth > 0 && 
                                               el.offsetHeight > 0;
                                    };
                                    
                                    // Find and return the search element
                                    const textareas = Array.from(document.querySelectorAll('textarea'));
                                    for (const textarea of textareas) {
                                        if (isVisible(textarea)) {
                                            const placeholder = textarea.getAttribute('placeholder') || '';
                                            if (placeholder.toLowerCase().includes('ask') || 
                                                placeholder.toLowerCase().includes('anything')) {
                                                return textarea;
                                            }
                                        }
                                    }
                                    
                                    const contenteditables = Array.from(document.querySelectorAll('[contenteditable="true"]'));
                                    for (const div of contenteditables) {
                                        if (isVisible(div)) {
                                            const text = div.textContent || '';
                                            if (text.toLowerCase().includes('ask anything') ||
                                                text.toLowerCase().includes('ask')) {
                                                return div;
                                            }
                                        }
                                    }
                                    
                                    // Fallback
                                    for (const textarea of textareas) {
                                        if (isVisible(textarea) && !textarea.disabled) {
                                            return textarea;
                                        }
                                    }
                                    
                                    return null;
                                }
                            """)
                            
                            if js_handle:
                                # Convert JSHandle to ElementHandle
                                if isinstance(js_handle, ElementHandle):
                                    search_box = js_handle
                                elif hasattr(js_handle, 'as_element'):
                                    search_box = js_handle.as_element()
                                else:
                                    # Try to use it directly if it's already an element handle
                                    search_box = js_handle
                        except Exception as e:
                            print(f"  evaluate_handle failed: {e}", flush=True)
                        
        except Exception as e:
            last_error = f"JavaScript search failed: {str(e)}"
            print(f"  JavaScript search failed: {e}", flush=True)
        
        # Fallback to traditional selector approach if JavaScript failed
        if not search_box:
            print("  JavaScript approach failed, trying traditional selectors...", flush=True)
            search_selectors = [
                # Contenteditable divs (modern UI)
                'div[contenteditable="true"]',
                '[contenteditable="true"]',
                # Textareas
                'textarea[placeholder*="Ask anything"]',
                'textarea[placeholder*="ask anything"]',
                'textarea[placeholder*="Ask"]',
                'textarea',
                # Inputs
                'input[type="text"]',
                'input[type="search"]',
            ]
            
            for selector in search_selectors:
                try:
                    print(f"    Trying: {selector}", flush=True)
                    search_box = self.page.wait_for_selector(selector, timeout=2000, state="visible")
                    if search_box and search_box.is_visible():
                        # Verify it's the right element
                        try:
                            text = search_box.inner_text() or ''
                            placeholder = search_box.get_attribute('placeholder') or ''
                            if 'ask' in text.lower() or 'ask' in placeholder.lower() or selector == 'textarea':
                                print(f"  ✓ Found search box with: {selector}", flush=True)
                                break
                        except:
                            pass
                    else:
                        search_box = None
                except Exception as e:
                    last_error = str(e)
                    continue
        
        if not search_box:
            # Take screenshot for debugging
            try:
                screenshot_path = "debug_search_failed.png"
                self.page.screenshot(path=screenshot_path, full_page=True)
                print(f"  Debug screenshot saved: {screenshot_path}", flush=True)
            except Exception as e:
                print(f"  Could not save screenshot: {e}", flush=True)
            
            # Get page title and URL for debugging
            try:
                title = self.page.title()
                url = self.page.url
                print(f"  Page title: {title}", flush=True)
                print(f"  Page URL: {url}", flush=True)
            except:
                pass
            
            raise Exception(
                f"Could not find search input.\n"
                f"Last error: {last_error}\n"
                f"Page may not be fully loaded or structure changed.\n"
                f"Check debug_search_failed.png for visual debugging.\n"
                f"Make sure you're logged in and on the Perplexity homepage."
            )
        
        # Determine element type and handle accordingly
        try:
            element_tag = search_box.evaluate("el => el.tagName.toLowerCase()")
            is_contenteditable = search_box.evaluate("el => el.contentEditable === 'true'")
        except:
            # Fallback: check tag name via attribute
            try:
                tag_name = search_box.evaluate("el => el.tagName")
                element_tag = tag_name.lower() if tag_name else 'textarea'
                is_contenteditable = False
            except:
                element_tag = 'textarea'
                is_contenteditable = False
        
        # Network monitoring is already set up in start() if debug_network is enabled
        
        # Click to focus first (important for all UIs)
        try:
            search_box.click()
            time.sleep(0.1)  # Minimal wait
        except:
            pass
        
        # Clear any existing text and enter query
        print(f"  Entering query...", flush=True)
        
        if is_contenteditable or element_tag == 'div':
            # Handle contenteditable divs - optimized for speed
            try:
                # Clear and type in one go
                search_box.evaluate(f"""
                    (el) => {{
                        el.focus();
                        el.textContent = '';
                        el.innerText = '';
                    }}
                """)
                # Type faster (30ms delay instead of 50ms)
                search_box.type(query, delay=30)
                
                # Trigger events immediately
                search_box.evaluate("""
                    (el) => {
                        const inputEvent = new Event('input', { bubbles: true });
                        el.dispatchEvent(inputEvent);
                        const changeEvent = new Event('change', { bubbles: true });
                        el.dispatchEvent(changeEvent);
                    }
                """)
            except Exception as e:
                # Fallback: use JavaScript to set content directly
                search_box.evaluate(f"""
                    (el) => {{
                        el.focus();
                        el.innerHTML = '';
                        el.textContent = '{query}';
                        el.innerText = '{query}';
                        const event = new Event('input', {{ bubbles: true }});
                        el.dispatchEvent(event);
                    }}
                """)
        else:
            # Handle textarea/input with standard methods
            try:
                search_box.clear()
            except:
                pass
            
        search_box.fill(query)
        
        # Press Enter to submit
        print(f"  Submitting query...", flush=True)
        search_box.press('Enter')
        
        if wait_for_response:
            # Wait for response using smart detection
            print("Waiting for response...", flush=True)
            try:
                # Wait for response container to appear (optimized timeout)
                response_selectors = [
                    '.prose',
                    '[class*="answer"]',
                    '[class*="response"]',
                    '[class*="result"]',
                    '[class*="output"]',
                    '[data-testid*="answer"]',
                    '[data-testid*="response"]',
                    'main article',
                    '[role="article"]',
                ]
                
                response_found = False
                for selector in response_selectors:
                    try:
                        # Shorter timeout per selector
                        self.page.wait_for_selector(selector, timeout=3000, state="visible")
                        response_found = True
                        print(f"  ✓ Response container found", flush=True)
                        break
                    except:
                        continue
                
                if not response_found:
                    # Try one more time with a longer wait
                    try:
                        self.page.wait_for_selector('.prose, [class*="answer"], main article', timeout=5000, state="visible")
                        response_found = True
                    except:
                        pass
                
                if response_found:
                    # Wait for initial rendering (Perplexity streams content)
                    print("  Waiting for content to render...", flush=True)
                    time.sleep(3)  # Give time for initial content to appear
                
                # Wait for response text to stabilize and fully render
                response_text = ""
                previous_length = 0
                stable_count = 0
                growing_count = 0
                max_wait_time = timeout / 1000  # Convert to seconds
                start_time = time.time()
                check_interval = 0.8  # Check every 800ms (slightly longer for rendering)
                
                print("  Monitoring response completion...", flush=True)
                
                while (time.time() - start_time) < max_wait_time:
                    current_text = self.get_response_text()
                    current_length = len(current_text) if current_text else 0
                    
                    if current_text:
                        # Check if text is growing (still streaming/rendering)
                        if current_length > previous_length:
                            growing_count += 1
                            stable_count = 0  # Reset stability counter
                            length_diff = current_length - previous_length
                            response_text = current_text
                            if self.debug_network:
                                print(f"    Text growing: {current_length} chars (+{length_diff})", flush=True)
                            previous_length = current_length
                        # Check if text is stable (not changing)
                        elif current_text == response_text:
                            stable_count += 1
                            # Wait for 5 seconds of stability (6-7 checks) to ensure rendering is complete
                            if stable_count >= 6:
                                print(f"  ✓ Response stable for {stable_count * check_interval:.1f}s", flush=True)
                                break
                        else:
                            # Text changed but length same (content reformatted)
                            stable_count = 0
                            response_text = current_text
                            previous_length = current_length
                    else:
                        # No text yet, keep waiting
                        stable_count = 0
                        growing_count = 0
                    
                    time.sleep(check_interval)
                
                # Final extraction with a bit more wait for any final rendering
                if response_text:
                    time.sleep(1)  # One more second for final render
                    final_text = self.get_response_text()
                    if final_text and len(final_text) > len(response_text):
                        response_text = final_text
                
                if response_text:
                    print(f"✓ Response received ({len(response_text)} chars)", flush=True)
                    return response_text
                else:
                    print("⚠ Response container found but no text extracted", flush=True)
                    print("  Response may still be loading or format changed", flush=True)
                    return ""
                
            except Exception as e:
                print(f"Timeout or error waiting for response: {e}", flush=True)
                # Try to get whatever text is available
                response_text = self.get_response_text()
                if response_text:
                    print(f"✓ Partial response received ({len(response_text)} chars)", flush=True)
                    return response_text
                return ""
    
    def get_response_text(self) -> str:
        """Extract response text from page using JavaScript for better extraction"""
        if not self.page:
            return ""
        
        # Extract ALL meaningful content from main element - maximal extraction
        try:
            response_data = self.page.evaluate("""
                () => {
                    // Get everything from main - it contains ALL response content
                    const main = document.querySelector('main');
                    if (!main) return '';
                    
                    // Get ALL text from main (includes answer, sections, sources, related questions)
                    const allText = main.innerText || main.textContent || '';
                    
                    // UI keywords to filter out
                    const uiKeywords = [
                        'Home', 'Travel', 'Academic', 'Sports', 'Library', 'Discover', 
                        'Spaces', 'Finance', 'Account', 'Upgrade', 'Install', 'Share',
                        'Download Comet', 'View All', 'Ask a follow-up', 'Answer', 'Images'
                    ];
                    
                    const lines = allText.split('\\n');
                    const filtered = [];
                    const seenLines = new Set(); // Track duplicates
                    const seenShortLines = new Set(); // Track short repeated lines (likely navigation)
                    let foundContentStart = false; // Track when we hit actual content
                    
                    // Patterns to detect navigation/bookmarks/JS code
                    const bookmarkPattern = /^(function\(|window\.open|Bookmarks|View All|Download Comet)/i;
                    const jsCodePattern = /^(function|const |let |var |window\.|document\.|\(function\(\))/i;
                    const repeatedQueryPattern = /^(What is|How does|Tell me about|Explain)/i; // Common query starters
                    
                    for (const line of lines) {
                        const trimmed = line.trim();
                        if (!trimmed) {
                            // Keep empty lines if we've found content (formatting)
                            if (foundContentStart) {
                                filtered.push('');
                            }
                            continue;
                        }
                        
                        // Filter single-word exact UI matches
                        const words = trimmed.split(/\\s+/);
                        const isSingleWordUI = words.length === 1 && uiKeywords.some(kw => 
                            trimmed.toLowerCase() === kw.toLowerCase());
                        
                        if (isSingleWordUI) continue;
                        
                        // Skip bookmark/JavaScript code patterns
                        if (bookmarkPattern.test(trimmed) || jsCodePattern.test(trimmed)) {
                            continue;
                        }
                        
                        // Skip if it looks like JavaScript code (contains common JS patterns)
                        if (trimmed.includes('function(') || trimmed.includes('window.open') || 
                            trimmed.includes('encodeURIComponent') || trimmed.includes('toLocaleDateString')) {
                            continue;
                        }
                        
                        // Skip "Bookmarks", "View All", "Download Comet" even if not single word
                        if (trimmed === 'Bookmarks' || trimmed === 'View All' || trimmed === 'Download Comet') {
                            continue;
                        }
                        
                        // Skip duplicate short lines (like repeated queries from search history)
                        const lineLower = trimmed.toLowerCase();
                        
                        // Before content starts: skip ALL duplicates and short lines that look like queries
                        if (!foundContentStart) {
                            if (trimmed.length < 60) {
                                // Skip if it's a duplicate or looks like a query/question
                                if (seenLines.has(lineLower) || 
                                    trimmed.endsWith('?') || 
                                    repeatedQueryPattern.test(trimmed) ||
                                    words.length <= 6) {
                                    continue;
                                }
                            }
                        } else {
                            // After content starts: only skip exact duplicates of very short lines
                            if (trimmed.length < 30 && seenShortLines.has(lineLower)) {
                                continue;
                            }
                            if (trimmed.length < 50) {
                                seenShortLines.add(lineLower);
                            }
                        }
                        
                        // Mark when we start seeing actual content (not just navigation)
                        // Look for longer lines, sentences, or content indicators
                        if (!foundContentStart) {
                            // Real content indicators:
                            // - Long lines (>50 chars)
                            // - Lines with multiple sentences (periods, commas)
                            // - Lines with citations (contains + or numbers like "ibm+2")
                            // - Lines starting with capital letters and having substantial length
                            const hasContent = trimmed.length > 50 || 
                                             (trimmed.match(/[.,;]/g) && trimmed.match(/[.,;]/g).length > 1) ||
                                             /\\+\\d+/.test(trimmed) || // Citation pattern like "ibm+2"
                                             (/^[A-Z]/.test(trimmed) && trimmed.length > 30);
                            
                            if (hasContent) {
                                foundContentStart = true;
                            }
                        }
                        
                        seenLines.add(lineLower);
                        filtered.push(trimmed);
                    }
                    
                    let result = filtered.join('\\n').trim();
                    
                    // Clean up leading navigation items if still present
                    const resultLines = result.split('\\n');
                    let contentStartIdx = 0;
                    for (let i = 0; i < resultLines.length; i++) {
                        const line = resultLines[i].trim();
                        // Look for start of actual content (long lines, starts with capital, has content)
                        if (line.length > 50 || /^[A-Z]/.test(line) && line.length > 20) {
                            contentStartIdx = i;
                            break;
                        }
                    }
                    if (contentStartIdx > 0) {
                        result = resultLines.slice(contentStartIdx).join('\\n').trim();
                    }
                    
                    // Extract all external links (sources) - comprehensive extraction
                    const links = [];
                    const seenUrls = new Set();
                    
                    // Find ALL links in main first
                    const allLinks = main.querySelectorAll('a[href]');
                    
                    allLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (!href) return;
                        
                        // Normalize href
                        let url = href;
                        if (url.startsWith('//')) {
                            url = 'https:' + url;
                        } else if (url.startsWith('/') && !url.startsWith('//')) {
                            // Skip internal Perplexity links (unless they're absolute)
                            if (!url.includes('http')) return;
                            url = 'https://www.perplexity.ai' + url;
                        }
                        
                        // Only include external HTTP links
                        if (url.startsWith('http') && 
                            !url.includes('perplexity.ai') && 
                            !url.includes('facebook.com') && 
                            !url.includes('twitter.com') &&
                            !url.includes('x.com') &&
                            !url.includes('linkedin.com') &&
                            !url.includes('pinterest.com') &&
                            !seenUrls.has(url)) {
                            
                            seenUrls.add(url);
                            
                            // Comprehensive link text extraction
                            let text = '';
                            
                            // Method 1: Direct link text
                            text = (link.innerText || link.textContent || '').trim();
                            
                            // Method 2: Attributes
                            if (!text || text.length < 2) {
                                text = (link.getAttribute('title') || 
                                       link.getAttribute('aria-label') || 
                                       link.getAttribute('data-title') || '').trim();
                            }
                            
                            // Method 3: Parent element text (common pattern)
                            if (!text || text.length < 2) {
                                const parent = link.parentElement;
                                if (parent) {
                                    // Get all text from parent
                                    const parentText = (parent.innerText || parent.textContent || '').trim();
                                    // Remove the URL from parent text
                                    let cleanText = parentText.replace(url, '').replace(href, '').trim();
                                    
                                    // If parent has multiple children, try to get just the text parts
                                    if (cleanText.length > 200) {
                                        // Look for specific text elements
                                        const textElements = parent.querySelectorAll('span, div, p, h1, h2, h3, h4');
                                        for (const el of textElements) {
                                            const elText = (el.innerText || el.textContent || '').trim();
                                            if (elText.length > 5 && elText.length < 200 && !elText.includes(url)) {
                                                cleanText = elText;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (cleanText.length > 2 && cleanText.length < 200) {
                                        text = cleanText;
                                    }
                                }
                            }
                            
                            // Method 4: Previous/next sibling elements
                            if (!text || text.length < 2) {
                                // Check previous sibling
                                const prevSibling = link.previousElementSibling;
                                if (prevSibling) {
                                    const prevText = (prevSibling.innerText || prevSibling.textContent || '').trim();
                                    if (prevText.length > 2 && prevText.length < 200) {
                                        text = prevText;
                                    }
                                }
                                
                                // Check next sibling
                                if (!text || text.length < 2) {
                                    const nextSibling = link.nextElementSibling;
                                    if (nextSibling) {
                                        const nextText = (nextSibling.innerText || nextSibling.textContent || '').trim();
                                        if (nextText.length > 2 && nextText.length < 200) {
                                            text = nextText;
                                        }
                                    }
                                }
                            }
                            
                            // Method 5: Look for text nodes in the same container
                            if (!text || text.length < 2) {
                                const container = link.closest('div, article, section, li');
                                if (container) {
                                    // Get all text but exclude the link itself
                                    const containerText = container.cloneNode(true);
                                    // Remove the link from clone
                                    const linkClone = containerText.querySelector('a[href="' + href + '"]');
                                    if (linkClone) {
                                        linkClone.remove();
                                        const remainingText = (containerText.innerText || containerText.textContent || '').trim();
                                        if (remainingText.length > 2 && remainingText.length < 300) {
                                            text = remainingText;
                                        }
                                    }
                                }
                            }
                            
                            // Method 6: Look for nearby elements with class names containing "title", "name", "label"
                            if (!text || text.length < 2) {
                                const container = link.closest('div, article, section');
                                if (container) {
                                    const titleEl = container.querySelector('[class*="title"], [class*="name"], [class*="label"], h1, h2, h3, h4, h5, h6');
                                    if (titleEl) {
                                        const titleText = (titleEl.innerText || titleEl.textContent || '').trim();
                                        if (titleText.length > 2 && titleText.length < 200) {
                                            text = titleText;
                                        }
                                    }
                                }
                            }
                            
                            // Final fallback: use domain name with better formatting
                            if (!text || text.length < 2) {
                                try {
                                    const urlObj = new URL(url);
                                    let hostname = urlObj.hostname.replace('www.', '');
                                    // Capitalize first letter
                                    text = hostname.charAt(0).toUpperCase() + hostname.slice(1);
                                } catch(e) {
                                    text = url;
                                }
                            }
                            
                            // Skip only very obvious navigation links (single-word exact matches)
                            const isNavLink = uiKeywords.some(kw => 
                                text.toLowerCase() === kw.toLowerCase() && text.length < 20);
                            
                            // Skip if text is just the URL (but allow domain names)
                            const isJustUrl = (text === url || text === href) && text.length > 50;
                            
                            // Include link if it has any reasonable text
                            if (!isNavLink && !isJustUrl && text.length >= 1) {
                                // Clean up text
                                text = text.replace(/\\s+/g, ' ').trim();
                                // If text is still too short, use domain name
                                if (text.length < 2) {
                                    try {
                                        const urlObj = new URL(url);
                                        text = urlObj.hostname.replace('www.', '');
                                    } catch(e) {
                                        text = url;
                                    }
                                }
                                links.push({ text: text, url: url });
                            }
                        }
                    });
                    
                    // Also try to find source links near "X sources" text
                    // When we see "10 sources", look for nearby containers with source links
                    const sourceCountPattern = /(\\d+)\\s+sources?/i;
                    const walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while (node = walker.nextNode()) {
                        if (node.textContent && sourceCountPattern.test(node.textContent)) {
                            // Found "X sources" text, look for links in parent containers
                            let parent = node.parentElement;
                            let depth = 0;
                            while (parent && depth < 7) {
                                // Look for ALL links in this parent (not just http-starting)
                                const nearbyLinks = parent.querySelectorAll('a[href]');
                                nearbyLinks.forEach(link => {
                                    let href = link.getAttribute('href');
                                    if (!href) return;
                                    
                                    // Normalize href
                                    if (href.startsWith('//')) {
                                        href = 'https:' + href;
                                    } else if (href.startsWith('/') && !href.startsWith('//')) {
                                        return; // Skip relative links
                                    }
                                    
                                    if (href.startsWith('http') && !href.includes('perplexity.ai') && !seenUrls.has(href)) {
                                        let text = (link.innerText || link.textContent || link.getAttribute('title') || '').trim();
                                        
                                        // Try parent text if link has no text
                                        if (!text || text.length < 2) {
                                            const linkParent = link.parentElement;
                                            if (linkParent) {
                                                const parentText = (linkParent.innerText || linkParent.textContent || '').trim();
                                                // Use parent text if reasonable length
                                                if (parentText.length > 2 && parentText.length < 300) {
                                                    text = parentText.replace(href, '').trim();
                                                }
                                            }
                                        }
                                        
                                        // Fallback to domain
                                        if (!text || text.length < 2) {
                                            try {
                                                const urlObj = new URL(href);
                                                text = urlObj.hostname.replace('www.', '');
                                            } catch(e) {
                                                text = href;
                                            }
                                        }
                                        
                                        if (text.length >= 1) {
                                            seenUrls.add(href);
                                            links.push({ text: text.replace(/\\s+/g, ' ').trim(), url: href });
                                        }
                                    }
                                });
                                parent = parent.parentElement;
                                depth++;
                            }
                        }
                    }
                    
                    // Add sources section if we found links
                    if (links.length > 0) {
                        // Links are already deduplicated by seenUrls during extraction
                        // Sort by text length (more descriptive first) or alphabetically
                        links.sort((a, b) => {
                            // Prefer links with better text (longer, more descriptive)
                            if (a.text.length !== b.text.length) {
                                return b.text.length - a.text.length;
                            }
                            return a.text.localeCompare(b.text);
                        });
                        
                        // Add sources section at the end
                        result += '\\n\\n---\\nSources:\\n';
                        links.forEach((link, idx) => {
                            // Clean up link text (remove extra whitespace, newlines)
                            const cleanText = link.text.replace(/\\s+/g, ' ').trim();
                            result += `${idx + 1}. [${cleanText}](${link.url})\\n`;
                        });
                    }
                    
                    return result;
                }
            """)
            
            if response_data:
                return response_data.strip()
        
        except Exception as e:
            # Fallback to traditional method
            pass
        
        # Traditional fallback method
        selectors = [
            '.prose',
            '[class*="answer"]',
            '[class*="response"]',
            '[class*="result"]',
            'main article',
            '[role="article"]',
        ]
        
        best_text = ""
        best_length = 0
        
        for selector in selectors:
            try:
                elements = self.page.query_selector_all(selector)
                for element in elements:
                    try:
                        if element.is_visible():
                            text = element.inner_text()
                            if text and len(text) > best_length:
                                text_lower = text.lower()
                                skip_keywords = ['menu', 'navigation', 'footer', 'header', 'cookie', 'sign in', 'log in', 'sign up']
                                if not any(skip in text_lower for skip in skip_keywords):
                                    best_text = text
                                    best_length = len(text)
                    except:
                        continue
            except:
                continue
        
        if best_text:
            return best_text.strip()
        
        return ""
    
    def interactive_mode(self) -> None:
        """Keep browser open for interactive use"""
        if not self.page:
            return
        
        print("\nBrowser is open. Use it interactively.")
        print("Press Ctrl+C to close...")
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nClosing browser...")
    
    def close(self) -> None:
        """Close browser and cleanup"""
        try:
            if self.page:
                self.page.close()
                self.page = None
        except:
            pass
        
        try:
            if self.context:
                # For persistent context, browser IS the context
                if self.user_data_dir:
                    # Persistent context - close all pages but keep context
                    for page in self.context.pages:
                        try:
                            page.close()
                        except:
                            pass
                    # Close the persistent context
                    self.context.close()
                else:
                    # Regular context - close it
                    self.context.close()
                self.context = None
        except:
            pass
        
        try:
            if self.browser and not self.user_data_dir:
                # Only close browser if it's not a persistent context
                # (persistent context is already closed above)
                self.browser.close()
                self.browser = None
        except:
            pass
        
        try:
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
        except:
            pass
        
        print("✓ Browser closed")