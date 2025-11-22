"""
ABOUTME: Handles cookie injection and validation for browser automation
ABOUTME: Manages Cloudflare cookies, login cookies, and persistent context cookies
"""
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from playwright.sync_api import BrowserContext

logger = logging.getLogger(__name__)


class CookieInjector:
    """Manages cookie injection into Playwright browser context"""
    
    def __init__(self):
        """Initialize cookie injector"""
        self._login_cookies: Optional[Dict[str, str]] = None
        self._cloudscraper_cookies: Optional[Dict[str, str]] = None
        self._cookies_injected: bool = False
        self._formatted_cookies_cache: Optional[List[Dict[str, Any]]] = None
    
    def set_login_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Store login cookies to be injected
        
        Args:
            cookies: Dictionary of cookie name-value pairs
        """
        self._login_cookies = cookies
        self._formatted_cookies_cache = None  # Invalidate cache
        self._cookies_injected = False  # Reset injection flag to allow re-injection with new cookies
    
    def set_cloudscraper_cookies(self, cookies: Dict[str, str]) -> None:
        """
        Store Cloudflare cookies from cloudscraper
        
        Args:
            cookies: Dictionary of Cloudflare cookie name-value pairs
        """
        self._cloudscraper_cookies = cookies
        self._formatted_cookies_cache = None  # Invalidate cache
        self._cookies_injected = False  # Reset injection flag to allow re-injection with new cookies
    
    def should_inject_cookies(self, user_data_dir: Optional[str]) -> bool:
        """
        Determine if cookies should be injected
        
        Args:
            user_data_dir: Path to persistent user data directory
            
        Returns:
            True if cookies should be injected, False otherwise
        """
        # Don't inject cookies if using persistent context (user_data_dir)
        # Persistent context already has cookies from previous sessions
        if user_data_dir:
            return False
        
        # Only inject if we have cookies to inject
        return bool(self._login_cookies or self._cloudscraper_cookies)
    
    def inject_cookies_into_context(
        self, 
        context: 'BrowserContext',
        user_data_dir: Optional[str]
    ) -> None:
        """
        Inject all cookies into browser context BEFORE navigation
        
        Args:
            context: Playwright browser context
            user_data_dir: Path to persistent user data directory (if using persistent context)
        """
        if not context:
            return
        
        # Don't inject if using persistent context
        if not self.should_inject_cookies(user_data_dir):
            return
        
        # Skip if cookies already injected (optimization)
        if self._cookies_injected:
            logger.debug("Cookies already injected, skipping redundant injection")
            return
        
        # Merge cookies (Cloudflare cookies take precedence)
        all_cookies = self._merge_cookies()
        
        if not all_cookies:
            return
        
        # Format cookies for Playwright (use cache if available)
        if self._formatted_cookies_cache is None:
            self._formatted_cookies_cache = self._format_cookies_for_playwright(all_cookies)
        
        playwright_cookies = self._formatted_cookies_cache
        
        if playwright_cookies:
            logger.debug(f"Injecting {len(playwright_cookies)} cookies into browser context")
            self._log_cloudflare_cookies(playwright_cookies)
            
            try:
                context.add_cookies(playwright_cookies)  # type: ignore[arg-type]
                logger.debug(f"Successfully injected {len(playwright_cookies)} cookies")
                self._verify_cookies_in_context(context)
                self._cookies_injected = True
            except Exception:
                # Fallback: try individual cookie injection
                self._inject_cookies_individually(context, playwright_cookies)
    
    def _merge_cookies(self) -> Dict[str, str]:
        """
        Merge login and Cloudflare cookies with proper precedence
        
        Returns:
            Merged cookie dictionary
        """
        all_cookies = {}
        
        # CRITICAL: Cloudflare cookies from cloudscraper MUST come first (they override old ones)
        if self._cloudscraper_cookies:
            all_cookies.update(self._cloudscraper_cookies)
        
        # Then add login cookies (but don't override Cloudflare cookies)
        if self._login_cookies:
            for k, v in self._login_cookies.items():
                # Don't override Cloudflare cookies that we just got from cloudscraper
                # Check for specific Cloudflare cookie patterns, not just 'cf' substring
                # This prevents filtering out legitimate cookies like 'csrf_token', 'config', 'scaffold', etc.
                is_cloudflare_cookie = (
                    k == 'cf_clearance' or
                    k.startswith('__cf') or  # __cf_bm, __cfduid, etc.
                    k.startswith('__Secure-cf_') or  # Secure Cloudflare cookies
                    (k.startswith('cf_') and k != 'cf_clearance') or  # Other cf_* cookies (rare)
                    k.startswith('cf_clearance')  # Variants of cf_clearance
                )
                if not is_cloudflare_cookie:
                    all_cookies[k] = v
        
        return all_cookies
    
    def _format_cookies_for_playwright(self, cookies: Dict[str, str]) -> List[Dict[str, Any]]:
        """
        Format cookies for Playwright's add_cookies() method
        
        Args:
            cookies: Dictionary of cookie name-value pairs
            
        Returns:
            List of cookie dictionaries in Playwright format
        """
        playwright_cookies: List[Dict[str, Any]] = []
        
        for name, value in cookies.items():
            if not name or not isinstance(value, str) or len(str(value)) > 4000:
                continue
            
            try:
                # Use URL-based cookie injection (more reliable than domain/path)
                cookie_data: Dict[str, Any] = {
                    'name': str(name),
                    'value': str(value),
                    'url': 'https://www.perplexity.ai',
                    'secure': True,
                    'sameSite': 'Lax',
                }
                
                # Handle __Host- prefix (requires path=/ and no domain)
                if name.startswith('__Host-'):
                    cookie_data['path'] = '/'
                    # Don't set domain for __Host- cookies
                    if 'domain' in cookie_data:
                        del cookie_data['domain']
                
                playwright_cookies.append(cookie_data)
            except Exception as e:
                logger.debug(f"Failed to format cookie {name}: {e}")
                continue
        
        return playwright_cookies
    
    def _log_cloudflare_cookies(self, playwright_cookies: List[Dict[str, Any]]) -> None:
        """
        Log Cloudflare cookies for debugging
        
        Args:
            playwright_cookies: List of formatted cookies
        """
        cf_clearance_injected = any(c.get('name') == 'cf_clearance' for c in playwright_cookies)
        cf_bm_injected = any(c.get('name') == '__cf_bm' for c in playwright_cookies)
        
        if self._cloudscraper_cookies:
            if not cf_clearance_injected:
                logger.warning("cf_clearance cookie not in cookies to inject")
            if not cf_bm_injected:
                logger.warning("__cf_bm cookie not found (may still work)")
        
        cf_cookies_to_inject: List[str] = []
        for c in playwright_cookies:
            cookie_name = c.get('name')
            if isinstance(cookie_name, str):
                name_lower = cookie_name.lower()
                if 'cf' in name_lower or cookie_name.startswith('__cf'):
                    cf_cookies_to_inject.append(cookie_name)
        
        if cf_cookies_to_inject:
            logger.debug(f"Cloudflare cookies to inject: {cf_cookies_to_inject}")
    
    def _verify_cookies_in_context(self, context: 'BrowserContext') -> None:
        """
        Verify that cookies were successfully injected into context
        
        Args:
            context: Playwright browser context
        """
        try:
            context_cookies = context.cookies()
            context_cf_cookies = [
                c.get('name') for c in context_cookies 
                if 'cf' in c.get('name', '').lower() or c.get('name', '').startswith('__cf')
            ]
            
            if context_cf_cookies:
                logger.debug(f"Verified Cloudflare cookies in context: {context_cf_cookies}")
            else:
                logger.warning("No Cloudflare cookies found in context after injection")
        except Exception as e:
            logger.warning(f"Failed to verify cookies in context: {e}")
    
    def _inject_cookies_individually(
        self, 
        context: 'BrowserContext',
        playwright_cookies: List[Dict[str, Any]]
    ) -> None:
        """
        Fallback: Inject cookies one by one if batch injection fails
        
        Args:
            context: Playwright browser context
            playwright_cookies: List of formatted cookies
        """
        injected_count = 0
        failed_cookies = []
        
        for cookie in playwright_cookies:
            try:
                # Type ignore needed because Playwright's SetCookieParam type is more specific
                # but our dict format is compatible at runtime
                context.add_cookies([cookie])  # type: ignore[list-item]
                injected_count += 1
            except Exception as cookie_error:
                cookie_name = cookie.get('name', 'unknown')
                failed_cookies.append(cookie_name)
                
                # Only log critical cookies (cf_clearance) as warnings
                if cookie_name == 'cf_clearance':
                    logger.warning(f"Failed to inject cf_clearance: {cookie_error}")
        
        # Only log summary if there are unexpected failures (not __Host-GAPS)
        critical_failures = [c for c in failed_cookies if c not in ['__Host-GAPS']]
        if critical_failures:
            logger.debug(f"Failed to inject {len(critical_failures)} cookies: {critical_failures[:5]}")
        
        if injected_count > 0:
            logger.debug(f"Injected {injected_count}/{len(playwright_cookies)} cookies successfully")
            self._cookies_injected = True
        
        # Verify after individual injection
        self._verify_cookies_in_context(context)
    
    def reset_injection_state(self) -> None:
        """Reset injection state (useful for re-authentication)"""
        self._cookies_injected = False
        self._formatted_cookies_cache = None
    
    def get_current_cookies(self) -> Dict[str, str]:
        """
        Get currently stored cookies (merged)
        
        Returns:
            Dictionary of all cookies
        """
        return self._merge_cookies()
