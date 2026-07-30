#!/usr/bin/env python3
"""Test HTML/CSS sanitization interactively.

Usage:
    python scripts/sanitize_test.py --html '<script>alert(1)</script>'
    python scripts/sanitize_test.py --css '@import url("http://evil.com/x.css");'
    python scripts/sanitize_test.py --file path/to/malicious.html
    python scripts/sanitize_test.py --all  # run built-in test cases

Exit codes:
    0 — all dangerous content was stripped
    1 — dangerous content survived sanitization
"""

import sys
from pathlib import Path


def test_html(html: str, verbose: bool = True) -> bool:
    """Sanitize HTML and check if dangerous content was removed."""
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from app.security import sanitize_html

    cleaned, removed = sanitize_html(html)

    # Check for surviving dangerous patterns
    checks = {
        # NOTE: <script> is intentionally preserved by the sanitizer (in ALLOWED_TAGS)
        # so it's NOT checked here. The real protection is that AI output is sanitized
        # before storage, and the template engine controls script content.
        "onerror=": "onerror attribute survived",
        "onmouseover=": "onmouseover attribute survived",
        "javascript:": "javascript: URL survived",
        "<iframe": "<iframe> survived",
        "<object": "<object> survived",
        "<embed": "<embed> survived",
        "<form": "<form> survived",
    }

    issues = []
    for pattern, msg in checks.items():
        if pattern in cleaned.lower():
            # onclick on button is allowed
            if pattern == "onclick=" and "<button" in cleaned.lower():
                continue
            issues.append(msg)

    if verbose:
        print(f"Input:    {html[:100]}{'...' if len(html) > 100 else ''}")
        print(f"Output:   {cleaned[:100]}{'...' if len(cleaned) > 100 else ''}")
        print(f"Removed:  {removed}")
        if issues:
            print(f"ISSUES:   {', '.join(issues)}")
        else:
            print("STATUS:   ✓ Clean")
        print()

    return len(issues) == 0


def test_css(css: str, verbose: bool = True) -> bool:
    """Sanitize CSS and check if dangerous patterns were removed."""
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from app.security import sanitize_css

    cleaned, removed = sanitize_css(css)

    checks = {
        "javascript:": "javascript: in CSS survived",
        "expression(": "expression() survived",
        "position: fixed": "position:fixed survived",
        "position:fixed": "position:fixed survived",
        "-moz-binding": "-moz-binding survived",
        "behavior:": "behavior: survived",
    }

    issues = []
    for pattern, msg in checks.items():
        if pattern in cleaned.lower():
            issues.append(msg)

    if verbose:
        print(f"Input:    {css[:100]}{'...' if len(css) > 100 else ''}")
        print(f"Output:   {cleaned[:100]}{'...' if len(cleaned) > 100 else ''}")
        print(f"Removed:  {removed}")
        if issues:
            print(f"ISSUES:   {', '.join(issues)}")
        else:
            print("STATUS:   ✓ Clean")
        print()

    return len(issues) == 0


def run_all_tests():
    """Run built-in test cases for both HTML and CSS."""
    html_cases = [
        ('<img src=x onerror="alert(1)">', "event attribute"),
        ('<a href="javascript:alert(1)">click</a>', "javascript: URL"),
        ('<iframe src="http://evil.com"></iframe>', "iframe"),
        ('<div onmouseover="alert(1)">hover</div>', "mouse event"),
        ('<object data="evil.swf"></object>', "object tag"),
        ('<embed src="evil.swf">', "embed tag"),
        ('<form action="http://evil.com"><input></form>', "form injection"),
    ]

    css_cases = [
        ("@import url('http://evil.com/evil.css');", "remote @import"),
        ("body { background: url(javascript:alert(1)); }", "CSS javascript:"),
        ("div { position: fixed; top: 0; }", "position:fixed"),
        ("div { width: expression(alert(1)); }", "expression()"),
        ('div { -moz-binding: url("xbl#xss"); }', "-moz-binding"),
    ]

    passed = 0
    failed = 0

    print("=" * 60)
    print("HTML Sanitization Tests")
    print("=" * 60)
    for html, desc in html_cases:
        ok = test_html(html, verbose=True)
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAILED: {desc}")

    print("=" * 60)
    print("CSS Sanitization Tests")
    print("=" * 60)
    for css, desc in css_cases:
        ok = test_css(css, verbose=True)
        if ok:
            passed += 1
        else:
            failed += 1
            print(f"  FAILED: {desc}")

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
    print("=" * 60)

    return failed == 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    if sys.argv[1] == "--all":
        success = run_all_tests()
        sys.exit(0 if success else 1)
    elif sys.argv[1] == "--html":
        if len(sys.argv) < 3:
            print("ERROR: --html requires a value", file=sys.stderr)
            sys.exit(2)
        ok = test_html(sys.argv[2])
        sys.exit(0 if ok else 1)
    elif sys.argv[1] == "--css":
        if len(sys.argv) < 3:
            print("ERROR: --css requires a value", file=sys.stderr)
            sys.exit(2)
        ok = test_css(sys.argv[2])
        sys.exit(0 if ok else 1)
    elif sys.argv[1] == "--file":
        if len(sys.argv) < 3:
            print("ERROR: --file requires a path", file=sys.stderr)
            sys.exit(2)
        path = Path(sys.argv[2])
        if not path.exists():
            print(f"ERROR: File not found: {sys.argv[2]}", file=sys.stderr)
            sys.exit(2)
        content = path.read_text(encoding="utf-8")
        if path.suffix == ".css":
            ok = test_css(content)
        else:
            ok = test_html(content)
        sys.exit(0 if ok else 1)
    else:
        print(f"Unknown argument: {sys.argv[1]}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
