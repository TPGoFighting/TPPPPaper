"""第 2 层：内容理解层。

用大模型分析预处理得到的文本，提取：
  - 题型（single_choice / multi_choice / true_false / fill_blank / subjective）
  - 题干、选项、正确答案、解析、分值、知识点
模型自行生成答案与解析。

输出：PaperDocument JSON（结构化，便于第 3 层模板注入）。
"""
import json
import logging

from client import chat_json

logger = logging.getLogger("tier2.understand")

SCHEMA = """输出 JSON 必须严格符合以下结构：
{
  "title": "试卷标题",
  "sections": [
    {"id": "s1", "title": "章节名", "question_ids": ["q1","q2"]}
  ],
  "questions": [
    {
      "id": "q1",
      "number": 1,
      "type": "single_choice",
      "stem": "题干",
      "score": 5,
      "options": [{"key": "A", "text": "选项A"}],
      "correct_keys": ["A"],
      "answer_text": "直接答案（填空/简答应填；选择/判断可留空）",
      "solution": "解答过程（含步骤与公式）",
      "explanation": "解析与易错提醒",
      "knowledge_points": ["考点1"]
    }
  ]
}
题型说明：single_choice=单选, multi_choice=多选, true_false=判断, fill_blank=填空, subjective=简答。
correct_keys：选择题填选项字母列表；判断题填 ["T"] 或 ["F"]；填空/简答可留空。
answer_text：填空/简答必须给出参考答案文本；选择/判断可留空。
solution：完整解答过程（计算/推导步骤），用换行分隔每一步，可用 $LaTeX$ 公式（如 $P(A\\cap\\bar B)$、$0.8\\times0.4$）。
explanation：解析与易错提醒（思路、考点、易错点），可用 $LaTeX$ 公式，用换行分隔。
knowledge_points：本题核心知识点（1-3个）。
数学公式一律用 $...$ 包裹；solution/explanation 内用换行（\\n）分隔步骤，保持可读。
必须只返回一个合法 JSON 对象。"""

# 23 题时，完整的逐题长解答会把单次响应推入极慢的长输出区间。
# 这些限制保留题目可用性，同时让输出能稳定落在 16k token 预算内。
OUTPUT_LENGTH_RULES = (
    "严格控制总输出：answer_text 不超过 40 字；solution 最多 3 步、120 字；"
    "explanation 不超过 80 字。选择题和判断题的 solution 只用一句话说明依据。"
)


def build_prompt(text: str, mode: str) -> list[dict]:
    if mode == "faithful_transcription":
        sys_extra = (
            "你是试卷结构化助手。忠实提取原文中的题目与选项，不得编造。"
        )
    else:
        sys_extra = (
            "你是出题助手。根据讲义内容生成练习题，并自行给出答案与解析。"
            "生成的题目标记 is_ai_generated=true。"
        )
    system = (
        sys_extra
        + "\n\n每题必须包含 answer_text / solution / explanation 三个字段："
        + "① answer_text 直接答案（不超过 40 字）；② solution 最多 3 步、120 字（步骤换行、公式用 $LaTeX$）；"
        + "③ explanation 不超过 80 字。选择/判断题的 solution 用一句话说明依据。填空题的 solution 开头先用【答案】给出结果，再写过程。"
        + "数学公式一律用 $...$ 包裹。"
        + "\n\n" + OUTPUT_LENGTH_RULES
        + "\n\n" + SCHEMA
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": f"内容如下：\n\n{text}"},
    ]


def understand(pages: list[dict], mode: str = "lecture_to_quiz", max_chars: int = 60000) -> dict:
    """合并文本 → 单次 LLM 调用 → PaperDocument JSON。"""
    chunks = []
    for p in pages:
        t = p.get("text", "")
        if t.strip():
            chunks.append(f"=== 第 {p['page']} 页 ===\n{t}")
    text = "\n\n".join(chunks)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[文本已截断]"
    logger.info(f"Tier 2: 合并文本 {len(text)} 字符，调用 LLM（mode={mode}）")

    messages = build_prompt(text, mode)
    # 23 题时 32k 输出会进入模型的极慢长生成区间；字段长度已受提示约束。
    doc = chat_json(messages, max_tokens=16000, temperature=0.2)
    return _normalize(doc)


def _normalize(doc: dict) -> dict:
    doc.setdefault("title", "未命名试卷")
    doc.setdefault("sections", [])
    doc.setdefault("questions", [])
    for i, q in enumerate(doc["questions"]):
        q.setdefault("id", f"q{i+1}")
        q.setdefault("number", i + 1)
        q.setdefault("type", "subjective")
        q.setdefault("stem", "")
        q.setdefault("options", [])
        q.setdefault("correct_keys", [])
        q.setdefault("answer_text", "")
        q.setdefault("solution", "")
        q.setdefault("explanation", "")
        q.setdefault("score", 0)
    if not doc["sections"] and doc["questions"]:
        doc["sections"] = [{
            "id": "default",
            "title": "",
            "question_ids": [q["id"] for q in doc["questions"]],
        }]
    return doc


if __name__ == "__main__":
    sample = "1. 下列哪项是公司最高权力机构？ A.董事会 B.股东会 C.经理层 D.监事会"
    d = understand([{"page": 1, "text": sample}], mode="faithful_transcription")
    print(json.dumps(d, ensure_ascii=False, indent=2))
