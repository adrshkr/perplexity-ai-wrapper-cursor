import re


def check_powershell_syntax(filepath):
    """Check PowerShell script for common syntax issues."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    issues = []
    lines = content.split("\n")

    for i, line in enumerate(lines, 1):
        line_stripped = line.strip()

        # Check for Python-style 'if not' syntax in PowerShell
        if "if not " in line and ":" in line and "$" in line:
            issues.append(
                f"Line {i}: Potential Python/PowerShell syntax mix: {line_stripped}"
            )

        # Check for unescaped variable references with colons
        if re.search(r"\$\w+:", line) and "param" not in line.lower():
            issues.append(
                f"Line {i}: Potential variable reference issue: {line_stripped}"
            )

        # Check for missing parameter declarations
        if (
            line_stripped.startswith("[")
            and "Parameter" in line
            and not line_stripped.endswith(",")
        ):
            next_line_idx = i
            if next_line_idx < len(lines):
                next_line = lines[next_line_idx].strip()
                if not next_line.startswith("[") and not next_line.startswith("$"):
                    issues.append(
                        f"Line {i}: Parameter declaration might be incomplete"
                    )

    return issues


if __name__ == "__main__":
    issues = check_powershell_syntax("perplexity.ps1")

    if issues:
        print("PowerShell syntax issues found:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("No obvious PowerShell syntax issues detected")
        print("Script appears to have valid PowerShell syntax")
