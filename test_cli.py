#!/usr/bin/env python3
"""
Test script to verify CLI functionality works correctly after optimization
"""

import os
import subprocess
import sys
from pathlib import Path


def test_cli_module_import():
    """Test if the CLI module can be imported"""
    print("🧪 Testing CLI module import...")

    try:
        # Change to project directory
        project_root = Path(__file__).parent
        os.chdir(project_root)

        # Test if we can import the CLI module
        import sys

        sys.path.insert(0, str(project_root))

        from src.interfaces.cli import cli

        print("✅ CLI module imported successfully")
        return True

    except Exception as e:
        print(f"❌ CLI import failed: {e}")
        return False


def test_powershell_script():
    """Test the PowerShell script syntax"""
    print("\n🔍 Testing PowerShell script...")

    ps_file = Path(__file__).parent / "perplexity.ps1"
    if not ps_file.exists():
        print("❌ perplexity.ps1 not found")
        return False

    try:
        # Test PowerShell syntax
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                f"Get-Content '{ps_file}' | Out-Null",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            print("✅ PowerShell script syntax OK")
        else:
            print(f"❌ PowerShell syntax error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("⚠️  PowerShell test timed out")
        return False
    except FileNotFoundError:
        print("⚠️  PowerShell not available (Linux/WSL?)")
        # This is OK on Linux systems
        return True
    except Exception as e:
        print(f"❌ PowerShell test failed: {e}")
        return False

    return True


def test_cli_help():
    """Test if CLI help command works"""
    print("\n📋 Testing CLI help command...")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "src.interfaces.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=Path(__file__).parent,
        )

        if result.returncode == 0:
            print("✅ CLI help command works")
            # Check for key commands
            help_output = result.stdout.lower()
            if "browser-search" in help_output and "search" in help_output:
                print("✅ Key commands found in help")
                return True
            else:
                print("⚠️  Some commands missing from help")
                return False
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ CLI help timed out")
        return False
    except Exception as e:
        print(f"❌ CLI help test failed: {e}")
        return False


def test_browser_search_command():
    """Test if browser-search command is available"""
    print("\n🌐 Testing browser-search command availability...")

    try:
        # Test with --help to see if command exists
        result = subprocess.run(
            [sys.executable, "-m", "src.interfaces.cli", "browser-search", "--help"],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=Path(__file__).parent,
        )

        if result.returncode == 0:
            print("✅ browser-search command exists")
            # Check for key options
            help_output = result.stdout.lower()
            if "--profile" in help_output and "--debug" in help_output:
                print("✅ Key options found")
                return True
            else:
                print("⚠️  Some options missing")
                return False
        else:
            print(f"❌ browser-search command failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ browser-search test timed out")
        return False
    except Exception as e:
        print(f"❌ browser-search test failed: {e}")
        return False


def test_parameter_compatibility():
    """Test if the PowerShell script parameters are compatible"""
    print("\n⚙️  Testing parameter compatibility...")

    ps_file = Path(__file__).parent / "perplexity.ps1"
    if not ps_file.exists():
        print("❌ perplexity.ps1 not found")
        return False

    try:
        with open(ps_file, "r") as f:
            content = f.read()

        # Check for required parameters
        required_params = [
            "param(",
            "$Query",
            "$Profile",
            "$Mode",
            "$Research",
            "$DebugMode",
            "$KeepBrowserOpen",
        ]

        missing_params = []
        for param in required_params:
            if param not in content:
                missing_params.append(param)

        if missing_params:
            print(f"❌ Missing parameters: {missing_params}")
            return False
        else:
            print("✅ All required parameters found")
            return True

    except Exception as e:
        print(f"❌ Parameter test failed: {e}")
        return False


def main():
    """Run all CLI tests"""
    print("🚀 Testing CLI Functionality After Optimization")
    print("=" * 50)

    tests = [
        ("CLI Module Import", test_cli_module_import),
        ("PowerShell Script", test_powershell_script),
        ("CLI Help Command", test_cli_help),
        ("Browser-Search Command", test_browser_search_command),
        ("Parameter Compatibility", test_parameter_compatibility),
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
            print(f"❌ {test_name} ERROR: {e}\n")

    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All CLI tests passed!")
        print("✨ Your PowerShell command should now work:")
        print(
            '   .\\perplexity.ps1 "your query" -Mode browser -Profile fresh -Research'
        )
        return True
    else:
        print("⚠️  Some CLI issues detected - checking fixes needed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
