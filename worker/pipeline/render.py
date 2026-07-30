"""渲染模块：PaperDocument → HTML + CSS。

对应 SPEC 14.3：使用模板渲染器生成受控 HTML 与 CSS。
"""
import json
import logging

logger = logging.getLogger("tpaper.pipeline.render")


def build_presentation_prompt(document_json: str) -> list[dict]:
    """生成 HTML/CSS 的 Prompt。

    .. deprecated:: Use app.prompts.presentation_v1.build_prompt() instead.
    """
    from app.prompts.presentation_v1 import build_prompt

    return build_prompt(document_json)


async def render_presentation(adapter, document: dict) -> tuple[str, str]:
    """使用模板渲染器生成 HTML + CSS。"""
    from app.presentation import render_paper
    return render_paper(document)
