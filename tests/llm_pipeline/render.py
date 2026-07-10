"""第 3 层：模板渲染层。

将第 2 层得到的 PaperDocument JSON 注入前端模板，生成可交互 HTML。
设计遵循：清晰(Clarity) / 内容优先(Deference) / 层次动效(Depth)。
（第 4 层可视化编辑器、第 5 层发布托管为后续扩展，这里给出接口占位。）
"""
import html
import logging
import os

logger = logging.getLogger("tier3.render")

_HERE = os.path.dirname(__file__)
TEMPLATE_PATH = os.path.join(_HERE, "template.html")

TYPE_TAG = {
    "single_choice": ("t-single", "单选"),
    "multi_choice": ("t-multi", "多选"),
    "true_false": ("t-true", "判断"),
    "fill_blank": ("t-fill", "填空"),
    "subjective": ("t-sub", "简答"),
}
SECTION_ICON = {
    "single_choice": "A", "multi_choice": "M",
    "true_false": "✓", "fill_blank": "—", "subjective": "?",
}


def render(doc: dict) -> str:
    sections = doc.get("sections", [])
    questions = doc.get("questions", [])

    # 按章节分组
    sec_qs = {}
    orphans = []
    sec_ids = {s.get("id"): set(s.get("question_ids", [])) for s in sections}
    for q in questions:
        qid = q.get("id", "")
        placed = False
        for sid, ids in sec_ids.items():
            if qid in ids:
                sec_qs.setdefault(sid, []).append(q)
                placed = True
                break
        if not placed:
            orphans.append(q)
    if not sections and questions:
        sections = [{"id": "default", "title": "", "question_ids": [q["id"] for q in questions]}]
        sec_qs = {"default": questions}

    parts = []
    si = 0
    for sec in sections:
        qs = sec_qs.get(sec.get("id", ""), [])
        if not qs:
            continue
        si += 1
        # 章节主类型着色
        tcount = {}
        for q in qs:
            t = q.get("type", "subjective")
            tcount[t] = tcount.get(t, 0) + 1
        main = max(tcount, key=tcount.get)
        ico = SECTION_ICON.get(main, "?")
        title = sec.get("title", "") or f"第 {si} 部分"
        parts.append(f'<section class="section"><div class="sec-head">'
                     f'<div class="sec-ico" style="background:var(--ink)">{ico}</div>'
                     f'<div class="sec-title">{html.escape(title)} '
                     f'<small>{len(qs)} 题</small></div></div>')
        for q in qs:
            parts.append(_render_question(q))
        parts.append("</section>")

    for q in orphans:
        parts.append(_render_question(q))

    questions_html = "\n".join(parts)

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        tpl = f.read()
    return (
        tpl.replace("{{TITLE}}", html.escape(doc.get("title", "试卷")))
        .replace("{{COUNT}}", str(len(questions)))
        .replace("{{QUESTIONS_HTML}}", questions_html)
    )


