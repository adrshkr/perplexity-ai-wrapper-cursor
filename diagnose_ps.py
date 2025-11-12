#!/usr/bin/env python3
"""
Diagnostic script to check what's wrong with the PowerShell file
"""

import os
import sys
from pathlib import Path


def diagnose_powershell():
    """Diagnose PowerShell script issues"""
    print("🔍 POWERSHELL DIAGNOSTIC TOOL")
    print("=" * 50)

    project_root = Path(__file__).parent
    ps_files = ["perplexity.ps1", "perplexity_clean.ps1", "perplexity_fixed.ps1"]

    for ps_file in ps_files:
        file_path = project_root / ps_file

        print(f"\n📋 ANALYZING: {ps_file}")
        print("-" * 30)

        if not file_path.exists():
            print(f"❌ File not found: {ps_file}")
            continue

        try:
            # Read file in different modes to check for encoding issues
            print(f"📄 File size: {file_path.stat().st_size} bytes")

            # Check UTF-8
            with open(file_path, "r", encoding="utf-8") as f:
                content_utf8 = f.read()
            print(f"✅ UTF-8 readable: {len(content_utf8)} characters")

            # Check for BOM
            with open(file_path, "rb") as f:
                raw_bytes = f.read(10)

            if raw_bytes.startswith(b"\xef\xbb\xbf"):
                print("⚠️  UTF-8 BOM detected")
            elif raw_bytes.startswith(b"\xff\xfe"):
                print("⚠️  UTF-16 LE BOM detected")
            elif raw_bytes.startswith(b"\xfe\xff"):
                print("⚠️  UTF-16 BE BOM detected")
            else:
                print("✅ No BOM detected")

            # Check parameter definitions
            param_block_start = content_utf8.find("param(")
            if param_block_start == -1:
                print("❌ No param() block found!")
                continue

            # Extract param block
            paren_count = 0
            param_end = param_block_start
            for i, char in enumerate(
                content_utf8[param_block_start:], param_block_start
            ):
                if char == "(":
                    paren_count += 1
                elif char == ")":
                    paren_count -= 1
                    if paren_count == 0:
                        param_end = i + 1
                        break

            param_block = content_utf8[param_block_start:param_end]
            print(f"✅ param() block found: {len(param_block)} characters")

            # Check for Profile parameter
            if "$Profile" in param_block:
                print("✅ $Profile parameter found in param block")

                # Show the Profile parameter definition
                lines = param_block.split("\n")
                for i, line in enumerate(lines):
                    if "$Profile" in line:
                        print(f"   Line {i + 1}: {line.strip()}")

                        # Check the next few lines for context
                        for j in range(1, 3):
                            if i + j < len(lines):
                                next_line = lines[i + j].strip()
                                if next_line:
                                    print(f"   Line {i + j + 1}: {next_line}")
            else:
                print("❌ $Profile parameter NOT found in param block!")
                print("🔍 Parameters found:")
                import re

                params = re.findall(r"\$(\w+)", param_block)
                for param in set(params):
                    print(f"   - ${param}")

            # Check for hidden characters around Profile
            profile_pos = content_utf8.find("$Profile")
            if profile_pos != -1:
                start = max(0, profile_pos - 20)
                end = min(len(content_utf8), profile_pos + 50)
                context = content_utf8[start:end]

                print(f"🔍 Context around $Profile:")
                print(f"   '{context}'")

                # Show character codes
                print(f"🔍 Character codes around $Profile:")
                for i, char in enumerate(context):
                    if char == "$" and context[i : i + 8] == "$Profile":
                        print(f"   Position {i}: Found $Profile")
                        for j in range(max(0, i - 5), min(len(context), i + 15)):
                            print(f"   {j}: '{context[j]}' (code: {ord(context[j])})")
                        break

            # Check for syntax errors by examining structure
            lines = content_utf8.split("\n")
            print(f"✅ Total lines: {len(lines)}")

            # Find param block lines
            param_start_line = -1
            param_end_line = -1
            for i, line in enumerate(lines):
                if "param(" in line:
                    param_start_line = i
                if param_start_line != -1 and ")" in line and "$" not in line:
                    param_end_line = i
                    break

            if param_start_line != -1 and param_end_line != -1:
                print(
                    f"✅ param block: lines {param_start_line + 1} to {param_end_line + 1}"
                )

                print("📋 Parameter block content:")
                for i in range(param_start_line, min(param_end_line + 1, len(lines))):
                    line_num = i + 1
                    line_content = lines[i].rstrip()
                    print(f"   {line_num:2d}: {line_content}")

                    # Check for issues
                    if "$Profile" in line_content:
                        print(f"   >>> FOUND $Profile on line {line_num}")

        except Exception as e:
            print(f"❌ Error analyzing {ps_file}: {e}")
            import traceback

            traceback.print_exc()

    # Create a working test file
    print(f"\n🛠️  CREATING TEST FILE...")
    test_file = project_root / "test_perplexity.ps1"

    test_content = """# Test PowerShell Script - Clean Version
param(
    [Parameter(Mandatory=$true)]
    [string]$Query,
    [string]$Mode = "browser",
    [string]$Profile = "fresh",
    [switch]$Research,
    [switch]$DebugMode,
    [switch]$KeepBrowserOpen
)

Write-Host "Test script working!" -ForegroundColor Green
Write-Host "Query: $Query" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor Cyan
Write-Host "Profile: $Profile" -ForegroundColor Cyan
Write-Host "Research: $Research" -ForegroundColor Cyan
Write-Host "DebugMode: $DebugMode" -ForegroundColor Cyan
Write-Host "KeepBrowserOpen: $KeepBrowserOpen" -ForegroundColor Cyan
"""

    try:
        with open(test_file, "w", encoding="utf-8", newline="\r\n") as f:
            f.write(test_content)
        print(f"✅ Created test file: {test_file}")
        print(
            '🧪 Test with: .\\test_perplexity.ps1 "test query" -Profile fresh -Research'
        )
    except Exception as e:
        print(f"❌ Failed to create test file: {e}")

    print(f"\n" + "=" * 50)
    print("DIAGNOSTIC COMPLETE")
    print(f"Use the test file to verify PowerShell parameter handling works")


if __name__ == "__main__":
    diagnose_powershell()
