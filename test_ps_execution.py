#!/usr/bin/env python3
"""
PowerShell Script Execution Test
Comprehensive test that mimics the actual PowerShell script execution flow
to identify issues before running the real script.
"""

import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path


def test_environment_setup():
    """Test the environment setup phase"""
    print("🔍 TESTING ENVIRONMENT SETUP")
    print("=" * 50)

    # Test 1: Check if we're in the right directory
    if not Path("perplexity.ps1").exists():
        print("❌ perplexity.ps1 not found in current directory")
        return False
    print("✅ PowerShell script found")

    # Test 2: Check virtual environment
    if os.environ.get("VIRTUAL_ENV"):
        print(f"✅ Virtual environment active: {os.environ['VIRTUAL_ENV']}")
    else:
        print("⚠️  No VIRTUAL_ENV detected - might be okay if using system Python")

    # Test 3: Check Python executable
    try:
        result = subprocess.run(
            [sys.executable, "--version"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print(f"✅ Python available: {result.stdout.strip()}")
        else:
            print(f"❌ Python check failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Python execution failed: {e}")
        return False

    return True


def test_dependency_imports():
    """Test critical dependency imports"""
    print("\n🔍 TESTING DEPENDENCY IMPORTS")
    print("=" * 50)

    # Test core imports that PowerShell script relies on
    test_imports = [
        "src.automation.web_driver",
        "httpx",
        "playwright",
    ]

    all_good = True

    for module in test_imports:
        try:
            if module == "src.automation.web_driver":
                # Special test for the main class
                from src.automation.web_driver import PerplexityWebDriver

                print(f"✅ {module}.PerplexityWebDriver imported successfully")
            else:
                __import__(module)
                print(f"✅ {module} imported successfully")
        except ImportError as e:
            print(f"❌ {module} import failed: {e}")
            all_good = False
        except Exception as e:
            print(f"❌ {module} unexpected error: {e}")
            all_good = False

    return all_good


def test_driver_initialization():
    """Test PerplexityWebDriver initialization"""
    print("\n🔍 TESTING DRIVER INITIALIZATION")
    print("=" * 50)

    try:
        from src.automation.web_driver import PerplexityWebDriver

        # Test initialization without starting browser
        driver = PerplexityWebDriver(headless=True, stealth_mode=True)
        print("✅ PerplexityWebDriver initialized successfully")

        # Test required methods exist
        required_methods = ["start", "navigate_to_perplexity", "search", "close"]
        for method in required_methods:
            if hasattr(driver, method) and callable(getattr(driver, method)):
                print(f"✅ Method {method} available")
            else:
                print(f"❌ Method {method} missing or not callable")
                return False

        return True

    except Exception as e:
        print(f"❌ Driver initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_python_script_generation():
    """Test the Python script generation logic from PowerShell"""
    print("\n🔍 TESTING PYTHON SCRIPT GENERATION")
    print("=" * 50)

    # Simulate PowerShell variable values
    headless_value = "True"
    keep_open_value = "False"
    debug_value = "True"
    escaped_query = "Test crypto market analysis with 'quotes' and special chars"
    search_mode = "research"
    cookie_profile = "fresh"

    print("Simulating PowerShell variable conversion:")
    print(f"  headless_value = {headless_value}")
    print(f"  keep_open_value = {keep_open_value}")
    print(f"  debug_value = {debug_value}")
    print(f"  escaped_query = {escaped_query}")
    print(f"  search_mode = {search_mode}")
    print(f"  cookie_profile = {cookie_profile}")

    # Python script template (copied from PowerShell script)
    python_script_template = '''import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, ".")

def main():
    try:
        from src.automation.web_driver import PerplexityWebDriver

        # Configuration from PowerShell
        headless = HEADLESS_VALUE
        keep_open = KEEP_OPEN_VALUE
        debug_mode = DEBUG_VALUE
        query = """QUERY_VALUE"""
        search_mode = "SEARCH_MODE_VALUE"
        cookie_profile = "COOKIE_PROFILE_VALUE"

        if debug_mode:
            print(f"Debug: Query = {query}")
            print(f"Debug: Search Mode = {search_mode}")
            print(f"Debug: Cookie Profile = {cookie_profile}")
            print(f"Debug: Headless = {headless}")
            print(f"Debug: Keep Open = {keep_open}")

        print("TEST: Would initialize browser driver here")
        print("TEST: Would start browser here")
        print("TEST: Would navigate to Perplexity here")
        print("TEST: Would perform search here")
        print("TEST: Search simulation completed successfully")

        return 0

    except Exception as e:
        print(f"Error: {e}")
        if debug_mode:
            print("\\nFull traceback:")
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
'''

    # Apply replacements (like PowerShell script does)
    python_script = python_script_template.replace("HEADLESS_VALUE", headless_value)
    python_script = python_script.replace("KEEP_OPEN_VALUE", keep_open_value)
    python_script = python_script.replace("DEBUG_VALUE", debug_value)
    python_script = python_script.replace("QUERY_VALUE", escaped_query)
    python_script = python_script.replace("SEARCH_MODE_VALUE", search_mode)
    python_script = python_script.replace("COOKIE_PROFILE_VALUE", cookie_profile)

    print("✅ Python script template replacement completed")

    # Test the generated script
    try:
        temp_script = os.path.join(
            tempfile.gettempdir(),
            f"test_perplexity_search_{random.randint(1000, 9999)}.py",
        )

        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(python_script)

        print(f"✅ Temporary script created: {temp_script}")

        # Execute the test script
        result = subprocess.run(
            [sys.executable, temp_script], capture_output=True, text=True, timeout=30
        )

        print(f"Script execution result:")
        print(f"  Return code: {result.returncode}")
        print(f"  Output: {result.stdout}")
        if result.stderr:
            print(f"  Errors: {result.stderr}")

        # Cleanup
        if os.path.exists(temp_script):
            os.remove(temp_script)
            print("✅ Temporary script cleaned up")

        return result.returncode == 0

    except Exception as e:
        print(f"❌ Script generation test failed: {e}")
        return False


def test_powershell_parameters():
    """Test PowerShell parameter parsing"""
    print("\n🔍 TESTING POWERSHELL PARAMETERS")
    print("=" * 50)

    # Read the actual PowerShell script
    try:
        with open("perplexity.ps1", "r", encoding="utf-8") as f:
            content = f.read()

        # Check for required parameters
        required_params = {
            "Query": "Mandatory query parameter",
            "CookieProfile": "Cookie profile parameter",
            "Mode": "Execution mode parameter",
            "SearchMode": "Search mode parameter",
            "DebugMode": "Debug switch parameter",
            "KeepBrowserOpen": "Keep browser open parameter",
            "ExportMarkdown": "Export markdown parameter",
        }

        all_params_found = True
        for param, description in required_params.items():
            if f"${param}" in content:
                print(f"✅ {param}: {description}")
            else:
                print(f"❌ {param}: {description} - MISSING")
                all_params_found = False

        return all_params_found

    except Exception as e:
        print(f"❌ PowerShell parameter test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🧪 POWERSHELL SCRIPT EXECUTION TEST")
    print("=" * 60)
    print("Testing all components before actual PowerShell execution")
    print("=" * 60)

    tests = [
        ("Environment Setup", test_environment_setup),
        ("Dependency Imports", test_dependency_imports),
        ("Driver Initialization", test_driver_initialization),
        ("Python Script Generation", test_python_script_generation),
        ("PowerShell Parameters", test_powershell_parameters),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n❌ {test_name} test crashed: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ PowerShell script should execute successfully")
        print("\n💡 Try running your PowerShell command now:")
        print(
            '   .\\perplexity.ps1 "your query" -CookieProfile fresh -Mode browser -SearchMode research -DebugMode'
        )
    else:
        print("\n❌ SOME TESTS FAILED!")
        print("🔧 Fix the issues above before running PowerShell script")
        print("💡 The most common issues:")
        print("   - Missing dependencies: pip install -e .")
        print("   - Wrong directory: ensure you're in the project root")
        print("   - Virtual environment: activate venv if needed")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
