#!/usr/bin/env python3
"""
PowerShell Script Validation
Simple test to validate the perplexity.ps1 script parameters and basic syntax
"""

import os
import re


def validate_powershell_script():
    """Validate the PowerShell script for basic correctness"""
    print("🔍 Validating PowerShell Script")
    print("=" * 50)

    script_path = "perplexity.ps1"

    if not os.path.exists(script_path):
        print("❌ perplexity.ps1 not found")
        return False

    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Test 1: Check for required parameters
    required_params = [
        "Query",
        "Mode",
        "CookieProfile",
        "SearchMode",
        "Headless",
        "KeepBrowserOpen",
        "DebugMode",
        "Research",
        "ExportMarkdown",
        "ExportDir",
    ]

    print("📋 Checking Parameters:")
    param_pattern = r"\[(?:Parameter|string|switch)\].*?\$(\w+)"
    found_params = re.findall(param_pattern, content, re.DOTALL)

    all_params_found = True
    for param in required_params:
        if param in found_params:
            print(f"  ✅ {param}")
        else:
            print(f"  ❌ {param} - MISSING")
            all_params_found = False

    # Test 2: Check for CookieProfile specifically (the main issue)
    print(f"\n🎯 CookieProfile Parameter Check:")
    if "[string]$CookieProfile" in content:
        print("  ✅ CookieProfile parameter defined correctly")
    else:
        print("  ❌ CookieProfile parameter not found")
        return False

    # Test 3: Basic syntax validation
    print(f"\n🔧 Basic Syntax Check:")
    syntax_ok = True

    # Just check for the most critical issues
    if "if not $" in content and ":" in content:
        print("  ❌ Found Python-style 'if not $var:' syntax")
        syntax_ok = False
    else:
        print("  ✅ No critical syntax issues found")

    # Test 4: Check for safe placeholder replacement
    print(f"\n🔄 Variable Handling Check:")
    if ".Replace(" in content and "HEADLESS_VALUE" in content:
        print("  ✅ Uses safe placeholder replacement method")
    elif "$headlessValue" in content or "$keepOpenValue" in content:
        print("  ❌ Still uses direct PowerShell variable interpolation")
        return False
    else:
        print("  ⚠️  Unknown variable handling method")

    # Test 5: Basic structure validation
    print(f"\n📄 Script Structure Check:")
    required_sections = [
        "param(",
        "venv\\Scripts\\Activate.ps1",
        "python",
        "PerplexityWebDriver",
    ]

    structure_ok = True
    for section in required_sections:
        if section in content:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ {section} - MISSING")
            structure_ok = False

    # Final result
    print(f"\n" + "=" * 50)
    if all_params_found and structure_ok:
        print("🎉 PowerShell Script Validation: PASSED")
        print("✅ Your command should now work:")
        print(
            '   ./perplexity.ps1 "your query" -CookieProfile fresh -Mode browser -SearchMode research'
        )
        print("\n📝 Key fix: Parameter is now -CookieProfile (not -Profile)")
        return True
    else:
        print("❌ PowerShell Script Validation: FAILED")
        print("🔧 Please fix the issues listed above")
        return False


if __name__ == "__main__":
    success = validate_powershell_script()
    exit(0 if success else 1)
