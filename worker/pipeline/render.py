"""渲染模块：PaperDocument → HTML + CSS。

对应 SPEC 14.3：使用模板渲染器生成受控 HTML 与 CSS。
"""
import json
import logging

logger = logging.getLogger("tpaper.pipeline.render")


def build_presentation_prompt(document_json: str) -> list[dict]:
    """生成 HTML/CSS 的 Prompt。"""
    system = (
        "你是网页生成助手。根据 PaperDocument 生成受控 HTML 与 CSS。"
        "规则：\n"
        "1. 只能使用安全语义标签和 TPaper 受控组件（<tp-section>, <tp-question>, "
        "<tp-choice>, <tp-blank>, <tp-explanation>）。\n"
        "2. 禁止生成 <script>、事件处理属性、javascript: URL、iframe、form。\n"
        "3. 禁止生成可执行 JavaScript。\n"
        "4. 答题、判分、进度由平台运行时实现，你只决定布局和视觉。\n"
        "5. 返回 JSON：{\"presentation_html\": str, \"theme_css\": str}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"PaperDocument:\n{document_json}"},
    ]


async def render_presentation(adapter, document: dict) -> tuple[str, str]:
    """使用模板渲染器生成 HTML + CSS。"""
    from app.presentation import render_paper
    return render_paper(document)
