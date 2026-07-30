"""Centralized LLM prompt registry.

All prompts used by the TPaper pipeline are versioned here.
When modifying a prompt, increment its VERSION and add a CHANGELOG entry.

Usage:
    from app.prompts import extract_v1, generate_v1, presentation_v1, answering_v1
    messages = extract_v1.build_prompt(page_text, page_number)
"""

from app.prompts import extract_v1, generate_v1, presentation_v1, answering_v1, simple_v1

__all__ = [
    "extract_v1",
    "generate_v1",
    "presentation_v1",
    "answering_v1",
    "simple_v1",
]
