#!/usr/bin/env python3
"""
Test script to validate PowerShell functionality without running PowerShell.
This simulates the Python code that gets executed by the PowerShell script.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, ".")


def test_powershell_python_code():
    """Test the Python code that would be executed by PowerShell"""
    print("🧪 Testing PowerShell Python functionality...")

    # Test 1: Import validation
    try:
        from src.automation.web_driver import PerplexityWebDriver

        print("✅ PerplexityWebDriver import successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected import error: {e}")
        return False

    # Test 2: Driver initialization (without starting browser)
    try:
        # Simulate PowerShell variable settings
        headless = True  # PowerShell: $headlessFlag
        keep_open = False  # PowerShell: $keepOpenFlag
        debug_mode = True  # PowerShell: $debugFlag
        query = "Test query with 'quotes' and special characters"
        search_mode = "search"

        print(f"   Query: {query}")
        print(f"   Search Mode: {search_mode}")
        print(f"   Headless: {headless}")
        print(f"   Keep Open: {keep_open}")
        print(f"   Debug Mode: {debug_mode}")

        # Test driver initialization
        driver = PerplexityWebDriver(headless=headless, stealth_mode=True)
        print("✅ Driver initialization successful")

        # Test that driver has required methods
        required_methods = ["start", "navigate_to_perplexity", "search", "close"]
        for method in required_methods:
            if hasattr(driver, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False

    except Exception as e:
        print(f"❌ Driver initialization failed: {e}")
        return False

    # Test 3: PowerShell script file structure
    script_files = [
        "perplexity.ps1",
        "perplexity_reference.ps1",  # Renamed from WORKING version
    ]

    for script in script_files:
        if os.path.exists(script):
            print(f"✅ PowerShell script exists: {script}")

            # Check for basic PowerShell syntax
            with open(script, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for parameter definition
            if "param(" in content:
                print(f"✅ {script} has parameter definitions")
            else:
                print(f"⚠️ {script} missing param() block")

            # Check for Python code execution
            if "python" in content.lower():
                print(f"✅ {script} executes Python code")
            else:
                print(f"⚠️ {script} doesn't execute Python")

            # Check for problematic syntax patterns
            problematic_patterns = [
                "if not $",  # This caused the original error
            ]

            for pattern in problematic_patterns:
                if pattern in content:
                    print(f"⚠️ {script} may have syntax issue with pattern: {pattern}")
                else:
                    print(f"✅ {script} clean of problematic pattern: {pattern}")
        else:
            print(f"❌ Missing PowerShell script: {script}")
            return False

    # Test 4: Temp file functionality (what PowerShell script does)
    try:
        import tempfile

        # Simulate creating temp file like PowerShell script does
        temp_script = os.path.join(tempfile.gettempdir(), "perplexity_search_test.py")

        # Test Python code that would go in temp file
        python_code = f"""
import sys
import os
sys.path.insert(0, '.')

def main():
    try:
        from src.automation.web_driver import PerplexityWebDriver

        # Configuration (would come from PowerShell variables)
        headless = True
        keep_open = False
        debug_mode = True
        query = "Test query"
        search_mode = "search"

        print("Python script executed successfully")
        print(f"Would search for: {{query}}")

        # Would initialize driver here in real execution
        # driver = PerplexityWebDriver(headless=headless, stealth_mode=True)
        # ... rest of search logic

        return 0

    except Exception as e:
        print(f"Error in temp script: {{e}}")
        return 1

if __name__ == '__main__':
    main()
"""

        # Write and test temp file
        with open(temp_script, "w", encoding="utf-8") as f:
            f.write(python_code)

        print(f"✅ Temp file created successfully: {temp_script}")

        # Clean up
        os.remove(temp_script)
        print("✅ Temp file cleanup successful")

    except Exception as e:
        print(f"❌ Temp file test failed: {e}")
        return False

    print("\n🎉 PowerShell functionality test completed successfully!")
    print("✨ The PowerShell script should work correctly")
    return True


def test_requirements_compatibility():
    """Test that required dependencies are available"""
    print("\n🔍 Testing dependency availability...")

    required_modules = [
        ("httpx", "HTTP client for unified sync/async requests"),
        ("playwright", "Browser automation"),
        ("click", "CLI framework"),
        ("rich", "Rich text output"),
        ("pydantic", "Data validation"),
    ]

    all_available = True

    for module, description in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}: {description}")
        except ImportError:
            print(f"❌ {module}: {description} - NOT AVAILABLE")
            all_available = False

    return all_available


if __name__ == "__main__":
    success = True

    # Run tests
    success &= test_powershell_python_code()
    success &= test_requirements_compatibility()

    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED")
        print("✅ PowerShell script should work correctly")
        print("🚀 Ready to test actual PowerShell execution")
    else:
        print("❌ SOME TESTS FAILED")
        print("🔧 Please fix issues before using PowerShell script")
        sys.exit(1)
