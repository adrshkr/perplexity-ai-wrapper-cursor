"""
Test script to verify refactored web_driver.py preserves all functionality

This tests:
1. Imports work correctly
2. Classes can be instantiated
3. Components are properly integrated
4. Key methods exist and are callable
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all imports work"""
    print("Testing imports...")
    try:
        from src.automation import PerplexityWebDriver, TabManager, CookieInjector, CloudflareHandler
        print("  ✓ All imports successful")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_component_instantiation():
    """Test that all components can be instantiated"""
    print("\nTesting component instantiation...")
    
    try:
        from src.automation.tab_manager import TabManager
        from src.automation.cookie_injector import CookieInjector
        from src.automation.cloudflare_handler import CloudflareHandler
        
        # Note: TabManager requires a BrowserContext, so we just check it's importable
        print("  ✓ TabManager class available")
        
        # Test CookieInjector
        cookie_injector = CookieInjector()
        print("  ✓ CookieInjector instantiated")
        
        # Test CloudflareHandler
        cloudflare_handler = CloudflareHandler()
        print("  ✓ CloudflareHandler instantiated")
        
        return True
    except Exception as e:
        print(f"  ✗ Component instantiation failed: {e}")
        return False


def test_webdriver_initialization():
    """Test that PerplexityWebDriver can be initialized"""
    print("\nTesting PerplexityWebDriver initialization...")
    
    try:
        from src.automation import PerplexityWebDriver
        
        # Test initialization without starting browser
        driver = PerplexityWebDriver(headless=True, stealth_mode=True)
        print("  ✓ PerplexityWebDriver instantiated")
        
        # Check that components are properly initialized
        assert hasattr(driver, 'cookie_injector'), "Missing cookie_injector"
        assert hasattr(driver, 'cloudflare_handler'), "Missing cloudflare_handler"
        print("  ✓ Components properly initialized")
        
        # Check that key methods exist
        assert hasattr(driver, 'set_cookies'), "Missing set_cookies method"
        assert hasattr(driver, 'start'), "Missing start method"
        assert hasattr(driver, 'navigate_to_perplexity'), "Missing navigate_to_perplexity method"
        assert hasattr(driver, 'search'), "Missing search method"
        assert hasattr(driver, 'close'), "Missing close method"
        print("  ✓ All key methods present")
        
        return True
    except Exception as e:
        print(f"  ✗ WebDriver initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cookie_injector_methods():
    """Test CookieInjector methods"""
    print("\nTesting CookieInjector methods...")
    
    try:
        from src.automation.cookie_injector import CookieInjector
        
        injector = CookieInjector()
        
        # Test set_login_cookies
        test_cookies = {'test': 'value'}
        injector.set_login_cookies(test_cookies)
        print("  ✓ set_login_cookies works")
        
        # Test set_cloudscraper_cookies
        injector.set_cloudscraper_cookies({'cf_clearance': 'test'})
        print("  ✓ set_cloudscraper_cookies works")
        
        # Test should_inject_cookies
        result = injector.should_inject_cookies(None)
        assert isinstance(result, bool), "should_inject_cookies should return bool"
        print("  ✓ should_inject_cookies works")
        
        # Test get_current_cookies
        cookies = injector.get_current_cookies()
        assert isinstance(cookies, dict), "get_current_cookies should return dict"
        print("  ✓ get_current_cookies works")
        
        return True
    except Exception as e:
        print(f"  ✗ CookieInjector method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_cloudflare_handler_methods():
    """Test CloudflareHandler methods"""
    print("\nTesting CloudflareHandler methods...")
    
    try:
        from src.automation.cloudflare_handler import CloudflareHandler
        
        handler = CloudflareHandler()
        
        # Test get_user_agent
        ua = handler.get_user_agent()
        print(f"  ✓ get_user_agent works (returned: {type(ua)})")
        
        # Test get_cookies
        cookies = handler.get_cookies()
        print(f"  ✓ get_cookies works (returned: {type(cookies)})")
        
        # Note: solve_challenge requires network and cloudscraper, so we don't test it
        print("  ⚠ Skipping solve_challenge (requires network)")
        
        return True
    except Exception as e:
        print(f"  ✗ CloudflareHandler method test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_integration():
    """Test that components work together"""
    print("\nTesting component integration...")
    
    try:
        from src.automation import PerplexityWebDriver
        
        driver = PerplexityWebDriver(headless=True)
        
        # Test set_cookies flows to cookie_injector
        test_cookies = {'session': 'test123'}
        driver.set_cookies(test_cookies)
        
        # Verify cookies were set in injector
        current_cookies = driver.cookie_injector.get_current_cookies()
        assert 'session' in current_cookies, "Cookies not properly passed to injector"
        print("  ✓ set_cookies integration works")
        
        # Test that cookie_injector is used in methods
        assert driver.cookie_injector is not None
        assert driver.cloudflare_handler is not None
        print("  ✓ Components properly integrated")
        
        return True
    except Exception as e:
        print(f"  ✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("="*60)
    print("REFACTORED WEB_DRIVER TEST SUITE")
    print("="*60)
    
    tests = [
        ("Imports", test_imports),
        ("Component Instantiation", test_component_instantiation),
        ("WebDriver Initialization", test_webdriver_initialization),
        ("CookieInjector Methods", test_cookie_injector_methods),
        ("CloudflareHandler Methods", test_cloudflare_handler_methods),
        ("Component Integration", test_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED - Refactoring successful!")
        print("\nOriginal functionality preserved:")
        print("  - All imports work")
        print("  - All components can be instantiated")
        print("  - PerplexityWebDriver properly uses extracted components")
        print("  - Cookie injection flows correctly")
        print("  - Cloudflare handler methods accessible")
        return True
    else:
        print(f"\n✗ {total - passed} test(s) failed - Review needed")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
