"""
ABOUTME: Handles Cloudflare challenge solving and cookie extraction
ABOUTME: Uses cloudscraper to solve JavaScript challenges and obtain cf_clearance cookies
"""
import logging
import time
from typing import Any, Dict, Optional
from pathlib import Path
import sys

logger = logging.getLogger(__name__)

# Try to import cloudscraper
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


class CloudflareHandler:
    """Handles Cloudflare challenge solving using cloudscraper"""
    
    def __init__(self):
        """Initialize Cloudflare handler"""
        self._cloudscraper_cookies: Optional[Dict[str, str]] = None
        self._cloudscraper_user_agent: Optional[str] = None
    
    def solve_challenge(
        self, 
        url: str = "https://www.perplexity.ai",
        login_cookies: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Solve Cloudflare challenge and extract cookies
        
        Args:
            url: URL to solve challenge for
            login_cookies: Optional login cookies to merge with Cloudflare cookies
            
        Returns:
            Dictionary of cookies including cf_clearance
            
        Raises:
            ImportError: If cloudscraper is not available
            Exception: If challenge solving fails
        """
        if not CLOUDSCRAPER_AVAILABLE:
            raise ImportError(
                "Cloudscraper is required for Cloudflare bypass. "
                "Install it with: pip install cloudscraper requests"
            )
        
        logger.info("Solving Cloudflare challenge with cloudscraper")
        
        try:
            # Try CloudflareBypass wrapper first
            if CloudflareBypass is not None:
                cookies = self._solve_with_wrapper(url, login_cookies)
                if cookies:
                    return cookies
            
            # Fallback to direct cloudscraper
            return self._solve_with_direct_cloudscraper(url, login_cookies)
            
        except Exception as e:
            error_msg = f"Cloudscraper failed to solve Cloudflare challenge: {str(e)}"
            logger.warning(error_msg)
            raise Exception(error_msg)
    
    def _solve_with_wrapper(
        self, 
        url: str,
        login_cookies: Optional[Dict[str, str]]
    ) -> Optional[Dict[str, str]]:
        """
        Solve challenge using CloudflareBypass wrapper
        
        Args:
            url: URL to solve challenge for
            login_cookies: Optional login cookies
            
        Returns:
            Dictionary of cookies or None if failed
        """
        try:
            bypass = CloudflareBypass(
                browser='firefox',
                use_stealth=True,
                interpreter='js2py',
                debug=False,
                auto_refresh_on_403=True,
                max_403_retries=5,
                session_refresh_interval=3600
            )
            
            # Extract user agent
            self._cloudscraper_user_agent = bypass.scraper.headers.get('User-Agent')
            if self._cloudscraper_user_agent:
                logger.debug(f"Extracted user agent from cloudscraper: {self._cloudscraper_user_agent[:50]}...")
            
            # Add login cookies if provided
            if login_cookies:
                bypass.update_cookies(login_cookies)
                logger.debug(f"Using {len(login_cookies)} login cookies with cloudscraper")
            
            # Solve challenge
            if bypass.solve_challenge(url):
                cloudscraper_cookies = bypass.get_cookies_dict()
                self._merge_login_cookies(cloudscraper_cookies, login_cookies)
                return cloudscraper_cookies
            else:
                raise Exception("Cloudflare challenge solve returned False")
                
        except Exception as e:
            logger.warning(f"CloudflareBypass wrapper failed: {e}, falling back to direct cloudscraper")
            return None
    
    def _solve_with_direct_cloudscraper(
        self,
        url: str,
        login_cookies: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Solve challenge using direct cloudscraper
        
        Args:
            url: URL to solve challenge for
            login_cookies: Optional login cookies
            
        Returns:
            Dictionary of cookies
            
        Raises:
            Exception: If challenge solving fails
        """
        import cloudscraper
        
        logger.debug("Creating cloudscraper with browser emulation and stealth mode")
        
        if not hasattr(cloudscraper, 'create_scraper'):
            raise ImportError("cloudscraper.create_scraper not available")
        
        scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'firefox',
                'platform': 'windows',
                'desktop': True
            },
            interpreter='js2py',
            delay=5,
            debug=False,
            doubleDown=True,
            enable_stealth=True,
            stealth_options={
                'min_delay': 1.0,
                'max_delay': 3.0,
                'human_like_delays': True,
                'randomize_headers': True,
                'browser_quirks': True
            },
            auto_refresh_on_403=True,
            max_403_retries=5,
            session_refresh_interval=3600
        )
        
        # Extract user agent
        self._cloudscraper_user_agent = scraper.headers.get('User-Agent')
        if self._cloudscraper_user_agent:
            logger.debug(f"Extracted user agent from cloudscraper: {self._cloudscraper_user_agent[:50]}...")
        
        # Attempt to solve challenge
        response = self._attempt_challenge_solving(scraper, url)
        
        # Extract cookies
        cloudscraper_cookies = self._extract_cookies_from_scraper(scraper, response)
        
        # Merge with login cookies
        self._merge_login_cookies(cloudscraper_cookies, login_cookies)
        
        # Verify critical cookies
        self._verify_cloudflare_cookies(cloudscraper_cookies)
        
        return cloudscraper_cookies
    
    def _attempt_challenge_solving(self, scraper: Any, url: str) -> Any:
        """
        Attempt to solve Cloudflare challenge with retries
        
        Args:
            scraper: Cloudscraper instance
            url: URL to access
            
        Returns:
            Response object
            
        Raises:
            Exception: If all attempts fail
        """
        logger.info("Getting fresh Cloudflare cookies with cloudscraper")
        
        max_attempts = 10
        response = None
        
        for attempt in range(1, max_attempts + 1):
            logger.debug(f"Cloudflare bypass attempt {attempt}/{max_attempts}")
            
            try:
                response = scraper.get(url, timeout=90, allow_redirects=True)
                
                # Check response status
                if response.status_code != 200:
                    if self._should_retry(response.status_code, attempt, max_attempts):
                        wait_time = min(1 + (attempt * 0.5), 3)
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Failed after {attempt} attempts with status {response.status_code}")
                
                # Check if still on challenge page
                if self._is_challenge_page(response):
                    wait_time = min(3 + attempt, 10)
                    logger.debug(f"Still on Cloudflare challenge page (attempt {attempt}), waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                # Verify we got actual content
                if self._has_perplexity_content(response):
                    logger.info("Successfully bypassed Cloudflare - got Perplexity content")
                    break
                else:
                    logger.debug(f"Response doesn't look like Perplexity content (attempt {attempt})")
                    wait_time = min(1 + attempt, 3)
                    time.sleep(wait_time)
                    continue
                    
            except Exception as e:
                logger.debug(f"Request failed (attempt {attempt}): {e}")
                if attempt < max_attempts:
                    wait_time = min(1 + (attempt * 0.5), 3)
                    time.sleep(wait_time)
                    continue
                else:
                    raise
        
        # Final validation
        if not response or response.status_code != 200:
            raise Exception(f"Failed to get Cloudflare cookies - status: {response.status_code if response else 'None'}")
        
        if self._is_challenge_page(response):
            raise Exception("Still on Cloudflare challenge page after all attempts")
        
        # Wait for cookies to be fully set
        logger.debug("Waiting for Cloudflare cookies to be fully set")
        time.sleep(0.3)
        
        # Final request to ensure cookies are set
        try:
            scraper.get(url, timeout=10)
            time.sleep(0.2)
        except Exception as e:
            logger.debug(f"Final request failed (may be OK): {e}")
        
        return response
    
    def _should_retry(self, status_code: int, attempt: int, max_attempts: int) -> bool:
        """
        Determine if request should be retried
        
        Args:
            status_code: HTTP status code
            attempt: Current attempt number
            max_attempts: Maximum attempts allowed
            
        Returns:
            True if should retry
        """
        if status_code == 403 and attempt >= 5:
            logger.warning(f"Cloudflare consistently returning 403 after {attempt} attempts")
            logger.warning("This may indicate IP blocking or advanced protection")
            if attempt >= max_attempts:
                return False
        
        logger.debug(f"Status {status_code}, waiting and retrying (attempt {attempt}/{max_attempts})")
        return True
    
    def _is_challenge_page(self, response: Any) -> bool:
        """
        Check if response is a Cloudflare challenge page
        
        Args:
            response: Response object
            
        Returns:
            True if challenge page detected
        """
        response_text_lower = response.text.lower()
        return ('just a moment' in response_text_lower or 
                'checking your browser' in response_text_lower or
                'please wait' in response_text_lower or
                'cf-browser-verification' in response_text_lower)
    
    def _has_perplexity_content(self, response: Any) -> bool:
        """
        Verify response contains actual Perplexity content
        
        Args:
            response: Response object
            
        Returns:
            True if Perplexity content detected
        """
        response_text_lower = response.text.lower()
        return ('perplexity' in response_text_lower and 
                ('ask anything' in response_text_lower or 
                 'search' in response_text_lower or
                 'home' in response_text_lower))
    
    def _extract_cookies_from_scraper(self, scraper: Any, response: Any) -> Dict[str, str]:
        """
        Extract cookies from scraper and response
        
        Args:
            scraper: Cloudscraper instance
            response: Response object
            
        Returns:
            Dictionary of cookies
        """
        # Get cookies from scraper
        if hasattr(scraper.cookies, 'get_dict'):
            cookies = scraper.cookies.get_dict()
        else:
            cookies = dict(scraper.cookies)
        
        # Check response headers for Set-Cookie
        set_cookie_headers = self._extract_set_cookie_headers(response)
        
        # Parse Set-Cookie headers
        for cookie_header in set_cookie_headers:
            if 'cf_clearance=' in cookie_header:
                self._extract_cf_clearance_from_header(cookie_header, cookies)
        
        # Log cookie extraction
        logger.debug(f"Cloudscraper obtained {len(cookies)} cookies")
        cf_cookies = [k for k in cookies.keys() if 'cf' in k.lower() or k.startswith('__cf')]
        if cf_cookies:
            logger.debug(f"Cloudflare cookies from cloudscraper: {cf_cookies}")
        else:
            logger.warning("No Cloudflare cookies found in cloudscraper response")
        
        # Try to get cf_clearance from cookie jar if not in dict
        if 'cf_clearance' not in cookies:
            for cookie in scraper.cookies:
                if cookie.name == 'cf_clearance':
                    cookies['cf_clearance'] = cookie.value
                    logger.debug(f"Found cf_clearance in cookie jar (length: {len(cookie.value)})")
                    break
        
        return cookies
    
    def _extract_set_cookie_headers(self, response: Any) -> list:
        """
        Extract Set-Cookie headers from response
        
        Args:
            response: Response object
            
        Returns:
            List of Set-Cookie header values
        """
        if hasattr(response.headers, 'getall'):
            return response.headers.getall('Set-Cookie', [])
        elif isinstance(response.headers.get('Set-Cookie', ''), list):
            return response.headers.get('Set-Cookie', [])
        else:
            set_cookie_val = response.headers.get('Set-Cookie', '')
            return [set_cookie_val] if set_cookie_val else []
    
    def _extract_cf_clearance_from_header(self, cookie_header: str, cookies: Dict[str, str]) -> None:
        """
        Extract cf_clearance from Set-Cookie header
        
        Args:
            cookie_header: Set-Cookie header value
            cookies: Dictionary to add cookie to
        """
        try:
            parts = cookie_header.split(';')[0].split('=')
            if len(parts) == 2 and parts[0].strip() == 'cf_clearance':
                cf_val = parts[1].strip()
                if cf_val and cf_val not in cookies.values():
                    cookies['cf_clearance'] = cf_val
                    logger.debug("Extracted cf_clearance from Set-Cookie header")
        except Exception:
            pass
    
    def _merge_login_cookies(
        self,
        cloudscraper_cookies: Dict[str, str],
        login_cookies: Optional[Dict[str, str]]
    ) -> None:
        """
        Merge login cookies with Cloudflare cookies
        
        Args:
            cloudscraper_cookies: Dictionary to merge into
            login_cookies: Login cookies to merge
        """
        if login_cookies:
            for k, v in login_cookies.items():
                if 'cf' not in k.lower() and not k.startswith('__cf'):
                    cloudscraper_cookies[k] = v
            logger.debug(f"Merged {len(login_cookies)} login cookies with fresh Cloudflare cookies")
        else:
            logger.debug("No login cookies to merge")
    
    def _verify_cloudflare_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Verify critical Cloudflare cookies are present
        
        Args:
            cookies: Dictionary of cookies to verify
        """
        cf_clearance = cookies.get('cf_clearance')
        cf_bm = cookies.get('__cf_bm')
        
        if not cf_clearance:
            logger.warning("cf_clearance cookie missing - Cloudflare may still block, continuing anyway")
        else:
            logger.debug(f"cf_clearance cookie obtained (length: {len(cf_clearance)})")
        
        if not cf_bm:
            logger.warning("__cf_bm cookie not found (may still work)")
        
        cf_cookies = [k for k in cookies.keys() if 'cf' in k.lower() or k.startswith('__cf')]
        logger.debug(f"Cloudflare cookies obtained: {cf_cookies}")
    
    def get_user_agent(self) -> Optional[str]:
        """
        Get user agent extracted from cloudscraper
        
        Returns:
            User agent string or None
        """
        return self._cloudscraper_user_agent
    
    def get_cookies(self) -> Optional[Dict[str, str]]:
        """
        Get last extracted cookies
        
        Returns:
            Dictionary of cookies or None
        """
        return self._cloudscraper_cookies
