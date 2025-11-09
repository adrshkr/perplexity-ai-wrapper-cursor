"""
Cloudflare Bypass Utility
Wrapper around cloudscraper with Perplexity-specific configuration
"""
import sys
import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple, Any
import time
import random

# Add cloudscraper submodule to path
project_root = Path(__file__).parent.parent.parent
cloudscraper_path = project_root / 'cloudscraper'
if cloudscraper_path.exists() and str(cloudscraper_path) not in sys.path:
    sys.path.insert(0, str(cloudscraper_path))

try:
    import cloudscraper
except ImportError:
    cloudscraper = None
    # Don't raise here - let the class handle it gracefully


class CloudflareBypass:
    """
    Wrapper around cloudscraper that provides Cloudflare bypass capabilities
    with Perplexity-specific configuration
    """
    
    def __init__(
        self,
        browser: str = 'chrome',
        delay_range: Tuple[float, float] = (1.0, 3.0),
        use_stealth: bool = True,
        proxy_rotation: Optional[List[str]] = None,
        interpreter: str = 'js2py',
        auto_refresh_on_403: bool = True,
        max_403_retries: int = 3,
        session_refresh_interval: int = 3600,
        debug: bool = False
    ):
        """
        Initialize Cloudflare bypass
        
        Args:
            browser: Browser to emulate ('chrome', 'firefox')
            delay_range: Random delay range for requests (min, max) seconds
            use_stealth: Enable stealth mode (human-like behavior)
            proxy_rotation: Optional list of proxy URLs for rotation
            interpreter: JavaScript interpreter ('js2py', 'nodejs', 'native')
            auto_refresh_on_403: Automatically refresh session on 403 errors
            max_403_retries: Maximum retry attempts on 403 errors
            session_refresh_interval: Time in seconds to refresh session
            debug: Enable debug output
        """
        if cloudscraper is None:
            raise ImportError(
                "cloudscraper is not available. Install it via:\n"
                "  pip install cloudscraper\n"
                "Or ensure the git submodule is initialized:\n"
                "  git submodule update --init --recursive"
            )
        
        self.browser = browser
        self.delay_range = delay_range
        self.use_stealth = use_stealth
        self.proxy_rotation = proxy_rotation
        self.interpreter = interpreter
        self.auto_refresh_on_403 = auto_refresh_on_403
        self.max_403_retries = max_403_retries
        self.session_refresh_interval = session_refresh_interval
        self.debug = debug
        
        # Create scraper with basic parameters that are definitely supported
        # Use create_scraper with minimal, well-supported parameters
        scraper_kwargs = {
            'browser': browser,
            'interpreter': interpreter,
            'debug': debug,
            'delay': delay_range[1] if delay_range else None,  # Use max delay
        }
        
        # Add stealth mode if enabled (only if supported)
        if use_stealth:
            try:
                scraper_kwargs['enable_stealth'] = True
                scraper_kwargs['stealth_options'] = {
                    'min_delay': delay_range[0],
                    'max_delay': delay_range[1],
                    'human_like_delays': True,
                    'randomize_headers': True,
                    'browser_quirks': True
                }
            except:
                # If stealth options fail, continue without them
                pass
        
        # Add proxy rotation if provided (only if supported)
        if proxy_rotation:
            try:
                scraper_kwargs['rotating_proxies'] = proxy_rotation
                scraper_kwargs['proxy_options'] = {
                    'rotation_strategy': 'smart',
                    'ban_time': 300
                }
            except:
                # If proxy options fail, continue without them
                pass
        
        # Create the scraper - use create_scraper which handles parameter validation
        try:
            self.scraper = cloudscraper.create_scraper(**scraper_kwargs)
        except TypeError as e:
            # If create_scraper fails with unsupported parameters, try with minimal params
            if 'unexpected keyword' in str(e) or 'got an unexpected keyword' in str(e):
                # Fallback to minimal parameters
                minimal_kwargs = {
                    'browser': browser,
                    'interpreter': interpreter,
                }
                if delay_range:
                    minimal_kwargs['delay'] = delay_range[1]
                self.scraper = cloudscraper.create_scraper(**minimal_kwargs)
            else:
                raise
        
        # Track session health
        self.session_start_time = time.time()
        self.request_count = 0
    
    def get(self, url: str, **kwargs) -> Any:
        """
        Make GET request with Cloudflare bypass
        
        Args:
            url: Target URL
            **kwargs: Additional requests arguments
        
        Returns:
            Response object
        """
        # Check if session needs refresh
        if self._should_refresh_session():
            self._refresh_session()
        
        # Add random delay if stealth mode enabled
        if self.use_stealth:
            time.sleep(random.uniform(*self.delay_range))
        
        self.request_count += 1
        return self.scraper.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> Any:
        """
        Make POST request with Cloudflare bypass
        
        Args:
            url: Target URL
            **kwargs: Additional requests arguments
        
        Returns:
            Response object
        """
        # Check if session needs refresh
        if self._should_refresh_session():
            self._refresh_session()
        
        # Add random delay if stealth mode enabled
        if self.use_stealth:
            time.sleep(random.uniform(*self.delay_range))
        
        self.request_count += 1
        return self.scraper.post(url, **kwargs)
    
    def get_cookies_dict(self) -> Dict[str, str]:
        """
        Get cookies as dictionary (for use with requests)
        
        Returns:
            Dictionary of cookies
        """
        return dict(self.scraper.cookies)
    
    def get_cookie_string(self, url: str = 'https://www.perplexity.ai') -> Tuple[str, str]:
        """
        Get cookies as string and user agent (for curl/external tools)
        
        Args:
            url: URL to get cookies for
        
        Returns:
            Tuple of (cookie_string, user_agent)
        """
        return cloudscraper.get_cookie_string(
            url,
            user_agent=self.scraper.headers.get('User-Agent', '')
        )
    
    def update_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Update scraper cookies
        
        Args:
            cookies: Dictionary of cookies to add/update
        """
        self.scraper.cookies.update(cookies)
    
    def solve_challenge(self, url: str, timeout: int = 30) -> bool:
        """
        Explicitly solve Cloudflare challenge for a URL
        
        Args:
            url: URL to solve challenge for
            timeout: Request timeout in seconds
        
        Returns:
            True if challenge solved successfully
        """
        try:
            response = self.get(url, timeout=timeout)
            # Check if we got past Cloudflare
            if response.status_code == 200:
                # Check if it's not a challenge page
                response_text = response.text.lower()
                if 'just a moment' not in response_text and 'challenge' not in response_text:
                    return True
            return False
        except Exception as e:
            if self.debug:
                print(f"Challenge solve failed: {e}")
            return False
    
    def _should_refresh_session(self) -> bool:
        """Check if session should be refreshed"""
        elapsed = time.time() - self.session_start_time
        return elapsed >= self.session_refresh_interval
    
    def _refresh_session(self) -> None:
        """Refresh the session by creating a new scraper"""
        if self.debug:
            print("Refreshing session...")
        
        # Create new scraper with same settings (using minimal params)
        scraper_kwargs = {
            'browser': self.browser,
            'interpreter': self.interpreter,
            'debug': self.debug,
        }
        if self.delay_range:
            scraper_kwargs['delay'] = self.delay_range[1]
        
        # Preserve cookies from old session
        old_cookies = dict(self.scraper.cookies)
        
        # Create new scraper with minimal params
        try:
            self.scraper = cloudscraper.create_scraper(**scraper_kwargs)
        except TypeError:
            # Fallback to absolute minimal
            self.scraper = cloudscraper.create_scraper(
                browser=self.browser,
                interpreter=self.interpreter
            )
        self.scraper.cookies.update(old_cookies)
        
        # Reset session timer
        self.session_start_time = time.time()
        self.request_count = 0

