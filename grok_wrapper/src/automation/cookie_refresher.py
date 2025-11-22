"""
Automatic cookie refresh when they expire
"""
import logging
import time
from typing import Dict, Optional
from .cookie_manager import CookieManager
from .web_driver import GrokWebDriver

logger = logging.getLogger(__name__)


class CookieRefresher:
    """Automatically refresh expired cookies"""
    
    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager
    
    def refresh_cookies(
        self,
        profile_name: str,
        headless: bool = True,
        timeout: int = 60
    ) -> Optional[Dict[str, str]]:
        """
        Refresh cookies by opening browser and extracting fresh ones
        
        Args:
            profile_name: Profile name to refresh
            headless: Run browser in headless mode
            timeout: Timeout in seconds
        
        Returns:
            New cookies dictionary or None
        """
        logger.info(f"Refreshing cookies for profile: {profile_name}")
        
        driver = GrokWebDriver(
            headless=headless,
            stealth_mode=True
        )
        
        try:
            driver.start()
            driver.navigate_to_grok()
            
            # Wait a bit for page to load
            time.sleep(2)
            
            # Check if logged in
            if not driver.is_logged_in():
                if headless:
                    logger.warning("Not logged in in headless mode - cannot refresh automatically")
                    return None
                else:
                    logger.info("Waiting for login...")
                    if not driver.wait_for_login(timeout=timeout):
                        logger.warning("Login timeout")
                        return None
            
            # Extract fresh cookies
            new_cookies = driver.get_cookies()
            
            if new_cookies:
                self.cookie_manager.save_cookies(new_cookies, profile_name)
                logger.info(f"Refreshed {len(new_cookies)} cookies for profile: {profile_name}")
                return new_cookies
            else:
                logger.warning("No cookies extracted")
                return None
                
        except Exception as e:
            logger.error(f"Error refreshing cookies: {e}")
            return None
        finally:
            driver.close()
    
    def check_and_refresh_if_needed(
        self,
        profile_name: str,
        test_cookies: Optional[Dict[str, str]] = None,
        auto_refresh: bool = True
    ) -> Optional[Dict[str, str]]:
        """
        Check if cookies are valid and refresh if needed
        
        Args:
            profile_name: Profile name to check
            test_cookies: Cookies to test (if None, loads from profile)
            auto_refresh: Whether to automatically refresh if expired
        
        Returns:
            Valid cookies dictionary or None
        """
        if test_cookies is None:
            test_cookies = self.cookie_manager.load_cookies(profile_name)
        
        if not test_cookies:
            logger.debug("No cookies found")
            if auto_refresh:
                return self.refresh_cookies(profile_name)
            return None
        
        # Try to use cookies - if they fail, refresh
        # This is handled by the client/CLI, so we just return the cookies
        # The actual refresh happens when API calls fail
        return test_cookies

