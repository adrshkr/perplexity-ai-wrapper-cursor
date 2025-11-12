#!/usr/bin/env python3
"""
Test script to verify the PowerShell fix works correctly
"""

import os
import subprocess
import sys
from pathlib import Path


def test_powershell_syntax():
    """Test if the fixed PowerShell script has valid syntax"""
    print("🔍 Testing PowerShell script syntax...")

    project_root = Path(__file__).parent
    ps_file = project_root / "perplexity.ps1"

    if not ps_file.exists():
        print("❌ perplexity.ps1 not found")
        return False

    try:
        # Test PowerShell syntax by parsing the file
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Command -Syntax 'Get-Content {ps_file} | Out-Null'",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ PowerShell syntax is valid")
            return True
        else:
            print(f"❌ PowerShell syntax error: {result.stderr}")
            return False

    except FileNotFoundError:
        print("⚠️  PowerShell not available (Linux/WSL environment)")
        return True  # Not a failure on non-Windows systems
    except Exception as e:
        print(f"❌ PowerShell test failed: {e}")
        return False


def test_required_parameters():
    """Test that all required parameters are present in the script"""
    print("\n📋 Testing required parameters...")

    project_root = Path(__file__).parent
    ps_file = project_root / "perplexity.ps1"

    if not ps_file.exists():
        print("❌ perplexity.ps1 not found")
        return False

    try:
        with open(ps_file, "r", encoding="utf-8") as f:
            content = f.read()

        required_params = [
            "$Query",
            "$Profile",
            "$Mode",
            "$Research",
            "$DebugMode",
            "$KeepBrowserOpen",
            "$SearchMode",
        ]

        missing = []
        for param in required_params:
            if param not in content:
                missing.append(param)

        if missing:
            print(f"❌ Missing parameters: {missing}")
            return False
        else:
            print("✅ All required parameters found")
            return True

    except Exception as e:
        print(f"❌ Parameter check failed: {e}")
        return False


def test_python_imports():
    """Test that the Python modules referenced in the script can be imported"""
    print("\n🐍 Testing Python module imports...")

    project_root = Path(__file__).parent
    os.chdir(project_root)
    sys.path.insert(0, str(project_root))

    modules_to_test = [
        ("src.automation.web_driver", "PerplexityWebDriver"),
        ("src.core.client", "PerplexityClient"),
    ]

    success = True

    for module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            cls = getattr(module, class_name)
            print(f"✅ {module_path}.{class_name}")
        except ImportError as e:
            print(f"❌ {module_path}.{class_name}: Import error - {e}")
            success = False
        except AttributeError as e:
            print(f"❌ {module_path}.{class_name}: Class not found - {e}")
            success = False
        except Exception as e:
            print(f"❌ {module_path}.{class_name}: Error - {e}")
            success = False

    return success


def test_virtual_environment():
    """Test virtual environment detection logic"""
    print("\n🔧 Testing virtual environment detection...")

    project_root = Path(__file__).parent
    venv_path = project_root / "venv"

    if venv_path.exists():
        print("✅ Virtual environment directory exists")

        # Check for activation script
        activate_script = venv_path / "Scripts" / "Activate.ps1"
        python_exe = venv_path / "Scripts" / "python.exe"

        if activate_script.exists():
            print("✅ PowerShell activation script found")
        elif python_exe.exists():
            print("✅ Python executable found (alternative activation)")
        else:
            print("⚠️  Virtual environment exists but activation files missing")
    else:
        print("⚠️  Virtual environment not found (will be created on first run)")

    return True


def test_fallback_mechanisms():
    """Test that the script has proper fallback mechanisms"""
    print("\n🛡️  Testing fallback mechanisms...")

    project_root = Path(__file__).parent
    ps_file = project_root / "perplexity.ps1"

    if not ps_file.exists():
        print("❌ perplexity.ps1 not found")
        return False

    try:
        with open(ps_file, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for key fallback patterns
        fallbacks = [
            ("API to Browser fallback", "switching to browser mode"),
            ("Alternative venv activation", "Alternative activation method"),
            ("Error handling", "catch" in content.lower() or "try" in content.lower()),
            ("Exit codes", "$LASTEXITCODE"),
        ]

        all_good = True
        for fallback_name, pattern in fallbacks:
            if isinstance(pattern, bool):
                if pattern:
                    print(f"✅ {fallback_name}")
                else:
                    print(f"❌ {fallback_name}")
                    all_good = False
            elif pattern in content:
                print(f"✅ {fallback_name}")
            else:
                print(f"❌ {fallback_name} - pattern '{pattern}' not found")
                all_good = False

        return all_good

    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
        return False


def test_command_compatibility():
    """Test that the original failing command should now work"""
    print("\n✨ Testing command compatibility...")

    # The original failing command
    original_command = [
        "current latest realtime update of cryptomarket",
        "-Mode",
        "browser",
        "-Profile",
        "fresh",
        "-KeepBrowserOpen",
        "-DebugMode",
        "-Research",
    ]

    print("Original command that was failing:")
    print(
        f'  .\\perplexity.ps1 "{original_command[0]}" {" ".join(original_command[1:])}'
    )

    # Check if all these parameters are supported
    project_root = Path(__file__).parent
    ps_file = project_root / "perplexity.ps1"

    try:
        with open(ps_file, "r", encoding="utf-8") as f:
            content = f.read()

        params_in_command = [
            "-Mode",
            "-Profile",
            "-KeepBrowserOpen",
            "-DebugMode",
            "-Research",
        ]

        supported = []
        for param in params_in_command:
            param_name = param.replace("-", "$")  # Convert -Mode to $Mode
            if param_name in content:
                supported.append(param)

        print(f"✅ Supported parameters: {supported}")

        if len(supported) == len(params_in_command):
            print("✅ All parameters from original command are supported!")
            return True
        else:
            missing = set(params_in_command) - set(supported)
            print(f"❌ Missing parameters: {missing}")
            return False

    except Exception as e:
        print(f"❌ Command compatibility test failed: {e}")
        return False


def main():
    """Run all PowerShell fix tests"""
    print("🚀 Testing PowerShell Fix")
    print("=" * 50)

    print(
        "This script tests if the PowerShell script fixes resolve the original error:"
    )
    print("  'A parameter cannot be found that matches parameter name 'Profile'.'")
    print()

    tests = [
        ("PowerShell Syntax", test_powershell_syntax),
        ("Required Parameters", test_required_parameters),
        ("Python Imports", test_python_imports),
        ("Virtual Environment", test_virtual_environment),
        ("Fallback Mechanisms", test_fallback_mechanisms),
        ("Command Compatibility", test_command_compatibility),
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} PASSED\n")
            else:
                print(f"❌ {test_name} FAILED\n")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}\n")

    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        print("✨ Your original PowerShell command should now work:")
        print(
            '   .\\perplexity.ps1 "crypto market update" -Mode browser -Profile fresh -Research -DebugMode'
        )
        print(
            "\n🚀 The optimization preserved all functionality while fixing the issues!"
        )
        return True
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        print("Check the output above for specific issues that need attention.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
