"""Presentation/render prompt v1 — HTML + CSS generation.

Corresponds to SPEC §14.3: 使用模板渲染器生成受控 HTML 与 CSS。
Used by: worker/pipeline/render.py
"""

VERSION = "1.0.0"
CHANGELOG = [
    ("1.0.0", "2026-07-16", "Initial extraction from worker/pipeline/render.py"),
]

SYSTEM_INSTRUCTION = (
    "你是网页生成助手。根据 PaperDocument 生成受控 HTML 与 CSS。"
    "规则：\n"
    "1. 只能使用安全语义标签和 TPaper 受控组件（<tp-section>, <tp-question>, "
    "<tp-choice>, <tp-blank>, <tp-explanation>）。\n"
    "2. 禁止生成 <script>、事件处理属性、javascript: URL、iframe、form。\n"
    "3. 禁止生成可执行 JavaScript。\n"
    "4. 答题、判分、进度由平台运行时实现，你只决定布局和视觉。\n"
    "5. 返回 JSON：{\"presentation_html\": str, \"theme_css\": str}"
)


def build_prompt(document_json: str) -> list[dict]:
    """Build presentation generation prompt."""
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": f"PaperDocument:\n{document_json}"},
    ]
