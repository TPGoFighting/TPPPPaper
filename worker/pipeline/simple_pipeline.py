"""简化版 Pipeline：单次 LLM 调用 + 模板渲染。

新架构：
1. PDF → 文本提取（快速，无 LLM）
2. 文本 → LLM → PaperDocument JSON（单次调用）
3. JSON → 模板渲染 → HTML
"""
import json
import logging
from typing import Any

from app.prompts.simple_v1 import build_prompt as _build_prompt
from app.prompts.simple_v1 import VERSION as SIMPLE_PROMPT_VERSION

logger = logging.getLogger("tpaper.pipeline.simple")


def _parse_json_response(content: str) -> dict:
    """从 LLM 响应中解析 JSON。"""
    # 尝试直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 尝试提取 JSON 块
    start = content.find("{")
    end = content.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass

    # 尝试提取 ```json ... ``` 块
    json_start = content.find("```json")
    if json_start >= 0:
        json_end = content.find("```", json_start + 7)
        if json_end > json_start:
            try:
                return json.loads(content[json_start + 7:json_end])
            except json.JSONDecodeError:
                pass

    raise ValueError(f"无法解析 JSON: {content[:200]}...")


def _ensure_valid_document(doc: dict) -> dict:
    """确保文档结构有效。"""
    # 确保必需字段存在
    doc.setdefault("title", "试卷")
    doc.setdefault("language", "zh-CN")
    doc.setdefault("metadata", {})
    doc.setdefault("sections", [])
    doc.setdefault("questions", [])

    # 确保每个题目有必需字段
    for i, q in enumerate(doc["questions"]):
        q.setdefault("id", f"q_{i + 1}")
        # 模型常将同一大题下的小问都标成相同题号。渲染层需要全局唯一、
        # 连续的题号，因此以最终 questions 数组顺序作为唯一编号来源。
        q["number"] = i + 1
        q.setdefault("type", "subjective")
        q.setdefault("stem", "")
        q.setdefault("score", 0)
        q.setdefault("options", [])
        q.setdefault("correct_keys", [])
        q.setdefault("explanation", "")
        q.setdefault("needs_review", True)

    # 章节经常保留模型输出中被截断题目的 ID。只保留最终题目列表中存在的
    # ID，并将未归类题目补入默认章节，保证所有草稿都能通过语义校验。
    valid_ids = [q["id"] for q in doc["questions"]]
    valid_id_set = set(valid_ids)
    assigned_ids: set[str] = set()
    normalized_sections = []
    for index, section in enumerate(doc["sections"], start=1):
        if not isinstance(section, dict):
            continue
        question_ids = []
        for question_id in section.get("question_ids") or []:
            question_id = str(question_id)
            if question_id in valid_id_set and question_id not in assigned_ids:
                question_ids.append(question_id)
                assigned_ids.add(question_id)
        if question_ids:
            normalized_sections.append({
                "id": str(section.get("id") or f"section_{index}"),
                "title": str(section.get("title") or ""),
                "question_ids": question_ids,
            })

    unassigned_ids = [qid for qid in valid_ids if qid not in assigned_ids]
    if unassigned_ids:
        existing_section_ids = {section["id"] for section in normalized_sections}
        normalized_sections.append({
            "id": "default" if "default" not in existing_section_ids else "unassigned",
            "title": "",
            "question_ids": unassigned_ids,
        })
    doc["sections"] = normalized_sections

    return doc


async def simple_extract_and_generate(
    adapter,
    preprocessed: dict,
    mode: str,
    vision_adapter=None,
    generate_answers: bool = True,
    research_provider: str = "",
    research_api_key: str = "",
    research_max_results: int = 3,
    research_timeout_seconds: int = 12,
) -> dict:
    """简化版提取和生成：单次 LLM 调用。

    Args:
        adapter: LLM 适配器
        preprocessed: 预处理结果 {"pages": [...], "page_count": int}
        mode: 模式 (faithful_transcription / lecture_to_quiz)

    Returns:
        PaperDocument JSON
    """
    # 合并所有页面文本
    pages = preprocessed.get("pages", [])
    all_text = []
    for page in pages:
        text = page.get("text", "")
        if text.strip():
            all_text.append(f"=== 第 {page['page']} 页 ===\n{text}")

    combined_text = "\n\n".join(all_text)
    logger.info(f"合并文本: {len(combined_text)} 字符, {len(pages)} 页")

    if not combined_text.strip():
        logger.warning("文本内容为空，返回空文档")
        return _ensure_valid_document({
            "title": "空白文档",
            "sections": [],
            "questions": [],
        })

    # 单次 LLM 调用（大输出：题目较多，需提高 max_tokens 防止截断）
    logger.info(f"调用 LLM 生成 PaperDocument (模式: {mode})...")
    visual_pages = [page for page in pages if page.get("image_b64")]
    model_adapter = vision_adapter if visual_pages and vision_adapter else adapter
    if visual_pages and not vision_adapter:
        logger.warning("检测到 %s 个视觉页面，但当前模型未启用视觉能力", len(visual_pages))
    elif visual_pages:
        logger.info("附加 %s 个含视觉内容的页面供模型忠实转写", len(visual_pages))
    msgs = _build_prompt(combined_text, mode, visual_pages=visual_pages)
    logger.info(f"Prompt 版本: simple_v{SIMPLE_PROMPT_VERSION}")
    result = await model_adapter.chat(msgs, response_format_json=True, max_tokens=32000)

    if not result.success:
        raise RuntimeError(f"LLM 调用失败: {result.error}")

    # 解析 JSON
    logger.info("解析 LLM 响应...")
    doc = _parse_json_response(result.content)

    # 确保文档结构有效
    doc = _ensure_valid_document(doc)

    if generate_answers:
        # 第二阶段独立生成答案、评分点和解析。分开执行能保证原文转写不被
        # 模型的求解过程污染，并让 AI 推导/网页研究的来源在草稿中可追溯。
        from worker.pipeline.answering import enrich_document_answers
        logger.info("生成答案、解析与可追溯证据...")
        doc = await enrich_document_answers(
            adapter, doc,
            research_provider=research_provider,
            research_api_key=research_api_key,
            research_max_results=research_max_results,
            research_timeout_seconds=research_timeout_seconds,
        )

    logger.info(f"生成完成: {len(doc['questions'])} 题, {len(doc['sections'])} 章节")
    return doc
