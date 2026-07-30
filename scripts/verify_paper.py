#!/usr/bin/env python3
"""Verify a PaperDocument JSON file against the schema.

Usage:
    python scripts/verify_paper.py <path-to-json>
    python scripts/verify_paper.py <path-to-json> --strict  # fail on warnings too

Exit codes:
    0 — valid document
    1 — validation errors found
    2 — file not found or parse error
"""

import json
import sys
from pathlib import Path


def verify(json_path: str, strict: bool = False) -> int:
    path = Path(json_path)
    if not path.exists():
        print(f"ERROR: File not found: {json_path}", file=sys.stderr)
        return 2

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON: {e}", file=sys.stderr)
        return 2

    # Add backend to path
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))

    from app.schemas import PaperDocument

    # Pydantic validation
    try:
        doc = PaperDocument(**data)
    except Exception as e:
        print(f"FAIL: Schema validation failed:\n{e}", file=sys.stderr)
        return 1

    print(f"OK: Schema validation passed")
    print(f"  Title: {doc.title}")
    print(f"  Language: {doc.language}")
    print(f"  Questions: {len(doc.questions)}")
    print(f"  Sections: {len(doc.sections)}")

    # Semantic validation
    errors = doc.semantic_validate()
    warnings = [e for e in errors if e.startswith("⚠")]
    hard_errors = [e for e in errors if not e.startswith("⚠")]

    if hard_errors:
        print(f"\nFAIL: {len(hard_errors)} semantic error(s):")
        for err in hard_errors:
            print(f"  ✗ {err}")

    if warnings:
        print(f"\nWARN: {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  ⚠ {w}")

    if hard_errors:
        return 1
    if strict and warnings:
        return 1

    if not errors:
        print("\nPASS: No semantic issues found")
    else:
        print(f"\nPASS: {len(hard_errors)} error(s), {len(warnings)} warning(s)")

    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    json_path = sys.argv[1]
    strict = "--strict" in sys.argv

    sys.exit(verify(json_path, strict))


if __name__ == "__main__":
    main()
