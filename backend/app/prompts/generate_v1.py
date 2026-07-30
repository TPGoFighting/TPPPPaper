"""Document generation prompt v1 — Stage 2: PaperDocument generation.

Corresponds to SPEC §14.2: PaperDocument 生成阶段。
Used by: worker/pipeline/generate.py
"""

from app.prompts.schemas import PAPER_DOCUMENT_SCHEMA, SAFETY_INSTRUCTION

VERSION = "1.0.0"
CHANGELOG = [
    ("1.0.0", "2026-07-16", "Initial extraction from worker/pipeline/generate.py"),
]

FAITHFUL_SYSTEM = (
    "你是试卷结构化助手。根据提取的内容生成 PaperDocument JSON。\n"
    "忠实转写模式：必须忠实原文，如果原文中有题目则提取题目，如果原文是报告/文档则将其内容转化为结构化题目。\n"
    "如果原文包含表格数据，将表格行转化为对应的题目。\n"
    "不得擅自补充题目或修改答案，但可以从原文中识别题目和答案结构。\n"
) + SAFETY_INSTRUCTION + "\n\n" + PAPER_DOCUMENT_SCHEMA

LECTURE_SYSTEM = (
    "你是试卷生成助手。根据讲义内容生成练习题、答案和解析。\n"
    "生成的题目必须标记 is_ai_generated=true。\n"
) + SAFETY_INSTRUCTION + "\n\n" + PAPER_DOCUMENT_SCHEMA


def build_prompt(
    extracted: list[dict],
    mode: str,
    requirements: str = "",
) -> list[dict]:
    """Build document generation prompt.

    Args:
        extracted: List of extracted page dicts from Stage 1.
        mode: "faithful_transcription" or "lecture_to_quiz".
        requirements: Optional additional requirements text.
    """
    import json

    system = FAITHFUL_SYSTEM if mode == "faithful_transcription" else LECTURE_SYSTEM
    if requirements:
        system += f"\n额外要求：{requirements}"

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": "提取的内容（JSON 数组）：\n" + json.dumps(extracted, ensure_ascii=False)},
    ]
