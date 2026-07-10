"""提取层 v2：合并提取+生成为单阶段。

升级点：
1. 提取+生成合并为单阶段，减少 API 调用
2. 支持多模态LLM直接读图
3. 优化 prompt 提升输出稳定性
"""
import json
import logging
from typing import Any

logger = logging.getLogger("tpaper.pipeline.extract_v2")

SINGLE_STAGE_SYSTEM = """你是试卷结构化助手。请从原始内容中直接提取并生成结构化的试卷文档。

输出 JSON 必须符合以下 Schema：
{
  "title": "试卷标题",
  "questions": [
    {
      "number": 1,
      "type": "single_choice | multi_choice | true_false | fill_blank | subjective",
      "stem": "题干文本",
      "options": [{"key": "A", "text": "选项内容"}],
      "correct_keys": ["A"],
      "reference_answer": "参考答案",
      "explanation": "解析",
      "knowledge_points": ["知识点"]
    }
  ]
}

重要规则：
1. 必须忠实原文，不得补充或修改答案
2. 跨页题目要完整提取，不要切断
3. 保留表格、列表等结构
4. 如果有图片，提取图片中的文字内容
5. 返回纯 JSON，不要包含任何 markdown 标记"""

SINGLE_STAGE_USER = """请从以下内容中提取试卷结构：

{content}"""


def _build_single_stage_prompt(content: str) -> list[dict]:
    """构建单阶段提取+生成的 prompt。"""
    return [
        {"role": "system", "content": SINGLE_STAGE_SYSTEM},
        {"role": "user", "content": SINGLE_STAGE_USER.format(content=content)},
    ]


async def extract_and_generate(adapter, chunks: list[dict], progress_callback=None) -> dict:
    """单阶段提取+生成：从预处理内容直接生成 PaperDocument。
    
    Args:
        adapter: 模型适配器
        chunks: 预处理后的内容块列表
        progress_callback: 进度回调函数
        
    Returns:
        PaperDocument JSON
    """
    all_questions = []
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(
                f"处理文档块 {i + 1}/{total_chunks}",
                int((i / total_chunks) * 100)
            )
        
        # 构建 prompt
        messages = _build_single_stage_prompt(chunk["text"])
        
        # 调用 LLM
        try:
            response = await adapter.chat(messages, response_format_json=True)
            result = json.loads(response.content)
            
            # 提取问题
            questions = result.get("questions", [])
            for q in questions:
                q["number"] = len(all_questions) + 1
                all_questions.append(q)
            
            logger.info(f"块 {i + 1}: 提取 {len(questions)} 道题")
        except Exception as e:
            logger.error(f"块 {i + 1} 处理失败: {e}")
            # 继续处理下一块
            continue
    
    # 构建最终的 PaperDocument
    document = {
        "title": "提取的试卷",
        "sections": [],
        "questions": all_questions,
    }
    
    return document


async def extract_and_generate_with_vision(adapter, chunks: list[dict], progress_callback=None) -> dict:
    """单阶段提取+生成（多模态版本）：支持扫描件。
    
    对于包含图片的块，使用多模态 LLM 直接读图。
    """
    all_questions = []
    total_chunks = len(chunks)
    
    for i, chunk in enumerate(chunks):
        if progress_callback:
            progress_callback(
                f"处理文档块 {i + 1}/{total_chunks}",
                int((i / total_chunks) * 100)
            )
        
        # 检查是否有图片需要处理
        has_images = any(p.get("image_b64") for p in chunk.get("pages", []))
        
        if has_images:
            # 多模态处理：将图片发送给 LLM
            result = await _process_with_vision(adapter, chunk)
        else:
            # 纯文本处理
            messages = _build_single_stage_prompt(chunk["text"])
            try:
                response = await adapter.chat(messages, response_format_json=True)
                result = json.loads(response.content)
            except Exception as e:
                logger.error(f"块 {i + 1} 处理失败: {e}")
                continue
        
        # 提取问题
        questions = result.get("questions", [])
        for q in questions:
            q["number"] = len(all_questions) + 1
            all_questions.append(q)
        
        logger.info(f"块 {i + 1}: 提取 {len(questions)} 道题")
    
    # 构建最终的 PaperDocument
    document = {
        "title": "提取的试卷",
        "sections": [],
        "questions": all_questions,
    }
    
    return document


async def _process_with_vision(adapter, chunk: dict) -> dict:
    """使用多模态 LLM 处理包含图片的内容。"""
    # 将文本和图片组合成多模态消息
    content_parts = []
    
    # 添加文本
    content_parts.append({
        "type": "text",
        "text": f"请从以下内容中提取试卷结构：\n\n{chunk['text']}"
    })
    
    # 添加图片
    for page in chunk.get("pages", []):
        if page.get("image_b64"):
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{page['mime']};base64,{page['image_b64']}"
                }
            })
    
    messages = [
        {"role": "system", "content": SINGLE_STAGE_SYSTEM},
        {"role": "user", "content": content_parts}
    ]
    
    response = await adapter.chat(messages, response_format_json=True)
    return json.loads(response.content)
