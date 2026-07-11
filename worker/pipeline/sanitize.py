"""净化模块：HTML/CSS 安全清理 + 校验。

对应 SPEC 14.4。
"""
import logging

logger = logging.getLogger("tpaper.pipeline.sanitize")


def sanitize(html: str, css: str, document: dict) -> tuple[str, str, list[str], bool]:
    """净化 HTML/CSS 并校验文档结构。

    Returns:
        (clean_html, clean_css, validation_errors, is_valid)
    """
    from app.security import sanitize_html, sanitize_css

    clean_html, _ = sanitize_html(html)
    clean_css, _ = sanitize_css(css, scope_selector="")

    validation_errors: list[str] = []
    try:
        from app.schemas import PaperDocument
        validation_errors = PaperDocument.model_validate(document).semantic_validate()
    except Exception as e:
        validation_errors = [f"文档结构错误: {e}"]

    is_valid = len(validation_errors) == 0
    return clean_html, clean_css, validation_errors, is_valid


def ensure_publishable_document(document: dict) -> dict:
    """补齐基础结构，但绝不伪造答案；不完整内容必须进入人工审核。"""
    questions = document.get("questions") or []
    for question in questions:
        qtype = question.get("type")
        question.setdefault("needs_review", False)
        if qtype in ("single_choice", "multi_choice"):
            options = question.get("options") or []
            if not options:
                question["needs_review"] = True
            elif not question.get("correct_keys"):
                question["needs_review"] = True
        elif qtype == "true_false" and question.get("true_false_answer") is None:
            question["needs_review"] = True
        elif qtype == "fill_blank" and not question.get("acceptable_answers"):
            question["needs_review"] = True
        elif qtype == "subjective":
            has_answer = (
                question.get("reference_answer")
                or question.get("scoring_points")
                or question.get("explanation")
            )
            if not has_answer:
                question["needs_review"] = True
        if not question.get("answer_origin"):
            question["answer_origin"] = "needs_review"
        question.setdefault("answer_sources", [])
    return document


def build_fallback_document(title: str, preprocessed: dict, mode: str) -> dict:
    """在模型不可用时生成一版可审核草稿，保证上传-审核-发布流程不断线。"""
    def _flatten_preprocessed_text(prep: dict) -> str:
        chunks: list[str] = []
        for page in prep.get("pages", []):
            text = (page.get("text") or "").strip()
            if text:
                chunks.append(text)
        return "\n\n".join(chunks).strip()

    source_text = _flatten_preprocessed_text(preprocessed)
    lines = [line.strip() for line in source_text.splitlines() if line.strip()]
    if not lines:
        lines = ["暂未从源文件中提取到足够文字，请在审核页补充题干与答案。"]

    question_lines = lines[:12]
    questions = []
    for index, line in enumerate(question_lines, start=1):
        is_blank = "____" in line or "（" in line and "）" in line
        question_type = "fill_blank" if is_blank else "subjective"
        question = {
            "id": f"q{index}",
            "number": index,
            "type": question_type,
            "stem": line,
            "score": 0,
            "source_page": 1,
            "confidence": 0.45,
            "needs_review": True,
            "is_ai_generated": mode == "lecture_to_quiz",
            "explanation": "这是系统在模型不可用时生成的兜底草稿，请人工审核。",
        }
        if question_type == "fill_blank":
            question["acceptable_answers"] = [["请补充答案"]]
            question["match_rule"] = "contains"
        else:
            question["reference_answer"] = "请在审核页补充参考答案。"
            question["scoring_points"] = ["人工确认题意", "补全答案或评分要点"]
        questions.append(question)

    return {
        "title": title or "未命名试卷",
        "language": "zh-CN",
        "metadata": {
            "generated_by": "local_fallback",
            "mode": mode,
            "review_required": True,
            "source_excerpt": source_text[:1000],
        },
        "sections": [
            {
                "id": "s1",
                "title": "待审核题目",
                "source_page": 1,
                "question_ids": [q["id"] for q in questions],
            }
        ],
        "questions": questions,
    }
