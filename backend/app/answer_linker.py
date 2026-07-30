"""Answer-key linker for 含答案 (questions-with-answer-key) exam papers.

Problem this solves
-------------------
Many Chinese exam papers (e.g. "操作系统试卷B（含答案）") keep the questions on
the early pages and a separate "参考答案及详细解答" section on later pages. The
questions and their answers are therefore in *different* pages, and question
numbers restart for every 大题 (一、二、三、四 …). A naïve "global question
number" lookup therefore mis-links answers.

This module detects the answer-key section and links each answer back to its
question by ``(section index, per-section question number)`` — the only reliable
key. It back-fills ``correct_keys`` / ``acceptable_answers`` / ``reference_answer``
/ ``explanation`` / ``scoring_points`` that the LLM or fallback parser left empty
or flagged for review. It never deletes an answer the model already produced
confidently; it only fills gaps.

It is intentionally dependency-free (stdlib only) so it can run inside the worker
without any LLM call.
"""
from __future__ import annotations

import re
from typing import Any

# ── Regexes ────────────────────────────────────────────────────────────────
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+)\s*[、.．]\s*(.+)$")
# Negative lookahead: a list like "0、1、2、3" must not be read as a question.
Q_RE = re.compile(r"^(\d+)[.、]\s*(?!\d[.、])(.+)$")
OPT_RE = re.compile(r"^([A-Da-d])\s*[.、]\s*(.+)$")
ANSWER_SECTION_RE = re.compile(r"参考答案|详细解答|答案解析|试题答案")
FOOTER_RE = re.compile(r"^第\s*\d+\s*页$")


def detect_answer_section_start(pages: list[dict]) -> int | None:
    """Return the 0-based index of the first page that introduces an answer key."""
    for i, page in enumerate(pages):
        text = (page.get("text") or "").strip()
        if ANSWER_SECTION_RE.search(text):
            return i
    return None


def _detect_type(title: str) -> str:
    if "单项选择" in title:
        return "single_choice"
    if "多项选择" in title:
        return "multi_choice"
    if "判断" in title:
        return "true_false"
    if "填空" in title:
        return "fill_blank"
    return "subjective"


def parse_answers_from_text(text: str) -> list[dict]:
    """Parse the answer-key text into sections; each has ``answers`` by number."""
    sections: list[dict] = []
    cur = None
    cur_a = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        sm = SECTION_RE.match(line)
        if sm:
            cur = {"title": sm.group(2).strip(), "type": _detect_type(sm.group(2)), "answers": []}
            sections.append(cur)
            cur_a = None
            continue
        if cur is None:
            continue
        qm = Q_RE.match(line)
        if qm:
            cur_a = {"number": int(qm.group(1)), "raw": [qm.group(2).strip()]}
            cur["answers"].append(cur_a)
            continue
        if cur_a is None:
            continue
        if FOOTER_RE.match(line):
            continue
        cur_a["raw"].append(line)
    return sections


def extract_choice_answer(raw: list[str]):
    first = raw[0]
    m = re.match(r"^([A-Da-d](?:\s*[、,，]?\s*[A-Da-d])*)", first)
    keys: list[str] = []
    if m:
        keys = [k.upper() for k in re.findall(r"[A-Da-d]", m.group(1))]
        rest = first[m.end():]
    else:
        rest = first
    joined = " ".join(([rest.strip()] + [ln.strip() for ln in raw[1:]]))
    paren = re.search(r"[（(](.+?)[)）]", joined)
    explanation = paren.group(1).strip() if paren else joined.strip()
    return keys, explanation


def extract_fill_answer(raw: list[str], stem: str):
    answer_text = " ".join(ln.strip() for ln in raw if ln.strip())
    blanks = len(re.findall(r"_{2,}|（\s*）|\(\)", stem))
    if blanks <= 1:
        parts = [answer_text]
    else:
        parts = re.split(r"\s*[、,，]\s*|\s{2,}", answer_text)
        parts = [p for p in parts if p]
        while len(parts) < blanks:
            parts.append("")
    return [[p] for p in parts], answer_text


def derive_scoring_points(text: str) -> list[str]:
    parts = re.split(r"[①②③④⑤⑥⑦⑧⑨⑩]", text)
    parts = [p.strip(" 、，。：:（）()\n") for p in parts if p.strip()]
    parts = [p for p in parts if p and not p.endswith("：") and not p.endswith(":")]
    if len(parts) >= 2:
        return parts[:10]
    parts = re.split(r"[（(]\s*\d+\s*[)）]", text)
    parts = [p.strip() for p in parts if p.strip()]
    parts = [p for p in parts if not p.endswith("：") and not p.endswith(":")]
    if len(parts) >= 2:
        return parts[:10]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) >= 2:
        return lines[:8]
    return ["要点完整", "结论正确"]


def link_answers(document: dict, preprocessed: dict) -> dict:
    """Back-fill answers into ``document`` from the source answer-key section.

    Only fills fields that are empty or on questions flagged ``needs_review``.
    Returns the (mutated) document.
    """
    pages = preprocessed.get("pages") or []
    start = detect_answer_section_start(pages)
    if start is None:
        return document

    answer_text = "\n".join((p.get("text") or "") for p in pages[start:])
    answer_sections = parse_answers_from_text(answer_text)
    if not answer_sections:
        return document

    # index: (section_index, per-section number) -> answer dict
    ans_lookup: dict[tuple[int, int], dict] = {}
    for si, sec in enumerate(answer_sections):
        for a in sec["answers"]:
            ans_lookup[(si, a["number"])] = a

    questions = document.get("questions") or []
    q_by_id = {q.get("id"): q for q in questions}

    for si, section in enumerate(document.get("sections") or []):
        if si >= len(answer_sections):
            break
        qids = section.get("question_ids") or []
        for ordinal, qid in enumerate(qids, start=1):
            q = q_by_id.get(qid)
            if not q:
                continue
            ans = ans_lookup.get((si, ordinal))
            if not ans:
                continue
            qtype = q.get("type")
            needs = q.get("needs_review") or (q.get("answer_origin") == "needs_review")
            if qtype in ("single_choice", "multi_choice"):
                if needs or not q.get("correct_keys") or not q.get("explanation"):
                    keys, explanation = extract_choice_answer(ans["raw"])
                    if keys and (needs or not q.get("correct_keys")):
                        q["correct_keys"] = keys
                    if explanation and (needs or not q.get("explanation")):
                        opts = {o.get("key"): o.get("text", "") for o in q.get("options", [])}
                        label = "、".join(
                            f"{k}（{opts.get(k, '')}）" for k in keys if k in opts
                        )
                        q["explanation"] = (
                            f"正确答案：{label}。\n{explanation}" if label else explanation
                        )
            elif qtype == "fill_blank":
                if needs or not q.get("acceptable_answers"):
                    acceptable, answer_text_q = extract_fill_answer(ans["raw"], q.get("stem", ""))
                    q["acceptable_answers"] = acceptable
                    q["match_rule"] = "contains"
                    q["reference_answer"] = answer_text_q
                    q["explanation"] = answer_text_q
            else:  # subjective
                if needs or not q.get("reference_answer"):
                    solution = "\n".join(ln.strip() for ln in ans["raw"] if ln.strip())
                    q["reference_answer"] = solution
                    q["explanation"] = solution
                    if not q.get("scoring_points"):
                        q["scoring_points"] = derive_scoring_points(solution)
            if ans_lookup.get((si, ordinal)) is not None:
                q["answer_origin"] = "model_knowledge"
                q["needs_review"] = False

    return document
