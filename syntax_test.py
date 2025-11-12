#!/usr/bin/env python3
"""
Minimal syntax validation test for optimized code
"""

import ast
import sys
from pathlib import Path


def test_file_syntax(file_path):
    """Test if a Python file has valid syntax"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse the file to check syntax
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f"Syntax error: {e}"
    except Exception as e:
        return False, f"Error: {e}"


def main():
    print("🔍 Testing Python syntax after optimization...")

    project_root = Path(__file__).parent

    # Files to test
    files_to_test = [
        "src/core/client.py",
        "src/core/async_client.py",
        "src/core/models.py",
        "src/automation/web_driver.py",
    ]

    passed = 0
    total = 0

    for file_path in files_to_test:
        full_path = project_root / file_path
        total += 1

        if not full_path.exists():
            print(f"❌ {file_path} - File not found")
            continue

        is_valid, error = test_file_syntax(full_path)

        if is_valid:
            print(f"✅ {file_path} - Syntax OK")
            passed += 1
        else:
            print(f"❌ {file_path} - {error}")

    print(f"\n📊 Syntax Test Results: {passed}/{total} files passed")

    if passed == total:
        print("🎉 All files have valid Python syntax!")
        print("✨ Ready to test imports and functionality")
        return True
    else:
        print("⚠️  Fix syntax errors before proceeding")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
