"""
Connection Manager - Automatic connection setup with fallback strategies
"""
import json
import os
import time
from typing import Optional, Dict
from pathlib import Path

try:
    from ..core.client import PerplexityClient
    from ..auth.cookie_manager import CookieManager
    from ..automation.web_driver import PerplexityWebDriver
    from ..utils.cloudflare_bypass import CloudflareBypass
except ImportError:
    # Fallback for direct imports
    from src.core.client import PerplexityClient
    from src.auth.cookie_manager import CookieManager
    from src.automation.web_driver import PerplexityWebDriver
    try:
        from src.utils.cloudflare_bypass import CloudflareBypass
    except ImportError:
        CloudflareBypass = None


class ConnectionManager:
    """Enhanced connection manager with fallback strategies"""
    
    def __init__(self, verbose: bool = False):
        """
        Initialize connection manager
        
        Args:
            verbose: If True, print detailed connection attempts
        """
        self.cookie_manager = CookieManager()
        self.connection_attempts = []
        self.active_client = None
        self.verbose = verbose
    
    def log_attempt(self, method: str, success: bool, message: str = ""):
        """Log connection attempts"""
        attempt = {
            'method': method,
            'success': success,
            'message': message,
            'timestamp': time.time()
        }
        self.connection_attempts.append(attempt)
        if self.verbose:
            status = "✓" if success else "✗"
            print(f"  {status} {method}: {message}")
    
    def setup_connection(
        self, 
        profile: Optional[str] = None,
        skip_browser_extraction: bool = False,
        skip_web_automation: bool = False
    ) -> Optional[PerplexityClient]:
        """
        Comprehensive connection setup with fallback strategies
        
        Args:
            profile: Specific profile to use (if provided, skips auto-discovery)
            skip_browser_extraction: Skip browser cookie extraction
            skip_web_automation: Skip web automation fallback
        
        Returns:
            PerplexityClient instance or None if all strategies failed
        """
        # If specific profile requested, try it first
        if profile:
            client = self._try_specific_profile(profile)
            if client:
                return client
        
        # Strategy 1: Try existing cookie profiles
        client = self._try_existing_cookies()
        if client:
            return client
        
        # Strategy 2: Try cloudscraper cookie extraction (new, preferred)
        if CloudflareBypass is not None:
            cookies = self.extract_cookies_with_cloudscraper()
            if cookies:
                try:
                    client = PerplexityClient(
                        cookies=cookies,
                        use_cloudflare_bypass=True,
                        cloudflare_stealth=True
                    )
                    # Test the connection
                    # Note: We don't actually make a request here, just create client
                    # The actual test happens when first request is made
                    self.log_attempt("cloudscraper_extraction", True, "Cookies extracted successfully")
                    self.active_client = client
                    return client
                except Exception as e:
                    if self.verbose:
                        self.log_attempt("cloudscraper_extraction", False, f"Client creation failed: {str(e)}")
        
        # Strategy 3: Try browser cookie extraction (if not skipped)
        if not skip_browser_extraction:
            client = self._try_cookie_extraction()
            if client:
                return client
        
        # Strategy 3: Try manual cookie files
        client = self._try_manual_cookies()
        if client:
            return client
        
        # Strategy 4: Use web automation as last resort (if not skipped)
        if not skip_web_automation:
            client = self._try_web_automation()
            if client:
                return client
        
        return None
    
    def _try_specific_profile(self, profile: str) -> Optional[PerplexityClient]:
        """Try loading a specific cookie profile"""
        try:
            cookies = self.cookie_manager.load_cookies(profile)
            if cookies:
                try:
                    # Enable cloudflare bypass by default (same as cloudscraper extraction)
                    client = PerplexityClient(
                        cookies=cookies, 
                        timeout=10,
                        use_cloudflare_bypass=True,
                        cloudflare_stealth=True
                    )
                    # Quick test (but don't fail if test fails - cookies might still work)
                    try:
                        client.search("test")
                    except:
                        pass  # Test failed but cookies might still be valid
                    self.log_attempt(f"Profile '{profile}'", True, f"Loaded {len(cookies)} cookies")
                    return client
                except Exception as e:
                    self.log_attempt(f"Profile '{profile}'", False, str(e))
        except Exception as e:
            self.log_attempt(f"Profile '{profile}'", False, str(e))
        return None
    
    def _try_existing_cookies(self) -> Optional[PerplexityClient]:
        """Try loading existing cookie profiles"""
        if self.verbose:
            print("\n[1/4] Checking existing cookie profiles...")
        
        try:
            profiles = self.cookie_manager.list_profiles()
            if profiles:
                if self.verbose:
                    print(f"  Found profiles: {', '.join(profiles)}")
                
                # Try each profile
                for profile in profiles:
                    try:
                        cookies = self.cookie_manager.load_cookies(profile)
                        if cookies:
                            try:
                                # Enable cloudflare bypass by default (same as cloudscraper extraction)
                                client = PerplexityClient(
                                    cookies=cookies, 
                                    timeout=10,
                                    use_cloudflare_bypass=True,
                                    cloudflare_stealth=True
                                )
                                # Quick test
                                try:
                                    client.search("test")
                                except:
                                    pass  # Test failed but continue
                                self.log_attempt(
                                    f"Existing profile '{profile}'", 
                                    True, 
                                    f"Loaded {len(cookies)} cookies"
                                )
                                return client
                            except Exception as e:
                                self.log_attempt(
                                    f"Profile '{profile}'", 
                                    False, 
                                    str(e)
                                )
                                continue
                    except Exception:
                        continue
            else:
                self.log_attempt("Existing profiles", False, "No profiles found")
                
        except Exception as e:
            self.log_attempt("Existing profiles", False, str(e))
        
        return None
    
    def extract_cookies_with_cloudscraper(self, url: str = "https://www.perplexity.ai") -> Optional[Dict[str, str]]:
        """
        Extract cookies by solving Cloudflare challenge with cloudscraper
        
        Args:
            url: URL to extract cookies from
        
        Returns:
            Dictionary of cookies including cf_clearance, or None if failed
        """
        if CloudflareBypass is None:
            if self.verbose:
                self.log_attempt("cloudscraper_cookie_extraction", False, "cloudscraper not available")
            return None
        
        try:
            if self.verbose:
                self.log_attempt("cloudscraper_cookie_extraction", True, "Attempting to solve Cloudflare challenge...")
            
            bypass = CloudflareBypass(
                browser='chrome',
                use_stealth=True,
                interpreter='js2py',
                debug=False
            )
            
            # Solve challenge
            if bypass.solve_challenge(url):
                cookies = bypass.get_cookies_dict()
                if self.verbose:
                    self.log_attempt("cloudscraper_cookie_extraction", True, f"Extracted {len(cookies)} cookies")
                return cookies
            else:
                if self.verbose:
                    self.log_attempt("cloudscraper_cookie_extraction", False, "Failed to solve Cloudflare challenge")
                return None
        except Exception as e:
            if self.verbose:
                self.log_attempt("cloudscraper_cookie_extraction", False, f"Error: {str(e)}")
            return None
    
    def _try_cookie_extraction(self) -> Optional[PerplexityClient]:
        """Try extracting cookies from browsers"""
        if self.verbose:
            print("\n[2/4] Attempting browser cookie extraction...")
        
        browsers = ['chrome', 'firefox', 'edge']
        
        for browser in browsers:
            try:
                if self.verbose:
                    print(f"  Trying {browser}...")
                cookies = self.cookie_manager.auto_extract(browser=browser)
                if cookies:
                    # Save and test
                    profile_name = f"auto_{browser}"
                    self.cookie_manager.save_cookies(cookies, profile_name)
                    
                    try:
                        # Enable cloudflare bypass by default
                        client = PerplexityClient(
                            cookies=cookies, 
                            timeout=10,
                            use_cloudflare_bypass=True,
                            cloudflare_stealth=True
                        )
                        try:
                            client.search("test")
                        except:
                            pass  # Test failed but continue
                        self.log_attempt(
                            f"Browser extraction ({browser})", 
                            True, 
                            f"Extracted {len(cookies)} cookies"
                        )
                        return client
                    except Exception as e:
                        self.log_attempt(
                            f"Browser extraction ({browser})", 
                            False, 
                            str(e)
                        )
                        continue
                    
            except Exception as e:
                self.log_attempt(
                    f"Browser extraction ({browser})", 
                    False, 
                    str(e)
                )
                continue
        
        return None
    
    def _try_manual_cookies(self) -> Optional[PerplexityClient]:
        """Try manual cookie files"""
        if self.verbose:
            print("\n[3/4] Checking manual cookie files...")
        
        manual_files = ['cookies.json', 'manual_cookies.json', 'pp_cookies.json']
        
        for file in manual_files:
            if os.path.exists(file):
                try:
                    with open(file, 'r') as f:
                        cookies = json.load(f)
                    
                    if cookies:
                        try:
                            # Enable cloudflare bypass by default
                            client = PerplexityClient(
                                cookies=cookies, 
                                timeout=10,
                                use_cloudflare_bypass=True,
                                cloudflare_stealth=True
                            )
                            try:
                                client.search("test")
                            except:
                                pass  # Test failed but continue
                            self.log_attempt(
                                f"Manual file '{file}'", 
                                True, 
                                f"Loaded {len(cookies)} cookies"
                            )
                            return client
                        except Exception as e:
                            self.log_attempt(f"Manual file '{file}'", False, str(e))
                            continue
                            
                except Exception as e:
                    self.log_attempt(f"Manual file '{file}'", False, str(e))
                    continue
        
        return None
    
    def _try_web_automation(self) -> Optional[PerplexityClient]:
        """Use web automation as fallback"""
        if self.verbose:
            print("\n[4/4] Attempting web automation...")
        
        try:
            if self.verbose:
                print("  Starting browser automation...")
            driver = PerplexityWebDriver(headless=False, stealth_mode=True)
            driver.start()
            driver.navigate_to_perplexity()
            
            if self.verbose:
                print("  Please complete any CAPTCHA or login in the browser window...")
                print("  Press Enter when you are logged in and ready to continue...")
            else:
                print("\n[yellow]Browser opened. Please log in, then press Enter...[/yellow]")
            
            input()
            
            # Extract cookies from browser context
            if driver.context:
                try:
                    # Playwright requires URL parameter for cookies()
                    cookies_list = driver.context.cookies(['https://www.perplexity.ai'])
                    auto_cookies = {cookie['name']: cookie['value'] for cookie in cookies_list 
                                  if 'perplexity.ai' in cookie.get('domain', '')}
                    
                    if auto_cookies:
                        self.cookie_manager.save_cookies(auto_cookies, "automation_profile")
                        # Enable cloudflare bypass by default
                        client = PerplexityClient(
                            cookies=auto_cookies,
                            use_cloudflare_bypass=True,
                            cloudflare_stealth=True
                        )
                        
                        self.log_attempt(
                            "Web automation", 
                            True, 
                            f"Extracted {len(auto_cookies)} cookies via automation"
                        )
                        
                        driver.close()
                        return client
                except Exception as e:
                    if self.verbose:
                        print(f"  Warning: Could not extract cookies: {e}")
            
            driver.close()
            
        except Exception as e:
            self.log_attempt("Web automation", False, str(e))
        
        return None
    
    def get_connection_summary(self) -> str:
        """Get summary of connection attempts"""
        successful = [a for a in self.connection_attempts if a['success']]
        failed = [a for a in self.connection_attempts if not a['success']]
        
        summary = f"\nConnection Summary: {len(successful)} successful, {len(failed)} failed"
        if successful:
            summary += f"\nActive method: {successful[-1]['method']}"
        return summary

