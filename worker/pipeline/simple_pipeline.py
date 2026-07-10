"""简化版 Pipeline：单次 LLM 调用 + 模板渲染。

新架构：
1. PDF → 文本提取（快速，无 LLM）
2. 文本 → LLM → PaperDocument JSON（单次调用）
3. JSON → 模板渲染 → HTML
"""
import json
import logging
from typing import Any

logger = logging.getLogger("tpaper.pipeline.simple")


# ── PaperDocument Schema ──
PAPER_DOCUMENT_SCHEMA = """输出 JSON 必须严格符合以下 Schema：
{
  "title": "试卷标题",
  "language": "zh-CN",
  "metadata": {},
  "sections": [
    {
      "id": "s_唯一ID",
      "title": "章节名称",
      "question_ids": ["q_xxx"]
    }
  ],
  "questions": [
    {
      "id": "q_唯一ID",
      "number": 1,
      "type": "single_choice | multi_choice | true_false | fill_blank | subjective",
      "stem": "题干文本",
      "score": 5.0,
      "options": [{"key": "A", "text": "选项内容"}],
      "correct_keys": ["A"],
      "true_false_answer": null,
      "acceptable_answers": [],
      "reference_answer": "",
      "explanation": "解析",
      "knowledge_points": [],
      "confidence": 1.0,
      "needs_review": false,
      "is_ai_generated": false
    }
  ]
}"""


def build_simple_prompt(
    text_content: str,
    mode: str,
    max_chars: int = 100000,
) -> list[dict[str, Any]]:
    """构建简化版 Prompt：单次调用生成完整 PaperDocument。"""
    # 截断过长文本
    if len(text_content) > max_chars:
        text_content = text_content[:max_chars] + "\n\n[文本已截断...]"

    if mode == "faithful_transcription":
        system = (
            "你是试卷结构化助手。根据以下文本内容生成 PaperDocument JSON。\n"
            "忠实转写模式：必须忠实原文，提取所有题目、选项、答案。\n"
            "如果原文包含表格数据，将表格行转化为对应的题目。\n"
            "不得擅自补充题目或修改答案。\n"
            "必须返回有效的 JSON，不要包含任何其他文本。\n\n"
        ) + PAPER_DOCUMENT_SCHEMA
    else:
        system = (
            "你是试卷生成助手。根据以下讲义内容生成练习题。\n"
            "生成 10-20 道练习题，包含单选、多选、判断、填空、简答等题型。\n"
            "每道题必须包含题干、选项（选择题）、正确答案和解析。\n"
            "生成的题目必须标记 is_ai_generated=true。\n"
            "必须返回有效的 JSON，不要包含任何其他文本。\n\n"
        ) + PAPER_DOCUMENT_SCHEMA

    user = f"文本内容：\n\n{text_content}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


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
        q.setdefault("number", i + 1)
        q.setdefault("type", "subjective")
        q.setdefault("stem", "")
        q.setdefault("score", 0)
        q.setdefault("options", [])
        q.setdefault("correct_keys", [])
        q.setdefault("explanation", "")
        q.setdefault("needs_review", True)

    # 如果没有章节，创建默认章节
    if not doc["sections"] and doc["questions"]:
        doc["sections"] = [{
            "id": "default",
            "title": "",
            "question_ids": [q["id"] for q in doc["questions"]],
        }]

    return doc


async def simple_extract_and_generate(
    adapter,
    preprocessed: dict,
    mode: str,
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
    msgs = build_simple_prompt(combined_text, mode)
    result = await adapter.chat(msgs, response_format_json=True, max_tokens=32000)

    if not result.success:
        raise RuntimeError(f"LLM 调用失败: {result.error}")

    # 解析 JSON
    logger.info("解析 LLM 响应...")
    doc = _parse_json_response(result.content)

    # 确保文档结构有效
    doc = _ensure_valid_document(doc)

    logger.info(f"生成完成: {len(doc['questions'])} 题, {len(doc['sections'])} 章节")
    return doc
