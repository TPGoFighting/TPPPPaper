#!/usr/bin/env python3
"""Render a PaperDocument JSON to HTML preview locally.

Usage:
    python scripts/render_preview.py <path-to-json>
    python scripts/render_preview.py <path-to-json> -o output.html

Exit codes:
    0 — rendered successfully
    1 — rendering failed
    2 — file not found or parse error
"""

import json
import sys
import webbrowser
from pathlib import Path


def render(json_path: str, output_path: str | None = None) -> int:
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
    from app.presentation import render_paper

    # Validate document
    try:
        doc = PaperDocument(**data)
    except Exception as e:
        print(f"ERROR: Invalid document: {e}", file=sys.stderr)
        return 2

    # Render
    try:
        html, css = render_paper(doc.model_dump())
    except Exception as e:
        print(f"ERROR: Rendering failed: {e}", file=sys.stderr)
        return 1

    # Build preview page
    preview = f"""<!DOCTYPE html>
<html lang="{doc.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title} — Preview</title>
    <style>{css}</style>
</head>
<body>
{html}
</body>
</html>"""

    # Write output
    if output_path is None:
        output_path = str(path.with_suffix(".html"))

    Path(output_path).write_text(preview, encoding="utf-8")
    print(f"Rendered: {output_path}")
    print(f"  Title: {doc.title}")
    print(f"  Questions: {len(doc.questions)}")
    print(f"  HTML size: {len(html):,} chars")
    print(f"  CSS size: {len(css):,} chars")

    return 0


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip())
        sys.exit(0)

    json_path = sys.argv[1]
    output_path = None

    if "-o" in sys.argv:
        idx = sys.argv.index("-o")
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    sys.exit(render(json_path, output_path))


if __name__ == "__main__":
    main()