def _render_question(q: dict) -> str:
    qid = html.escape(str(q.get("id", "")))
    num = q.get("number", "")
    qtype = q.get("type", "subjective")
    stem = html.escape(q.get("stem", ""))
    correct = ",".join(html.escape(str(k)) for k in q.get("correct_keys", []))
    tag_cls, tag_txt = TYPE_TAG.get(qtype, ("t-sub", "简答"))

    out = [f'<div class="card" data-type="{qtype}" data-correct="{correct}">']
    out.append('<div class="q-top"><div class="q-num">%s</div><div class="q-body">' % num)
    out.append(f'<span class="q-type {tag_cls}">{tag_txt}</span>')
    out.append(f'<div class="q-stem">{stem}</div></div></div>')

    if qtype in ("single_choice", "multi_choice"):
        out.append('<div class="opts">')
        for opt in q.get("options", []):
            k = html.escape(str(opt.get("key", "")))
            t = html.escape(str(opt.get("text", "")))
            out.append(f'<div class="opt" data-k="{k}"><span class="k">{k}</span>'
                       f'<span class="t">{t}</span><span class="mark">✓</span></div>')
        out.append('</div>')

    elif qtype == "true_false":
        out.append('<div class="opts">')
        for k, t in [("T", "正确"), ("F", "错误")]:
            out.append(f'<div class="opt" data-k="{k}"><span class="k">{k}</span>'
                       f'<span class="t">{t}</span><span class="mark">✓</span></div>')
        out.append('</div>')

    elif qtype == "fill_blank":
        out.append('<div class="blank-row"><input class="blank" type="text" '
                   'placeholder="输入答案，回车或失焦判分" autocomplete="off">'
                   '<span class="blank-hint">输入后自动判分</span></div>')

    # 解析 / 解答 / 答案
    answer_text = q.get("answer_text", "") or " ".join(q.get("correct_keys", []))
    solution = q.get("solution", "")
    explanation = q.get("explanation", "")
    kps = q.get("knowledge_points", [])

    blocks = []
    # 填空题 / 简答：先给答案
    if qtype in ("fill_blank", "subjective") and answer_text.strip():
        blocks.append(f'<div class="blk ans ans-ans"><span class="lbl ans">▍答案</span>'
                       f'{_fmt(answer_text)}</div>')
    if solution.strip():
        blocks.append(f'<div class="blk sol"><span class="lbl sol">▍解答</span>'
                       f'{_fmt(solution)}</div>')
    if explanation.strip():
        blocks.append(f'<div class="blk exp"><span class="lbl">▍解析</span>'
                       f'{_fmt(explanation)}</div>')
    if kps:
        blocks.append('<div class="kp">' + "".join(
            f"<span>{html.escape(str(k))}</span>" for k in kps) + "</div>")

    if blocks:
        out.append('<button class="toggle"><svg viewBox="0 0 24 24" fill="none" '
                   'stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/>'
                   '</svg>查看解析</button>')
        out.append('<div class="ans"><div class="ans-box">' + "".join(blocks) + "</div></div>")

    out.append("</div>")
    return "\n".join(out)


def _fmt(text: str) -> str:
    """转义 HTML 并保留换行（\\n → <br>），数学公式 $...$ 交由 KaTeX 渲染。"""
    return html.escape(text or "").replace("\n", "<br>")


def publish(html_str: str, out_path: str) -> str:
    """第 5 层（发布托管）雏形：写出最终 HTML 文件。"""
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_str)
    return out_path


if __name__ == "__main__":
    sample = {
        "title": "概率统计小测",
        "sections": [{"id": "s1", "title": "第一章 概率基础", "question_ids": ["q1", "q2"]}],
        "questions": [
            {"id": "q1", "number": 1, "type": "single_choice",
             "stem": "设A、B为随机事件，则“A发生但B不发生”可表示为（）",
             "options": [{"key": "A", "text": "A∪B"}, {"key": "B", "text": "A∩$\\bar B$"},
                         {"key": "C", "text": "$\\bar A$∪$\\bar B$"}, {"key": "D", "text": "A∩B"}],
             "correct_keys": ["B"],
             "answer_text": "",
             "solution": "“A发生但B不发生”即 A 且 非B。\n公式：$A\\cap\\bar B$（或 $A-B$）。",
             "explanation": "易错：注意是“不发生B”，不是“都不发生”。\n区分 $A\\cap\\bar B$ 与 $\\overline{A\\cup B}$。",
             "knowledge_points": ["事件运算", "差事件"]},
            {"id": "q2", "number": 2, "type": "fill_blank",
             "stem": "若 $P(A)=0.6, P(B)=0.4, P(A|B)=0.8$，则 $P(B|A)=$____",
             "correct_keys": ["0.533", "8/15"],
             "answer_text": "$\\frac{8}{15}\\approx0.533$",
             "solution": "【答案】$\\frac{8}{15}$\n① $P(AB)=P(A|B)P(B)=0.8\\times0.4=0.32$\n② $P(B|A)=\\frac{P(AB)}{P(A)}=\\frac{0.32}{0.6}\\approx0.533$",
             "explanation": "考点：条件概率与乘法公式。\n易错：分母用错成 P(B)。",
             "knowledge_points": ["条件概率", "乘法公式"]},
        ],
    }
    h = render(sample)
    print("HTML 长度:", len(h))
    print("含卡片:", h.count('class="card"'))
