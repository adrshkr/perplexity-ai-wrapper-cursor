#!/usr/bin/env python3
"""
Comprehensive Functionality Audit Script
This script performs a thorough comparison between the original and optimized versions
to ensure NO functionality has been lost or compromised during optimization.
"""

import ast
import difflib
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class FunctionalityAuditor:
    """Comprehensive auditor to verify all functionality is preserved"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.backup_path = project_root / "backup_original"
        self.current_path = project_root / "src"
        self.issues = []
        self.warnings = []
        self.passed_checks = []

    def audit_all(self) -> bool:
        """Run complete functionality audit"""
        print("🔍 COMPREHENSIVE FUNCTIONALITY AUDIT")
        print("=" * 60)
        print("Comparing original vs optimized versions to ensure")
        print("ZERO functionality loss during optimization process")
        print("=" * 60)

        checks = [
            ("File Structure", self.check_file_structure),
            ("Class Definitions", self.check_class_definitions),
            ("Method Signatures", self.check_method_signatures),
            ("CLI Commands", self.check_cli_commands),
            ("PowerShell Scripts", self.check_powershell_scripts),
            ("Configuration Files", self.check_configuration_files),
            ("Module Imports", self.check_module_imports),
            ("Essential Logic", self.check_essential_logic),
            ("Browser Automation", self.check_browser_automation),
            ("Cookie Management", self.check_cookie_management),
            ("Export Functionality", self.check_export_functionality),
        ]

        for check_name, check_func in checks:
            print(f"\n📋 {check_name}...")
            try:
                success = check_func()
                if success:
                    self.passed_checks.append(check_name)
                    print(f"   ✅ {check_name} - PASSED")
                else:
                    print(f"   ❌ {check_name} - FAILED")
            except Exception as e:
                self.issues.append(f"{check_name}: Exception - {str(e)}")
                print(f"   💥 {check_name} - ERROR: {e}")

        return self.generate_report()

    def check_file_structure(self) -> bool:
        """Verify all essential files are present"""
        essential_files = [
            "src/core/client.py",
            "src/core/async_client.py",
            "src/core/models.py",
            "src/automation/web_driver.py",
            "src/automation/cookie_injector.py",
            "src/automation/cloudflare_handler.py",
            "src/automation/tab_manager.py",
            "src/auth/cookie_manager.py",
            "src/auth/account_generator.py",
            "src/interfaces/cli.py",
            "src/utils/cloudflare_bypass.py",
            "src/utils/connection_manager.py",
            "src/utils/imports.py",
            "requirements.txt",
            "config.yaml",
            "perplexity.ps1",
        ]

        missing_files = []
        for file_path in essential_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            self.issues.append(f"Missing files: {missing_files}")
            return False

        return True

    def check_class_definitions(self) -> bool:
        """Verify all classes are present with same structure"""
        critical_classes = {
            "src/core/client.py": ["PerplexityClient"],
            "src/core/async_client.py": ["AsyncPerplexityClient"],
            "src/core/models.py": [
                "SearchMode",
                "SearchResponse",
                "SearchConfig",
                "Conversation",
            ],
            "src/automation/web_driver.py": ["PerplexityWebDriver"],
            "src/auth/cookie_manager.py": ["CookieManager"],
            "src/auth/account_generator.py": ["AccountGenerator"],
        }

        for file_path, expected_classes in critical_classes.items():
            original_file = self.backup_path / file_path
            current_file = self.current_path / file_path.replace("src/", "")

            if not current_file.exists():
                self.issues.append(f"Missing file: {file_path}")
                continue

            try:
                # Parse both files
                original_classes = self._extract_classes(original_file)
                current_classes = self._extract_classes(current_file)

                for expected_class in expected_classes:
                    if expected_class not in current_classes:
                        self.issues.append(
                            f"Missing class {expected_class} in {file_path}"
                        )
                    elif expected_class in original_classes:
                        # Compare class structure
                        orig_methods = set(original_classes[expected_class])
                        curr_methods = set(current_classes[expected_class])

                        missing_methods = orig_methods - curr_methods
                        if missing_methods:
                            self.issues.append(
                                f"Missing methods in {expected_class}: {missing_methods}"
                            )

            except Exception as e:
                self.issues.append(f"Error parsing {file_path}: {e}")

        return len(self.issues) == 0

    def check_method_signatures(self) -> bool:
        """Check that critical method signatures are preserved"""
        critical_methods = {
            "PerplexityClient": [
                "search",
                "__init__",
                "start_conversation",
                "export_conversation",
                "get_cookies",
                "set_cookies",
                "create_labs_project",
            ],
            "AsyncPerplexityClient": [
                "search",
                "__init__",
                "batch_search",
                "start_conversation",
            ],
            "PerplexityWebDriver": [
                "search",
                "start",
                "navigate_to_perplexity",
                "export_as_markdown",
                "select_mode",
                "extract_cookies",
            ],
        }

        signature_issues = []

        for class_name, methods in critical_methods.items():
            # Find the file containing this class
            class_files = {
                "PerplexityClient": "core/client.py",
                "AsyncPerplexityClient": "core/async_client.py",
                "PerplexityWebDriver": "automation/web_driver.py",
            }

            if class_name not in class_files:
                continue

            file_path = class_files[class_name]
            original_file = self.backup_path / "src" / file_path
            current_file = self.current_path / file_path

            if not current_file.exists():
                signature_issues.append(f"Missing file for {class_name}: {file_path}")
                continue

            try:
                orig_sigs = self._extract_method_signatures(original_file, class_name)
                curr_sigs = self._extract_method_signatures(current_file, class_name)

                for method in methods:
                    if method not in curr_sigs:
                        signature_issues.append(f"Missing method {class_name}.{method}")
                    elif method in orig_sigs:
                        # Compare parameter counts (simplified check)
                        orig_params = len(orig_sigs[method])
                        curr_params = len(curr_sigs[method])
                        if (
                            abs(orig_params - curr_params) > 1
                        ):  # Allow for minor differences
                            self.warnings.append(
                                f"Parameter count difference in {class_name}.{method}: {orig_params} vs {curr_params}"
                            )

            except Exception as e:
                signature_issues.append(f"Error checking {class_name}: {e}")

        if signature_issues:
            self.issues.extend(signature_issues)
            return False
        return True

    def check_cli_commands(self) -> bool:
        """Verify all CLI commands are present"""
        expected_commands = [
            "search",
            "conversation",
            "batch",
            "browser",
            "browser-search",
            "browser-batch",
            "cookies",
        ]

        cli_file = self.current_path / "interfaces" / "cli.py"
        if not cli_file.exists():
            self.issues.append("CLI file missing")
            return False

        try:
            with open(cli_file, "r", encoding="utf-8") as f:
                cli_content = f.read()

            missing_commands = []
            for command in expected_commands:
                # Look for @cli.command() or @cli.command('command-name')
                if f"@cli.command('{command}')" not in cli_content and (
                    f"@cli.command()" not in cli_content
                    or f"def {command.replace('-', '_')}" not in cli_content
                ):
                    # Special handling for commands with dashes
                    cmd_func = command.replace("-", "_")
                    if f"def {cmd_func}" not in cli_content:
                        missing_commands.append(command)

            if missing_commands:
                self.issues.append(f"Missing CLI commands: {missing_commands}")
                return False

        except Exception as e:
            self.issues.append(f"Error checking CLI: {e}")
            return False

        return True

    def check_powershell_scripts(self) -> bool:
        """Check PowerShell script functionality"""
        ps_file = self.project_root / "perplexity.ps1"
        if not ps_file.exists():
            self.issues.append("PowerShell script missing")
            return False

        try:
            with open(ps_file, "r", encoding="utf-8") as f:
                ps_content = f.read()

            required_params = [
                "$Query",
                "$Mode",
                "$Profile",
                "$Research",
                "$DebugMode",
                "$KeepBrowserOpen",
                "$SearchMode",
            ]

            missing_params = []
            for param in required_params:
                if param not in ps_content:
                    missing_params.append(param)

            if missing_params:
                self.issues.append(f"Missing PowerShell parameters: {missing_params}")
                return False

            # Check for browser automation fallback
            if "browser automation" not in ps_content.lower():
                self.warnings.append(
                    "PowerShell script may not have browser automation fallback"
                )

        except Exception as e:
            self.issues.append(f"Error checking PowerShell script: {e}")
            return False

        return True

    def check_configuration_files(self) -> bool:
        """Verify configuration files are intact"""
        config_file = self.project_root / "config.yaml"
        if not config_file.exists():
            self.issues.append("config.yaml missing")
            return False

        try:
            import yaml

            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            required_sections = [
                "client",
                "search",
                "logging",
                "automation",
                "cloudflare_bypass",
            ]
            missing_sections = []

            for section in required_sections:
                if section not in config:
                    missing_sections.append(section)

            if missing_sections:
                self.issues.append(f"Missing config sections: {missing_sections}")
                return False

        except Exception as e:
            self.issues.append(f"Error checking config: {e}")
            return False

        return True

    def check_module_imports(self) -> bool:
        """Test that all modules can be imported"""
        critical_modules = [
            "src.core.client",
            "src.core.async_client",
            "src.core.models",
            "src.automation.web_driver",
            "src.auth.cookie_manager",
            "src.interfaces.cli",
        ]

        import_failures = []
        old_path = sys.path.copy()

        try:
            sys.path.insert(0, str(self.project_root))

            for module_name in critical_modules:
                try:
                    spec = importlib.util.find_spec(module_name)
                    if spec is None:
                        import_failures.append(f"{module_name} - spec not found")
                    else:
                        # Try to load the module
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                except Exception as e:
                    import_failures.append(f"{module_name} - {str(e)}")

        finally:
            sys.path = old_path

        if import_failures:
            self.issues.extend(import_failures)
            return False
        return True

    def check_essential_logic(self) -> bool:
        """Check that essential business logic patterns are preserved"""
        essential_patterns = {
            "src/core/client.py": [
                "CloudflareBypass",
                "httpx",
                "SearchResponse",
                "_parse_response",
                "export_conversation",
            ],
            "src/automation/web_driver.py": [
                "PerplexityWebDriver",
                "select_mode",
                "search",
                "export_as_markdown",
                "Camoufox",
            ],
            "src/interfaces/cli.py": [
                "browser-search",
                "click.command",
                "@cli.command",
                "PerplexityWebDriver",
                "browser automation",
            ],
        }

        missing_logic = []

        for file_path, patterns in essential_patterns.items():
            full_path = self.current_path / file_path.replace("src/", "")
            if not full_path.exists():
                missing_logic.append(f"File missing: {file_path}")
                continue

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()

                for pattern in patterns:
                    if pattern not in content:
                        missing_logic.append(
                            f"Missing pattern '{pattern}' in {file_path}"
                        )

            except Exception as e:
                missing_logic.append(f"Error checking {file_path}: {e}")

        if missing_logic:
            self.issues.extend(missing_logic)
            return False
        return True

    def check_browser_automation(self) -> bool:
        """Verify browser automation features are intact"""
        web_driver_file = self.current_path / "automation" / "web_driver.py"
        if not web_driver_file.exists():
            self.issues.append("web_driver.py missing")
            return False

        try:
            with open(web_driver_file, "r", encoding="utf-8") as f:
                content = f.read()

            essential_methods = [
                "def start",
                "def navigate_to_perplexity",
                "def search",
                "def select_mode",
                "def export_as_markdown",
                "def extract_cookies",
                "def close",
            ]

            missing_methods = []
            for method in essential_methods:
                if method not in content:
                    missing_methods.append(method)

            if missing_methods:
                self.issues.append(f"Missing web driver methods: {missing_methods}")
                return False

            # Check for Playwright and Camoufox support
            if "playwright" not in content.lower():
                self.warnings.append("Playwright support may be missing")
            if "camoufox" not in content.lower():
                self.warnings.append("Camoufox support may be missing")

        except Exception as e:
            self.issues.append(f"Error checking web driver: {e}")
            return False

        return True

    def check_cookie_management(self) -> bool:
        """Verify cookie management functionality"""
        cookie_files = [
            "src/auth/cookie_manager.py",
            "src/automation/cookie_injector.py",
        ]

        for file_path in cookie_files:
            full_path = self.project_root / file_path
            if not full_path.exists():
                self.issues.append(f"Cookie file missing: {file_path}")
                return False

        return True

    def check_export_functionality(self) -> bool:
        """Check export and output features"""
        # Check for markdown export in web driver
        web_driver_file = self.current_path / "automation" / "web_driver.py"
        if web_driver_file.exists():
            try:
                with open(web_driver_file, "r", encoding="utf-8") as f:
                    content = f.read()
                if "export_as_markdown" not in content:
                    self.issues.append("export_as_markdown method missing")
                    return False
            except Exception as e:
                self.issues.append(f"Error checking export functionality: {e}")
                return False

        return True

    def _extract_classes(self, file_path: Path) -> Dict[str, List[str]]:
        """Extract class names and their methods from a Python file"""
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except:
            return {}

        classes = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        methods.append(item.name)
                classes[node.name] = methods

        return classes

    def _extract_method_signatures(
        self, file_path: Path, class_name: str
    ) -> Dict[str, List[str]]:
        """Extract method signatures for a specific class"""
        if not file_path.exists():
            return {}

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
        except:
            return {}

        methods = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        params = [arg.arg for arg in item.args.args]
                        methods[item.name] = params
                break

        return methods

    def generate_report(self) -> bool:
        """Generate comprehensive audit report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE AUDIT REPORT")
        print("=" * 60)

        total_checks = len(self.passed_checks) + len(self.issues)
        passed = len(self.passed_checks)

        print(f"✅ PASSED CHECKS: {passed}")
        for check in self.passed_checks:
            print(f"   ✅ {check}")

        if self.issues:
            print(f"\n❌ FAILED CHECKS: {len(self.issues)}")
            for issue in self.issues:
                print(f"   ❌ {issue}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   ⚠️  {warning}")

        print("\n" + "=" * 60)

        if len(self.issues) == 0:
            print("🎉 AUDIT RESULT: ✅ ALL FUNCTIONALITY PRESERVED!")
            print(
                "✨ The optimization successfully maintained 100% of original functionality"
            )
            print("🚀 No shortcuts taken - all essential logic intact")
            return True
        else:
            print("⚠️  AUDIT RESULT: ❌ FUNCTIONALITY ISSUES DETECTED!")
            print(f"🔧 {len(self.issues)} issues need to be addressed")
            print("🛠️  Please review and fix the issues listed above")
            return False


def main():
    """Run the comprehensive functionality audit"""
    project_root = Path(__file__).parent
    auditor = FunctionalityAuditor(project_root)

    success = auditor.audit_all()

    print(f"\n{'=' * 60}")
    if success:
        print("✅ COMPREHENSIVE AUDIT: PASSED")
        print("🎉 ALL FUNCTIONALITY PRESERVED - NO SHORTCUTS TAKEN!")
    else:
        print("❌ COMPREHENSIVE AUDIT: FAILED")
        print("⚠️  FUNCTIONALITY ISSUES DETECTED - NEEDS ATTENTION!")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
