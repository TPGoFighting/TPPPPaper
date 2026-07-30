#!/usr/bin/env python3
"""Check documentation freshness — run in CI to catch doc rot.

Verifies:
1. All files referenced in docs/ actually exist
2. FILE-REFERENCE.md lists files that exist
3. No plaintext secrets (passwords, SSH keys, API keys) in docs/
4. AGENTS.md references are still valid

Exit codes:
    0 — all checks passed
    1 — issues found
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"

# Patterns that indicate plaintext secrets
SECRET_PATTERNS = [
    (r"ssh\s+-i\s+\S+", "SSH key path"),
    (r"password\s*[:=]\s*['\"][^'\"]{4,}['\"]", "Plaintext password literal"),
    (r"api[_-]?key\s*[:=]\s*['\"][^'\"]{8,}['\"]", "API key literal"),
    (r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----", "Private key"),
    (r"postgres://\w+:\w+@", "Database connection string with credentials"),
    (r"redis://\w+:\w+@", "Redis connection string with credentials"),
]


def check_file_references() -> list[str]:
    """Check that files referenced in docs/ actually exist."""
    issues = []

    if not DOCS_DIR.exists():
        return issues

    for doc_file in DOCS_DIR.glob("*.md"):
        content = doc_file.read_text(encoding="utf-8")
        # Find markdown links: [text](path)
        links = re.findall(r"\[([^\]]*)\]\(([^)]+)\)", content)
        for text, link in links:
            # Skip external URLs and internal anchors
            if link.startswith("http://") or link.startswith("https://"):
                continue
            if link.startswith("#"):
                continue
            # Resolve relative to the doc file's directory
            target = (doc_file.parent / link).resolve()
            if not target.exists():
                issues.append(
                    f"  {doc_file.name}: broken link '{link}' → {text}"
                )

    return issues


def check_file_reference_md() -> list[str]:
    """Check that FILE-REFERENCE.md lists files that exist."""
    issues = []
    ref_file = DOCS_DIR / "FILE-REFERENCE.md"

    if not ref_file.exists():
        return issues

    content = ref_file.read_text(encoding="utf-8")
    # Find file paths mentioned (e.g., `backend/app/main.py`)
    paths = re.findall(r"`((?:backend|worker|web|docs)/[^\`]+)`", content)

    for path_str in paths:
        # Clean up the path (remove trailing punctuation)
        path_str = path_str.rstrip(".,;:")
        target = PROJECT_ROOT / path_str
        if not target.exists():
            issues.append(f"  FILE-REFERENCE.md: references non-existent '{path_str}'")

    return issues


def check_no_secrets() -> list[str]:
    """Check that docs/ doesn't contain plaintext secrets."""
    issues = []

    if not DOCS_DIR.exists():
        return issues

    for doc_file in DOCS_DIR.glob("*.md"):
        content = doc_file.read_text(encoding="utf-8")
        for pattern, description in SECRET_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                for match in matches[:3]:  # Limit to 3 matches per pattern
                    issues.append(
                        f"  {doc_file.name}: {description} found: "
                        f"'{match[:50]}{'...' if len(match) > 50 else ''}'"
                    )

    return issues


def check_agents_md() -> list[str]:
    """Check that AGENTS.md references are still valid."""
    issues = []
    agents_file = PROJECT_ROOT / "AGENTS.md"

    if not agents_file.exists():
        return ["AGENTS.md not found at project root"]

    content = agents_file.read_text(encoding="utf-8")

    # Check that referenced files/directories exist
    referenced_paths = re.findall(r"`((?:backend|worker|web|docs|tests|scripts)/[^\`]+)`", content)
    for path_str in referenced_paths:
        path_str = path_str.rstrip(".,;:/")
        target = PROJECT_ROOT / path_str
        if not target.exists():
            issues.append(f"  AGENTS.md: references non-existent '{path_str}'")

    return issues


def main():
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__.strip())
        sys.exit(0)

    all_issues = []

    print("Checking documentation freshness...")
    print()

    print("1. File references in docs/:")
    issues = check_file_references()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("  ✓ All links valid")
    print()

    print("2. FILE-REFERENCE.md accuracy:")
    issues = check_file_reference_md()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("  ✓ All referenced files exist")
    print()

    print("3. Secret detection in docs/:")
    issues = check_no_secrets()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("  ✓ No secrets detected")
    print()

    print("4. AGENTS.md references:")
    issues = check_agents_md()
    if issues:
        all_issues.extend(issues)
        for i in issues:
            print(f"  ✗ {i}")
    else:
        print("  ✓ All references valid")
    print()

    if all_issues:
        print(f"FAILED: {len(all_issues)} issue(s) found")
        return 1
    else:
        print("PASSED: Documentation is fresh")
        return 0


if __name__ == "__main__":
    sys.exit(main())
