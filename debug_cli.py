#!/usr/bin/env python3
"""
Debug CLI - Identify exact issue with PowerShell command
"""

import os
import sys
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_basic_cli():
    """Test basic CLI functionality"""
    print("🔍 Debug: Testing CLI imports...")

    try:
        # Test if we can import CLI
        from src.interfaces.cli import cli

        print("✅ CLI imported successfully")

        # Test click decorators
        import click

        print("✅ Click available")

        # Test if CLI has browser-search command
        if hasattr(cli, "commands"):
            commands = cli.commands.keys()
            print(f"✅ Available commands: {list(commands)}")

            if "browser-search" in commands:
                print("✅ browser-search command found")
            else:
                print("❌ browser-search command missing")
        else:
            print("⚠️ CLI commands not accessible")

    except ImportError as e:
        print(f"❌ CLI import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ CLI test failed: {e}")
        return False

    return True


def test_powershell_command():
    """Test the exact PowerShell command that's failing"""
    print("\n🔍 Debug: Testing PowerShell command mapping...")

    # Simulate the exact command from PowerShell
    test_args = [
        "browser-search",
        "test query",
        "--profile",
        "fresh",
        "--mode",
        "research",
        "--debug",
        "--keep-browser-open",
    ]

    print(f"Testing args: {test_args}")

    try:
        # Test if we can run the CLI programmatically
        import sys

        from src.interfaces.cli import cli

        # Override sys.argv to test
        old_argv = sys.argv.copy()
        sys.argv = ["cli"] + test_args

        try:
            # Don't actually run, just test if it would parse
            cli.main(standalone_mode=False, args=test_args)
        except SystemExit as e:
            if e.code == 0:
                print("✅ Command would execute successfully")
            else:
                print(f"❌ Command would fail with exit code: {e.code}")
        except Exception as e:
            print(f"⚠️ Command parsing issue: {e}")
        finally:
            sys.argv = old_argv

    except Exception as e:
        print(f"❌ PowerShell command test failed: {e}")
        return False

    return True


def check_dependencies():
    """Check if all required dependencies are available"""
    print("\n🔍 Debug: Checking dependencies...")

    deps = ["click", "rich", "httpx", "playwright", "asyncio"]

    missing = []
    for dep in deps:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} missing")
            missing.append(dep)

    if missing:
        print(f"❌ Missing dependencies: {missing}")
        return False
    else:
        print("✅ All dependencies available")
        return True


def main():
    print("🐛 CLI Debug Tool")
    print("=" * 30)

    print("Testing the exact PowerShell command that's failing:")
    print(
        '.\perplexity.ps1 "query" -Mode browser -Profile fresh -KeepBrowserOpen -DebugMode -Research'
    )
    print()

    tests = [check_dependencies, test_basic_cli, test_powershell_command]

    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 30)
    print("🔍 Debug complete. Check output above for issues.")


if __name__ == "__main__":
    main()
