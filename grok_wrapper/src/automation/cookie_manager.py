"""
Cookie management for Grok authentication
"""
import json
import logging
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CookieManager:
    """Manage Grok authentication cookies"""
    
    def __init__(self, cookies_dir: Optional[str] = None):
        """
        Initialize cookie manager
        
        Args:
            cookies_dir: Directory to store cookie profiles (default: .grok_cookies)
        """
        if cookies_dir:
            self.cookies_dir = Path(cookies_dir)
        else:
            self.cookies_dir = Path.home() / ".grok_cookies"
        
        self.cookies_dir.mkdir(parents=True, exist_ok=True)
    
    def save_cookies(self, cookies: Dict[str, str], name: str = "default") -> None:
        """
        Save cookies to a profile
        
        Args:
            cookies: Dictionary of cookie name -> value
            name: Profile name
        """
        profile_path = self.cookies_dir / f"{name}.json"
        
        with open(profile_path, 'w') as f:
            json.dump(cookies, f, indent=2)
        
        logger.info(f"Saved cookies to profile: {name}")
    
    def load_cookies(self, name: str = "default") -> Optional[Dict[str, str]]:
        """
        Load cookies from a profile
        
        Args:
            name: Profile name
        
        Returns:
            Dictionary of cookies or None if not found
        """
        profile_path = self.cookies_dir / f"{name}.json"
        
        if not profile_path.exists():
            logger.debug(f"Cookie profile not found: {name}")
            return None
        
        try:
            with open(profile_path, 'r') as f:
                cookies = json.load(f)
            logger.debug(f"Loaded cookies from profile: {name}")
            return cookies
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return None
    
    def delete_profile(self, name: str) -> bool:
        """
        Delete a cookie profile
        
        Args:
            name: Profile name
        
        Returns:
            True if deleted, False if not found
        """
        profile_path = self.cookies_dir / f"{name}.json"
        
        if profile_path.exists():
            profile_path.unlink()
            logger.info(f"Deleted cookie profile: {name}")
            return True
        
        return False
    
    def list_profiles(self) -> List[str]:
        """
        List all cookie profiles
        
        Returns:
            List of profile names
        """
        profiles = []
        for file in self.cookies_dir.glob("*.json"):
            profiles.append(file.stem)
        return sorted(profiles)
    
    def extract_from_browser(self, browser_cookies: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extract Grok cookies from browser cookies list
        
        Args:
            browser_cookies: List of cookie dictionaries from browser
        
        Returns:
            Dictionary of Grok cookies
        """
        grok_cookies = {}
        
        for cookie in browser_cookies:
            domain = cookie.get("domain", "")
            if "grok.com" in domain or "x.ai" in domain:
                name = cookie.get("name")
                value = cookie.get("value")
                if name and value:
                    grok_cookies[name] = value
        
        logger.debug(f"Extracted {len(grok_cookies)} Grok cookies")
        return grok_cookies
    
    @staticmethod
    def extract_from_chrome(profile_path: Optional[str] = None) -> Dict[str, str]:
        """
        Extract Grok cookies from Chrome using browser_cookie3
        
        Args:
            profile_path: Custom Chrome profile path
        
        Returns:
            Cookie dictionary
        """
        try:
            import browser_cookie3
        except ImportError:
            raise ImportError("browser_cookie3 not installed. Run: pip install browser-cookie3")
        
        cookie_dict = {}
        
        # Try different methods to get Chrome cookies
        try:
            # Method 1: Default Chrome profile
            cookies = browser_cookie3.chrome(domain_name='grok.com')
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            
            # Also get x.ai cookies (for authentication)
            try:
                xai_cookies = browser_cookie3.chrome(domain_name='x.ai')
                for cookie in xai_cookies:
                    cookie_dict[cookie.name] = cookie.value
            except Exception:
                pass
            
            if cookie_dict:
                logger.info(f"Extracted {len(cookie_dict)} cookies from default Chrome profile")
                return cookie_dict
        except Exception as e:
            logger.debug(f"Default method failed: {e}")
        
        # Method 2: Try with custom profile path
        if not profile_path:
            username = os.getenv('USERNAME') or os.getenv('USER')
            if username:
                default_paths = []
                if platform.system() == 'Windows':
                    default_paths = [
                        f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Default",
                        f"C:\\Users\\{username}\\AppData\\Local\\Google\\Chrome\\User Data\\Profile 1",
                    ]
                elif platform.system() == 'Linux':
                    wsl_windows_path = f"/mnt/c/Users/{username}/AppData/Local/Google/Chrome/User Data/Default"
                    if os.path.exists(wsl_windows_path):
                        default_paths.append(wsl_windows_path)
                    default_paths.extend([
                        os.path.expanduser("~/.config/google-chrome/Default"),
                        os.path.expanduser("~/.config/google-chrome/Profile 1"),
                        os.path.expanduser("~/.config/chromium/Default"),
                        os.path.expanduser("~/.config/chromium/Profile 1"),
                    ])
                
                for path in default_paths:
                    if os.path.exists(path):
                        try:
                            cookies = browser_cookie3.chrome(
                                domain_name='grok.com',
                                cookie_file=os.path.join(path, 'Cookies')
                            )
                            for cookie in cookies:
                                cookie_dict[cookie.name] = cookie.value
                            
                            # Also get x.ai cookies
                            try:
                                xai_cookies = browser_cookie3.chrome(
                                    domain_name='x.ai',
                                    cookie_file=os.path.join(path, 'Cookies')
                                )
                                for cookie in xai_cookies:
                                    cookie_dict[cookie.name] = cookie.value
                            except Exception:
                                pass
                            
                            if cookie_dict:
                                logger.info(f"Extracted {len(cookie_dict)} cookies from {path}")
                                return cookie_dict
                        except Exception:
                            continue
        
        # Method 3: Try with provided profile path
        if profile_path:
            try:
                cookie_file = os.path.join(profile_path, 'Cookies')
                if os.path.exists(cookie_file):
                    cookies = browser_cookie3.chrome(
                        domain_name='grok.com',
                        cookie_file=cookie_file
                    )
                    for cookie in cookies:
                        cookie_dict[cookie.name] = cookie.value
                    
                    # Also get x.ai cookies
                    try:
                        xai_cookies = browser_cookie3.chrome(
                            domain_name='x.ai',
                            cookie_file=cookie_file
                        )
                        for cookie in xai_cookies:
                            cookie_dict[cookie.name] = cookie.value
                    except Exception:
                        pass
                    
                    if cookie_dict:
                        return cookie_dict
            except Exception:
                pass
        
        if not cookie_dict:
            raise Exception(
                "Failed to find Chrome cookies. Make sure:\n"
                "1. Chrome is completely closed (check Task Manager)\n"
                "2. You have visited grok.com and are logged in\n"
                "3. Try using --profile-path option with your Chrome profile path"
            )
        
        return cookie_dict
    
    @staticmethod
    def extract_from_firefox() -> Dict[str, str]:
        """Extract Grok cookies from Firefox"""
        try:
            import browser_cookie3
        except ImportError:
            raise ImportError("browser_cookie3 not installed. Run: pip install browser-cookie3")
        
        cookie_dict = {}
        try:
            # Extract from grok.com
            cookies = browser_cookie3.firefox(domain_name='grok.com')
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            
            # Also get x.ai cookies (for authentication)
            try:
                xai_cookies = browser_cookie3.firefox(domain_name='x.ai')
                for cookie in xai_cookies:
                    cookie_dict[cookie.name] = cookie.value
            except Exception as e:
                logger.debug(f"Could not extract x.ai cookies from Firefox: {e}")
            
            # Also try accounts.x.ai
            try:
                accounts_cookies = browser_cookie3.firefox(domain_name='accounts.x.ai')
                for cookie in accounts_cookies:
                    cookie_dict[cookie.name] = cookie.value
            except Exception:
                pass
            
            if not cookie_dict:
                raise Exception(
                    "No cookies found for grok.com in Firefox. Make sure:\n"
                    "1. Firefox is completely closed\n"
                    "2. You have visited https://grok.com and are logged in\n"
                    "3. Try visiting grok.com in Firefox first"
                )
            
            logger.info(f"Extracted {len(cookie_dict)} cookies from Firefox")
            return cookie_dict
        except Exception as e:
            raise Exception(f"Failed to extract Firefox cookies: {str(e)}")
    
    @staticmethod
    def extract_from_edge() -> Dict[str, str]:
        """Extract Grok cookies from Edge"""
        try:
            import browser_cookie3
        except ImportError:
            raise ImportError("browser_cookie3 not installed. Run: pip install browser-cookie3")
        
        cookie_dict = {}
        try:
            cookies = browser_cookie3.edge(domain_name='grok.com')
            for cookie in cookies:
                cookie_dict[cookie.name] = cookie.value
            
            # Also get x.ai cookies
            try:
                xai_cookies = browser_cookie3.edge(domain_name='x.ai')
                for cookie in xai_cookies:
                    cookie_dict[cookie.name] = cookie.value
            except Exception:
                pass
        except Exception as e:
            raise Exception(f"Failed to extract Edge cookies: {str(e)}")
        
        return cookie_dict
    
    def auto_extract(self, browser: str = 'chrome') -> Optional[Dict[str, str]]:
        """
        Automatically extract cookies from specified browser
        
        Args:
            browser: Browser name (chrome, firefox, edge)
        
        Returns:
            Cookie dictionary or None
        """
        try:
            if browser == 'chrome':
                return self.extract_from_chrome()
            elif browser == 'firefox':
                return self.extract_from_firefox()
            elif browser == 'edge':
                return self.extract_from_edge()
            else:
                logger.error(f"Unsupported browser: {browser}")
                return None
        except Exception as e:
            logger.error(f"Failed to extract cookies from {browser}: {e}")
            return None

