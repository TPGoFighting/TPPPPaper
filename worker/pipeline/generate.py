"""文档生成模块：分批生成 + 合并。

对应 SPEC 14.2：PaperDocument 生成阶段。
"""
import json
import logging
from typing import Any

logger = logging.getLogger("tpaper.pipeline.generate")

from app.prompts.schemas import PAPER_DOCUMENT_SCHEMA


def build_document_prompt(
    extracted: list[dict[str, Any]],
    mode: str,
    requirements: str = "",
) -> list[dict[str, Any]]:
    """生成 PaperDocument 的 Prompt。

    .. deprecated:: Use app.prompts.generate_v1.build_prompt() instead.
    """
    from app.prompts.generate_v1 import build_prompt

    return build_prompt(extracted, mode, requirements)


def _parse_json_response(content: str) -> dict:
    """从 LLM 响应中解析 JSON，支持修复。"""
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON 解析失败，尝试修复: {e}")
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


async def _generate_document_chunk(
    adapter, extracted: list[dict], mode: str
) -> dict:
    """单批文档生成。"""
    msgs = build_document_prompt(extracted, mode)
    result = await adapter.chat(msgs, response_format_json=True)
    if not result.success:
        raise RuntimeError(f"文档生成失败: {result.error}")
    return _parse_json_response(result.content)


def _merge_documents(partials: list[dict]) -> dict:
    """合并多个分批生成的 PaperDocument 为一个。"""
    all_sections: list[dict] = []
    all_questions: list[dict] = []
    q_num = 1
    for doc in partials:
        for section in doc.get("sections", []):
            all_sections.append(section)
        for q in doc.get("questions", []):
            q["number"] = q_num
            q["id"] = f"q_{q_num}"
            all_questions.append(q)
            q_num += 1
    title = partials[0].get("title", "试卷") if partials else "试卷"
    return {
        "title": title,
        "language": "zh-CN",
        "metadata": partials[0].get("metadata", {}) if partials else {},
        "sections": all_sections,
        "questions": all_questions,
    }


async def generate_document(
    adapter, extracted: list[dict], mode: str, chunk_size: int = 10
) -> dict:
    """生成 PaperDocument。小文档一次生成，大文档分批+合并。"""
    total_items = sum(len(e.get("items", [])) for e in extracted)
    logger.info(f"文档生成输入: {len(extracted)} pages, {total_items} total items")

    if len(extracted) <= chunk_size:
        return await _generate_document_chunk(adapter, extracted, mode)

    partials: list[dict] = []
    for i in range(0, len(extracted), chunk_size):
        chunk = extracted[i : i + chunk_size]
        chunk_items = sum(len(e.get("items", [])) for e in chunk)
        logger.info(f"文档生成分批: pages {i+1}-{i+len(chunk)}, {chunk_items} items")
        try:
            doc = await _generate_document_chunk(adapter, chunk, mode)
            partials.append(doc)
            logger.info(f"分批 {i//chunk_size + 1} 成功: {len(doc.get('questions', []))} questions")
        except Exception as e:
            logger.warning(f"分批 {i//chunk_size + 1} 失败: {e}，跳过该批次")

    if not partials:
        raise RuntimeError("所有分批生成均失败")

    merged = _merge_documents(partials)
    logger.info(f"合并完成: {len(merged.get('questions', []))} questions total")
    return merged
