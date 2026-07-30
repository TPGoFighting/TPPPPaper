"""Simple pipeline prompt v1 — single-call PaperDocument generation.

Used by: worker/pipeline/simple_pipeline.py
This is the fast-path prompt that combines extraction + generation in one call.
"""

import json
from typing import Any

from app.prompts.schemas import PAPER_DOCUMENT_SCHEMA, SOURCE_TRANSCRIPTION_SCHEMA, SAFETY_INSTRUCTION

VERSION = "1.1.0"
CHANGELOG = [
    ("1.1.0", "2026-07-16", "Add <source_text> XML fencing around user data for injection defense"),
    ("1.0.0", "2026-07-16", "Initial extraction from worker/pipeline/simple_pipeline.py"),
]

FAITHFUL_SYSTEM = (
    "你是试卷结构化助手。根据以下文本内容生成 PaperDocument JSON。\n"
    "第一阶段仅忠实转写：提取所有题目、选项、原卷分值和来源页码。\n"
    "原卷未出现的答案、解析、评分点一律保持空值，绝不可自行求解或猜测。\n"
    "如果原文包含表格数据，将表格行转化为对应的题目。\n"
    "若同时提供页面图片，必须将图片中的公式、表格、图形、代码和状态信息\n"
    "与文字层合并转写；图片是原文件的一部分，不能因文字层不完整而省略。\n"
    "不得擅自补充题目、修改题干或编造答案。每题 source_page 必须是题干所在页。\n"
    "必须返回有效的 JSON，不要包含任何其他文本。\n"
) + SAFETY_INSTRUCTION + "\n\n" + SOURCE_TRANSCRIPTION_SCHEMA

LECTURE_SYSTEM = (
    "你是试卷生成助手。根据以下讲义内容生成练习题。\n"
    "生成 10-20 道练习题，包含单选、多选、判断、填空、简答等题型。\n"
    "每道题必须包含题干、选项（选择题）、正确答案和解析。\n"
    "生成的题目必须标记 is_ai_generated=true。\n"
    "必须返回有效的 JSON，不要包含任何其他文本。\n"
) + SAFETY_INSTRUCTION + "\n\n" + PAPER_DOCUMENT_SCHEMA


def build_prompt(
    text_content: str,
    mode: str,
    visual_pages: list[dict[str, Any]] | None = None,
    max_chars: int = 100_000,
) -> list[dict[str, Any]]:
    """Build simple pipeline prompt (single-call extraction + generation).

    Args:
        text_content: Extracted text from the source document.
        mode: "faithful_transcription" or "lecture_to_quiz".
        visual_pages: Optional list of page image dicts for multimodal input.
        max_chars: Maximum text length before truncation.
    """
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n\n[文本已截断...]"

    system = FAITHFUL_SYSTEM if mode == "faithful_transcription" else LECTURE_SYSTEM

    user: str | list[dict[str, Any]] = (
        f"文本内容：\n<source_text>\n{text_content}\n</source_text>"
    )
    visual_pages = visual_pages or []
    if visual_pages:
        user = [{"type": "text", "text": (
            f"文字层内容：\n<source_text>\n{text_content}\n</source_text>"
        )}]
        for page in visual_pages:
            image_b64 = page.get("image_b64")
            if not image_b64:
                continue
            page_number = page.get("page", "?")
            user.extend([
                {
                    "type": "text",
                    "text": f"以下是第 {page_number} 页的原始页面图。"
                    "请用它补全文字层遗漏的公式、图表、序列、状态、表格和代码，"
                    "并保留该页来源页码。",
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{page.get('mime', 'image/png')};base64,{image_b64}"},
                },
            ])

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
