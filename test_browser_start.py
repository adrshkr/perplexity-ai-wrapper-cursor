"""
Integration test to verify browser start works without errors
This catches issues like missing attributes that unit tests might miss
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_browser_start_without_playwright():
    """Test that browser initialization checks work correctly"""
    print("Testing browser start initialization checks...")
    
    try:
        from src.automation import PerplexityWebDriver
        
        # Create driver instance
        driver = PerplexityWebDriver(headless=True, stealth_mode=True)
        
        # Check all components are initialized
        assert driver.cookie_injector is not None, "cookie_injector not initialized"
        assert driver.cloudflare_handler is not None, "cloudflare_handler not initialized"
        
        # Verify no references to old private attributes exist
        has_old_attrs = any(hasattr(driver, attr) for attr in [
            '_login_cookies',
            '_cloudscraper_cookies', 
            '_cloudscraper_user_agent',
            '_cookies_injected'
        ])
        
        if has_old_attrs:
            print("  ERROR: Found old attribute references that should be in components!")
            for attr in ['_login_cookies', '_cloudscraper_cookies', '_cloudscraper_user_agent', '_cookies_injected']:
                if hasattr(driver, attr):
                    print(f"    - Found: {attr}")
            return False
        
        print("  SUCCESS: No old attributes found")
        print("  SUCCESS: All components properly initialized")
        
        # Try to access methods that previously used old attributes
        # This will catch AttributeError at method call time
        try:
            # This should work - delegates to cloudflare_handler
            ua = driver.cloudflare_handler.get_user_agent()
            print(f"  SUCCESS: cloudflare_handler.get_user_agent() works (returned {type(ua).__name__})")
            
            # This should work - delegates to cookie_injector
            cookies = driver.cookie_injector.get_current_cookies()
            print(f"  SUCCESS: cookie_injector.get_current_cookies() works (returned {type(cookies).__name__})")
            
        except AttributeError as e:
            print(f"  ERROR: Method call failed with AttributeError: {e}")
            return False
        
        print("\nSUCCESS: Browser initialization passes all checks")
        return True
        
    except Exception as e:
        print(f"  ERROR: Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_simulated_start_sequence():
    """Simulate the start() method sequence without actually starting browser"""
    print("\nTesting simulated start sequence...")
    
    try:
        from src.automation import PerplexityWebDriver
        
        driver = PerplexityWebDriver(headless=True)
        
        # Simulate what happens in start() method
        # 1. Check cloudflare_handler
        if not driver.user_data_dir and not driver.cookie_injector.get_current_cookies():
            print("  Would attempt Cloudflare pre-auth (simulated)")
            # This would call: driver.cloudflare_handler.solve_challenge()
            # But we skip it since it requires network
        
        # 2. Check user agent extraction (this is what failed before)
        try:
            ua = driver.cloudflare_handler.get_user_agent()
            print(f"  SUCCESS: User agent extraction works (got {type(ua).__name__})")
        except AttributeError as e:
            print(f"  ERROR: User agent extraction failed: {e}")
            return False
        
        # 3. Check cookie injection
        try:
            # This shouldn't fail even without browser context
            should_inject = driver.cookie_injector.should_inject_cookies(driver.user_data_dir)
            print(f"  SUCCESS: Cookie injection check works (should_inject={should_inject})")
        except AttributeError as e:
            print(f"  ERROR: Cookie injection check failed: {e}")
            return False
        
        print("\nSUCCESS: Start sequence simulation passed")
        return True
        
    except Exception as e:
        print(f"  ERROR: Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    print("="*60)
    print("BROWSER START INTEGRATION TEST")
    print("="*60)
    
    test1 = test_browser_start_without_playwright()
    test2 = test_simulated_start_sequence()
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    if test1 and test2:
        print("SUCCESS: All integration tests passed")
        print("\nThe AttributeError bug has been fixed!")
        print("Browser start should now work correctly.")
        sys.exit(0)
    else:
        print("FAILURE: Some tests failed")
        sys.exit(1)
