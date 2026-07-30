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
    """在模型不可用或兜底时生成结构化试卷草稿，支持自动解析中文试卷大题、选择题选项与参考答案。"""
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

    import re
    sec_pattern = re.compile(r'^[一二三四五六七八九十]+\s*[、. ]\s*(.+)')
    q_pattern = re.compile(r'^(\d+)\s*[.、\s]\s*(.+)')
    opt_pattern = re.compile(r'^([A-D])\s*[.、\s]\s*(.+)')

    sections = []
    questions = []
    current_sec = None
    current_q = None
    q_counter = 1

    main_lines = []
    ans_lines = []
    in_answer_section = False

    for line in lines:
        if ("参考答案" in line or "详细解答" in line) and len(line) < 40:
            in_answer_section = True
            continue
        if in_answer_section:
            ans_lines.append(line)
        else:
            main_lines.append(line)

    for line in main_lines:
        sec_match = sec_pattern.match(line)
        if sec_match:
            sec_id = f"s{len(sections) + 1}"
            current_sec = {
                "id": sec_id,
                "title": line,
                "source_page": 1,
                "question_ids": [],
            }
            sections.append(current_sec)
            current_q = None
            continue

        q_match = q_pattern.match(line)
        if q_match:
            qid = f"q{q_counter}"
            num = int(q_match.group(1))
            stem = q_match.group(2).strip()

            is_fill = "____" in stem or ("（" in stem and "）" in stem) or ("(" in stem and ")" in stem)
            q_type = "fill_blank" if is_fill else "subjective"

            current_q = {
                "id": qid,
                "number": num,
                "type": q_type,
                "stem": stem,
                "score": 0,
                "source_page": 1,
                "confidence": 0.85,
                "needs_review": False,
                "is_ai_generated": mode == "lecture_to_quiz",
            }
            if q_type == "fill_blank":
                current_q["acceptable_answers"] = [["请复核答案"]]
                current_q["match_rule"] = "contains"
            else:
                current_q["reference_answer"] = ""
                current_q["scoring_points"] = []

            questions.append(current_q)
            q_counter += 1
            if current_sec:
                current_sec["question_ids"].append(qid)
            continue

        opt_match = opt_pattern.match(line)
        if current_q and opt_match:
            current_q["type"] = "single_choice"
            if "options" not in current_q:
                current_q["options"] = []
            key = opt_match.group(1)
            text = opt_match.group(2).strip()
            current_q["options"].append({"key": key, "text": text})
            continue

        if current_q:
            current_q["stem"] += " " + line

    if not questions:
        question_lines = lines[:12]
        for index, line in enumerate(question_lines, start=1):
            is_blank = "____" in line or ("（" in line and "）" in line)
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

    if not sections:
        sections = [{
            "id": "s1",
            "title": "试卷题目",
            "source_page": 1,
            "question_ids": [q["id"] for q in questions],
        }]

    ans_text = " ".join(ans_lines)
    for q in questions:
        if q["type"] == "single_choice":
            m = re.search(r'\b' + str(q["number"]) + r'\s*[\.、\s]\s*([A-D])\b', ans_text)
            if m:
                q["correct_keys"] = [m.group(1)]
            else:
                q["correct_keys"] = ["A"]
                q["needs_review"] = True

    return {
        "title": title or "未命名试卷",
        "language": "zh-CN",
        "metadata": {
            "generated_by": "smart_fallback_parser",
            "mode": mode,
            "review_required": True,
            "source_excerpt": source_text[:1000],
        },
        "sections": sections,
        "questions": questions,
    }
