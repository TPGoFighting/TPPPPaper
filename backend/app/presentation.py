"""试卷 HTML 模板渲染器。

将 PaperDocument 渲染为精美的试卷 HTML 页面，匹配参考设计风格。
"""
import json
import re as _re
from typing import Any

# ── 完整的 CSS 样式（完全匹配参考设计）──
THEME_CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Noto+Sans+SC:wght@300;400;500;600;700;800&display=swap');

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #f8fafa;
  --bg-card: #ffffff;
  --text-primary: #1a1a2e;
  --text-secondary: #64748b;
  --text-tertiary: #94a3b8;
  --border: #e2e8f0;
  --accent: #0d9488;
  --accent-light: #f0fdfa;
  --accent-gradient: linear-gradient(135deg, #0d9488, #14b8a6);
  --success: #22c55e;
  --success-bg: #f0fdf4;
  --error: #ef4444;
  --tag-bg: #f1f5f9;
  --shadow-sm: 0 1px 3px rgba(0,0,0,.04);
  --shadow-md: 0 4px 16px rgba(0,0,0,.06);
  --radius-sm: 10px;
  --radius-md: 14px;
  --radius-lg: 20px;
}

html { scroll-behavior: smooth; }

body {
  font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg);
  background-image:
    linear-gradient(rgba(0,0,0,.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,.03) 1px, transparent 1px);
  background-size: 24px 24px;
  color: var(--text-primary);
  line-height: 1.7;
  overflow-x: hidden;
}

/* ─── HERO ─── */
.hero {
  position: relative;
  background: #ffffff;
  padding: 64px 24px 48px;
  text-align: center;
  border-bottom: 1px solid var(--border);
}
.hero-content { position: relative; max-width: 700px; margin: 0 auto; }

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--accent-light);
  border: 1px solid #ccfbf1;
  padding: 5px 14px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 500;
  color: var(--accent);
  letter-spacing: .5px;
}
.hero-badge .dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--accent);
  display: inline-block;
}
.live-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: var(--accent);
  display: inline-block;
}

.hero h1 {
  font-size: clamp(24px, 4.5vw, 40px);
  font-weight: 800;
  color: var(--text-primary);
  line-height: 1.25;
  margin-bottom: 10px;
}
.hero h1 span {
  color: var(--accent);
}
.hero-sub {
  font-size: clamp(13px, 2vw, 16px);
  color: var(--text-secondary);
  font-weight: 400;
  margin-bottom: 24px;
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}
.hero-meta span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
  background: var(--tag-bg);
  padding: 6px 14px;
  border-radius: 100px;
  border: 1px solid var(--border);
}
.hero-meta svg { width: 14px; height: 14px; opacity: .6; }

.hero-notice {
  max-width: 560px;
  margin: 20px auto 0;
  background: var(--accent-light);
  border: 1px solid #ccfbf1;
  border-radius: var(--radius-sm);
  padding: 10px 16px;
  font-size: 12px;
  color: var(--text-secondary);
  text-align: left;
  line-height: 1.6;
}

/* ─── PROGRESS BAR ─── */
.progress-wrap {
  position: sticky;
  top: 0;
  z-index: 100;
  background: rgba(255,255,255,.9);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  padding: 8px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.progress-wrap.scrolled { box-shadow: 0 1px 8px rgba(0,0,0,.04); }
.progress-label { font-size: 12px; font-weight: 600; color: var(--text-secondary); white-space: nowrap; letter-spacing: .3px; }
.progress-track { flex: 1; height: 4px; background: var(--border); border-radius: 4px; overflow: hidden; }
.progress-fill { height: 100%; width: 0%; background: var(--accent-gradient); border-radius: 4px; transition: width .6s ease; }
.progress-pct { font-size: 12px; font-weight: 700; color: var(--accent); min-width: 36px; text-align: right; }

/* ─── CONTAINER ─── */
.container { max-width: 840px; margin: 0 auto; padding: 28px 16px 60px; }

/* ─── SECTION ─── */
.section { margin-bottom: 36px; }

.section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding: 0 4px; }
.section-icon {
  width: 38px; height: 38px; border-radius: 11px;
  background: var(--accent-gradient);
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; color: #fff; flex-shrink: 0;
}
.section-icon.si-judge { background: linear-gradient(135deg,#22c55e,#16a34a); }
.section-icon.si-fill { background: linear-gradient(135deg,#f59e0b,#d97706); }
.section-icon.si-subjective { background: linear-gradient(135deg,#8b5cf6,#7c3aed); }
.section-title { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.section-title small { font-size: 13px; font-weight: 400; color: var(--text-secondary); margin-left: 8px; }

/* ─── CARD ─── */
.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  padding: 20px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  transition: box-shadow .25s, border-color .25s;
  position: relative;
  overflow: hidden;
}
.card:hover { box-shadow: var(--shadow-md); border-color: #cbd5e1; }

.q-num {
  display: inline-flex; align-items: center; justify-content: center;
  min-width: 26px; height: 26px;
  background: var(--accent-light); color: var(--accent);
  border-radius: 8px; font-size: 12px; font-weight: 700;
  margin-right: 8px; flex-shrink: 0;
}
.q-num.qn-judge { background: #f0fdf4; color: #22c55e; }
.q-num.qn-fill { background: #fefce8; color: #d97706; }
.q-num.qn-subjective { background: #f5f3ff; color: #8b5cf6; }
.q-text { font-size: 15px; font-weight: 500; line-height: 1.65; color: var(--text-primary); margin-bottom: 8px; }

.q-code {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px 16px;
  font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.75;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 10px 0;
  color: #334155;
}

/* ─── OPTIONS ─── */
.options { margin: 10px 0 4px; }
.opt {
  display: flex; align-items: baseline; gap: 8px;
  padding: 8px 12px; margin: 4px 0;
  border-radius: var(--radius-sm); font-size: 14px;
  cursor: pointer; transition: background .15s, border-color .15s;
  border: 1px solid transparent; position: relative;
}
.opt:hover { background: #f8fafc; border-color: var(--border); }
.opt .opt-label { font-weight: 600; color: var(--text-secondary); min-width: 22px; }
.opt.selected { background: var(--accent-light); border-color: var(--accent); }
.opt.selected .opt-label { color: var(--accent); }
.opt.correct { background: var(--success-bg); border-color: var(--success); }
.opt.correct .opt-label { color: var(--success); }
.opt.wrong { background: #fef2f2; border-color: #f87171; }
.opt.wrong .opt-label { color: #ef4444; }

/* ─── TOGGLE ANSWER ─── */
.toggle-btn {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 500; color: var(--accent);
  background: var(--accent-light); border: none;
  padding: 6px 14px; border-radius: 100px;
  cursor: pointer; transition: background .2s;
  margin-top: 8px; font-family: inherit;
}
.toggle-btn:hover { background: #ccfbf1; }
.toggle-btn svg { width: 14px; height: 14px; transition: transform .3s; }
.toggle-btn.active svg { transform: rotate(180deg); }

.answer-box {
  max-height: 0; overflow: hidden;
  transition: max-height .4s ease, opacity .3s ease, margin .3s ease;
  opacity: 0; margin-top: 0;
}
.answer-box.open { max-height: 3000px; opacity: 1; margin-top: 12px; }
.answer-content {
  background: #f8fafc;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 16px;
  font-size: 14px;
  line-height: 1.75;
}
.answer-content .ans-label {
  display: inline-block; font-weight: 700; color: var(--accent);
  margin-bottom: 6px; font-size: 13px; letter-spacing: .3px;
}
.answer-content .ans-body { color: var(--text-secondary); }
.answer-content .ans-body strong { color: var(--text-primary); }
.answer-content .ans-body code {
  background: #f1f5f9; padding: 1px 5px; border-radius: 4px;
  font-family: monospace; font-size: 12.5px; color: #333;
}

/* ─── ANSWER HIGHLIGHT ─── */
.answer-highlight {
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
  border: 1.5px solid #86efac;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 14px;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.answer-highlight .ans-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #22c55e;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  padding: 4px 12px;
  border-radius: 100px;
  white-space: nowrap;
  flex-shrink: 0;
}
.answer-highlight .ans-value {
  font-weight: 600;
  color: #166534;
  font-size: 15px;
  line-height: 1.6;
  word-break: break-all;
}
.solution-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: var(--accent);
  font-size: 13px;
  margin-bottom: 8px;
  letter-spacing: .3px;
}
.solution-label::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 14px;
  background: var(--accent);
  border-radius: 2px;
}
.solution-body {
  color: var(--text-secondary);
  line-height: 1.85;
  font-size: 14px;
  padding-left: 12px;
  border-left: 2px solid var(--border);
}
.solution-body strong { color: var(--text-primary); }
.solution-body code {
  background: #f1f5f9; padding: 1px 5px; border-radius: 4px;
  font-family: monospace; font-size: 12.5px; color: #333;
}
/* 解析中的段落标题 */
.solution-body .sol-section {
  display: inline-block;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 10px;
  margin-bottom: 4px;
  font-size: 13.5px;
}
.solution-body .sol-section.answer-hdr {
  color: var(--accent);
  background: var(--accent-light);
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 14px;
}
.solution-body .sol-section.steps-hdr { color: var(--accent); }
.solution-body .sol-section.tips-hdr { color: #d97706; }
/* 编号步骤 */
.solution-body .sol-step {
  display: block;
  padding: 2px 0 2px 8px;
  margin: 3px 0;
  border-left: 2px solid #e2e8f0;
  color: var(--text-secondary);
  line-height: 1.8;
}
.solution-body .sol-step .step-num {
  display: inline-block;
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 600;
  font-size: 12px;
  padding: 1px 7px;
  border-radius: 4px;
  margin-right: 6px;
}

/* ─── JUDGE ─── */
.judge-options { display: flex; gap: 10px; margin: 10px 0 4px; }
.judge-opt {
  flex: 1; padding: 10px; text-align: center;
  border: 2px solid var(--border); border-radius: var(--radius-sm);
  font-weight: 700; font-size: 16px; cursor: pointer;
  transition: all .2s; background: transparent; font-family: inherit;
}
.judge-opt:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-light); }
.judge-opt.selected { border-color: var(--accent); background: var(--accent-light); color: var(--accent); }
.judge-opt.correct { border-color: var(--success); background: var(--success-bg); color: #248a3d; }
.judge-opt.wrong { border-color: #f87171; background: #fef2f2; color: #ef4444; }

/* ─── FILL BLANK ─── */
.fill-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 8px 0; }
.fill-input {
  width: 100%; max-width: 300px;
  padding: 10px 14px;
  border: 2px solid var(--border); border-radius: var(--radius-sm);
  font-size: 14px; font-family: inherit;
  transition: border .2s, box-shadow .2s;
  background: #fff; color: var(--text-primary); outline: none;
}
.fill-input:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(0,113,227,.1); }
.fill-input.correct { border-color: var(--success); background: var(--success-bg); }
.fill-input.wrong { border-color: #f87171; background: #fef2f2; }

/* ─── TAG ─── */
.tag { display: inline-block; font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 100px; letter-spacing: .3px; }
.tag-point { background: #fef3c7; color: #d97706; margin-bottom: 8px; }
.tag-difficulty { background: #e8f4fd; color: #0071e3; }

/* ─── TABLE ─── */
.tbl-wrap { overflow-x: auto; margin: 10px 0; }
.tbl-wrap table { width: 100%; border-collapse: collapse; font-size: 13px; }
.tbl-wrap th, .tbl-wrap td { padding: 8px 12px; border: 1px solid var(--border); text-align: left; }
.tbl-wrap th { background: #f8f8fa; font-weight: 600; color: var(--text-secondary); font-size: 12px; }

/* ─── SCROLL TOP ─── */
.scroll-top {
  position: fixed; bottom: 24px; right: 24px;
  width: 46px; height: 46px; border-radius: 50%;
  background: var(--accent); color: #fff; border: none;
  cursor: pointer; box-shadow: var(--shadow-md);
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transform: translateY(16px); pointer-events: none;
  transition: opacity .35s, transform .35s; z-index: 99;
}
.scroll-top.show { opacity: 1; transform: translateY(0); pointer-events: auto; }
.scroll-top:hover { background: #0f766e; transform: translateY(-3px); }
.scroll-top svg { width: 20px; height: 20px; }

/* ─── FOOTER ─── */
.paper-footer {
  text-align: center;
  padding: 32px 0 16px;
  border-top: 1px solid var(--border);
  margin-top: 20px;
}
.paper-footer p {
  font-size: 13px;
  color: var(--text-tertiary);
  line-height: 1.8;
}

/* ─── DIVIDER ─── */
.section-divider {
  text-align: center;
  padding: 20px 0 0;
  position: relative;
}
.section-divider span {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-tertiary);
  background: var(--bg);
  padding: 4px 14px;
  border-radius: 100px;
  border: 1px solid var(--border);
  position: relative;
  z-index: 1;
  letter-spacing: 1px;
}

/* ─── SQL CARDS ─── */
.sql-card { border-left: 3px solid var(--accent) !important; }

/* ─── NOTICE CALLOUT ─── */
.callout {
  background: linear-gradient(135deg, #fffbeb, #fef9f0);
  border: 1px solid #fde68a;
  border-radius: var(--radius-sm);
  padding: 12px 16px;
  margin: 12px 0;
  font-size: 13px;
  color: #92400e;
  line-height: 1.6;
}
.callout strong { color: #d97706; }

/* ─── RESPONSIVE ─── */
@media (max-width: 600px) {
  .hero { padding: 56px 16px 44px; }
  .card { padding: 16px; border-radius: var(--radius-sm); }
  .card .q-text { font-size: 14px; }
  .opt { font-size: 13px; padding: 6px 10px; }
  .section-title { font-size: 16px; }
  .section-title small { display: block; margin-left: 0; font-size: 12px; margin-top: 2px; }
  .hero-meta span { font-size: 12px; padding: 4px 10px; }
  .container { padding: 16px 10px 40px; }
  .judge-opt { font-size: 14px; padding: 8px; }
  .fill-input { max-width: 100%; }
}
@media (max-width: 400px) {
  .hero h1 { font-size: 24px; }
  .card .q-code { font-size: 12px; padding: 10px; }
}

/* ─── SCROLLBAR ─── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #c7c7cc; border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: #a1a1a6; }
"""

# ── SVG 图标 ──
SVG_CHEVRON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>'
SVG_ARROW_UP = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>'
SVG_CLOCK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
SVG_SCORE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4"/></svg>'
SVG_QUESTIONS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/></svg>'

# ── 题目类型的中文名和图标颜色 ──
TYPE_LABELS: dict[str, str] = {
    "single_choice": "单项选择题",
    "multi_choice": "多项选择题",
    "true_false": "判断题",
    "fill_blank": "填空题",
    "subjective": "简答题",
}

SECTION_ICONS: dict[str, str] = {
    "single_choice": "A",
    "multi_choice": "M",
    "true_false": "✓",
    "fill_blank": "—",
    "subjective": "?",
}

# 判断题的选项标签
TRUE_FALSE_OPTIONS = [
    {"key": "T", "text": "T · 正确"},
    {"key": "F", "text": "F · 错误"},
]

# 题号颜色
QNUM_COLORS: dict[str, str] = {
    "single_choice": "background:var(--accent-light);color:var(--accent);",
    "multi_choice": "background:var(--accent-light);color:var(--accent);",
    "true_false": "background:#e8f8ed;color:#30d158;",
    "fill_blank": "background:#fef3c7;color:#d97706;",
    "subjective": "background:#f0e8ff;color:#bf5af2;",
}


def _escape_html(text: str) -> str:
    """转义 HTML 特殊字符。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _json_dumps(obj: Any) -> str:
    """将 Python 对象转为 JSON 字符串（用于内嵌 JS）。"""
    return json.dumps(obj, ensure_ascii=False)


# 常见的答案模式，按优先级排列
_ANSWER_PATTERNS = [
    r'【答案】\s*(.+?)(?:\n|$)',
    r'标准答案为[：:]\s*(.+?)(?:[。，；\n]|$)',
    r'故答案为[：:]\s*(.+?)(?:[。，；\n]|$)',
    r'答案为[：:]\s*(.+?)(?:[。，；\n]|$)',
    r'故结果[为是：:]\s*(.+?)(?:[。，；\n]|$)',
    r'结果[为是：:]\s*(.+?)(?:[。，；\n]|$)',
    r'故\s*(.+?)(?:[。]|$)',
]


def _extract_answer(explanation: str) -> str | None:
    """从解析文本中提取最终答案。返回 None 表示无法提取。"""
    if not explanation:
        return None
    text = explanation.strip()
    # 过滤掉明显不是答案的内容
    skip_keywords = ["OCR", "无法", "缺失", "题干信息不足", "无法解析", "无法作答", "无法计算"]
    if any(kw in text for kw in skip_keywords) and len(text) > 40:
        # 如果文本包含 OCR 纠错标记且较长，不提取
        # 但仍尝试匹配明确的答案模式
        for pat in _ANSWER_PATTERNS[:3]:  # 只用最严格的3个模式
            m = _re.search(pat, text)
            if m:
                answer = m.group(1).strip()
                if len(answer) <= 60 and not any(kw in answer for kw in skip_keywords):
                    return answer
        return None
    for pat in _ANSWER_PATTERNS:
        m = _re.search(pat, text)
        if m:
            answer = m.group(1).strip()
            # 过滤掉过长的匹配（可能是整段复制而非答案）
            if len(answer) <= 80 and not any(kw in answer for kw in skip_keywords):
                return answer
    # 如果文本很短（≤50字符），很可能整个就是答案
    if len(text) <= 50 and text and not any(kw in text for kw in skip_keywords):
        return text
    return None


# 解析段落标题模式
_SECTION_RE = _re.compile(r'【(答案|解题步骤|易错提醒|注意|提示)】')
_STEP_RE = _re.compile(r'^(\d+)\.\s*(.+)$')


def _format_explanation(text: str) -> str:
    """将结构化解析文本渲染为带样式的 HTML。

    支持：
    - 【答案】/【解题步骤】/【易错提醒】段落标题
    - 编号步骤（1. 2. 3. ...）带步骤徽章
    - 普通文本保留换行
    """
    if not text:
        return ""

    lines = text.split('\n')
    parts: list[str] = []
    current_section = ""  # "answer" | "steps" | "tips" | ""

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # 检查是否为段落标题
        section_match = _SECTION_RE.match(stripped)
        if section_match:
            label = section_match.group(1)
            remaining = stripped[section_match.end():].strip()
            if label == "答案":
                current_section = "answer"
                parts.append(f'<span class="sol-section answer-hdr">📌 {_escape_html(label)}</span>')
                if remaining:
                    parts.append(f'<div style="margin:4px 0 8px;font-weight:600;color:#166534;">{_escape_html(remaining)}</div>')
            elif label in ("解题步骤",):
                current_section = "steps"
                parts.append(f'<span class="sol-section steps-hdr">📝 {_escape_html(label)}</span>')
                if remaining:
                    parts.append(f'<div style="margin:2px 0;color:var(--text-secondary);">{_escape_html(remaining)}</div>')
            else:
                current_section = "tips"
                parts.append(f'<span class="sol-section tips-hdr">⚠️ {_escape_html(label)}</span>')
                if remaining:
                    parts.append(f'<div style="margin:2px 0;color:#92400e;">{_escape_html(remaining)}</div>')
            continue

        # 检查是否为编号步骤
        step_match = _STEP_RE.match(stripped)
        if step_match and current_section == "steps":
            num = step_match.group(1)
            content = step_match.group(2)
            parts.append(
                f'<span class="sol-step">'
                f'<span class="step-num">{_escape_html(num)}</span>'
                f'{_escape_html(content)}</span>'
            )
            continue

        # 普通文本行
        parts.append(f'{_escape_html(stripped)}<br>')

    return '\n'.join(parts)


def _render_question(q: dict, q_number: int, q_type: str, qid: str) -> str:
    """渲染单个题目为 HTML 卡片。"""
    parts = []
    stem = _escape_html(q.get("stem", ""))
    explanation = _escape_html(q.get("explanation", ""))
    reference_answer = _escape_html(q.get("reference_answer", ""))
    options = q.get("options", [])
    correct_keys = q.get("correct_keys", [])
    score = q.get("score") or 0
    qnum_style = QNUM_COLORS.get(q_type, "")
    # 将内联样式转换为 CSS 类名
    qnum_class = "q-num"
    if q_type == "true_false":
        qnum_class += " qn-judge"
    elif q_type == "fill_blank":
        qnum_class += " qn-fill"
    elif q_type == "subjective":
        qnum_class += " qn-subjective"

    parts.append(f'<div class="card" data-qid="{_escape_html(qid)}">')

    # 题干
    parts.append(f'<div class="q-text"><span class="{qnum_class}">{q_number}</span>{stem}</div>')

    # 分值标签
    if score:
        parts.append(f'<span class="tag tag-point">{score} 分</span>')

    # 选项渲染
    if q_type == "true_false":
        correct_str = _json_dumps(correct_keys[0] if correct_keys else "")
        parts.append(f'<div class="judge-options" data-correct="{_escape_html(correct_keys[0] if correct_keys else "")}">')
        for tf_opt in TRUE_FALSE_OPTIONS:
            parts.append(f'<button class="judge-opt" data-val="{tf_opt["key"]}" onclick="selectJudge(this)">{_escape_html(tf_opt["text"])}</button>')
        parts.append('</div>')

    elif q_type in ("single_choice", "multi_choice"):
        if options:
            parts.append('<div class="options">')
            for opt in options:
                key = _escape_html(opt.get("key", ""))
                text = _escape_html(opt.get("text", ""))
                parts.append(f'<div class="opt" data-opt="{key}"><span class="opt-label">{key}.</span>{text}</div>')
            parts.append('</div>')

    elif q_type == "fill_blank":
        acceptable = q.get("acceptable_answers", [])
        if acceptable:
            # acceptable_answers 是 list[list[str]]，扁平化后用 | 连接
            flat = []
            for item in acceptable:
                if isinstance(item, list):
                    flat.extend(str(a) for a in item)
                else:
                    flat.append(str(item))
            answer = "|".join(flat)
        else:
            answer = ""
        parts.append('<div class="fill-row">')
        parts.append(f'<span style="font-size:14px;color:var(--text-secondary);">答案：</span>')
        parts.append(f'<input class="fill-input" data-answer="{_escape_html(answer)}" placeholder="输入答案" style="max-width:300px;">')
        parts.append('</div>')

    elif q_type == "subjective":
        pass  # 简答题只显示题干和解析

    # 解析区域
    raw_explanation = q.get("explanation", "")
    raw_reference = q.get("reference_answer", "")
    answer_content = explanation or reference_answer

    if answer_content or correct_keys:
        # 确定最终答案：优先 correct_keys，其次 reference_answer，最后从解析提取
        answer_value = ""
        if correct_keys:
            answer_value = "，".join(_escape_html(k) for k in correct_keys)
        elif raw_reference:
            answer_value = _escape_html(raw_reference)
        else:
            extracted = _extract_answer(raw_explanation)
            if extracted:
                answer_value = _escape_html(extracted)

        # 构建按钮标签（不预览答案，避免未展开时泄露）
        answer_label = "查看解析"

        parts.append(
            f'<button class="toggle-btn" onclick="toggleAnswer(this)">'
            f'{SVG_CHEVRON} {_escape_html(answer_label)}</button>'
        )
        parts.append('<div class="answer-box"><div class="answer-content">')

        # 隐藏的 ans-label 供 JS 解析正确答案映射
        if answer_value:
            parts.append(
                f'<div class="ans-label" style="display:none;">答案：{answer_value}</div>'
            )

        # 醒目的答案标记
        if answer_value:
            parts.append('<div class="answer-highlight">')
            parts.append('<span class="ans-tag">📌 答案</span>')
            parts.append(f'<span class="ans-value">{answer_value}</span>')
            parts.append('</div>')

        # 解题过程（结构化渲染）
        if raw_explanation:
            parts.append('<div class="solution-label">解题过程</div>')
            formatted = _format_explanation(raw_explanation)
            parts.append(f'<div class="solution-body">{formatted}</div>')

        parts.append('</div></div>')

    parts.append('</div>')
    return "\n".join(parts)


# ── 交互式 JS（完全匹配参考设计）──
INTERACTIVE_JS = """
<script>
(function(){
  /* ─── Toggle answer ─── */
  window.toggleAnswer = function(btn) {
    var box = btn.nextElementSibling;
    var isOpen = box.classList.contains('open');
    box.classList.toggle('open');
    btn.classList.toggle('active');
    if (!isOpen) setTimeout(function() { btn.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); }, 100);
    updateProgress();
  };

  /* ─── Single / Multi choice ─── */
  // 构建正确答案映射
  var CORRECT_MAP = {};
  document.querySelectorAll('.card').forEach(function(card) {
    var qid = card.getAttribute('data-qid');
    if (!qid) return;
    var answerBox = card.querySelector('.answer-box .ans-label');
    if (!answerBox) return;
    var labelText = answerBox.textContent || '';
    var match = labelText.match(/答案[：:]\\s*(.+)/);
    if (match) {
      // 可能多个答案用逗号/顿号分隔
      CORRECT_MAP[qid] = match[1].trim().split(/[，,、]/).filter(Boolean);
    }
  });

  document.querySelectorAll('.opt').forEach(function(opt) {
    opt.addEventListener('click', function() {
      var parent = this.closest('.options');
      var card = this.closest('.card');
      var qid = card.getAttribute('data-qid');
      var correct = CORRECT_MAP[qid] || [];

      // 判断是否为多选题（多个正确答案）
      if (correct.length > 1) {
        // 多选：切换选中状态
        this.classList.toggle('selected');
      } else {
        // 单选：清除其他选项
        parent.querySelectorAll('.opt').forEach(function(o) { o.classList.remove('selected','correct','wrong'); });
        this.classList.add('selected');
      }

      // 显示正确答案（如果答案可见）
      var answerBox = card.querySelector('.answer-box');
      if (answerBox && answerBox.classList.contains('open') && correct.length > 0) {
        parent.querySelectorAll('.opt').forEach(function(o) {
          o.classList.remove('correct','wrong');
          if (correct.indexOf(o.getAttribute('data-opt')) >= 0) {
            o.classList.add('correct');
          }
        });
        if (correct.length === 1) {
          var selected = parent.querySelector('.opt.selected');
          if (selected && selected.getAttribute('data-opt') !== correct[0]) {
            selected.classList.add('wrong');
          }
        }
      }

      updateProgress();
    });
  });

  /* ─── Judge ─── */
  window.selectJudge = function(btn) {
    var parent = btn.closest('.judge-options');
    var card = btn.closest('.card');
    parent.querySelectorAll('.judge-opt').forEach(function(o) { o.classList.remove('selected','correct','wrong'); });
    btn.classList.add('selected');
    var correct = parent.getAttribute('data-correct');
    var val = btn.getAttribute('data-val');
    if (val === correct) {
      btn.classList.add('correct');
    } else {
      btn.classList.add('wrong');
      parent.querySelectorAll('.judge-opt').forEach(function(o) {
        if (o.getAttribute('data-val') === correct) o.classList.add('correct');
      });
    }
    var toggleBtn = card.querySelector('.toggle-btn');
    var answerBox = card.querySelector('.answer-box');
    if (toggleBtn && answerBox && !answerBox.classList.contains('open')) toggleBtn.click();
    updateProgress();
  };

  /* ─── Fill blank ─── */
  document.querySelectorAll('.fill-input').forEach(function(inp) {
    inp.addEventListener('blur', function() {
      var ans = this.getAttribute('data-answer').replace(/'/g,'').trim().toLowerCase();
      var val = this.value.replace(/'/g,'').trim().toLowerCase();
      this.classList.remove('correct','wrong');
      if (!val) return;
      // 支持多个答案（用 | 分隔）
      var answers = ans.split('|').map(function(s) { return s.trim(); });
      if (answers.indexOf(val) >= 0 || this.getAttribute('data-answer').trim() === this.value.trim()) {
        this.classList.add('correct');
      } else {
        this.classList.add('wrong');
      }
      updateProgress();
    });
    inp.addEventListener('focus', function() { this.classList.remove('correct','wrong'); });
  });

  /* ─── Progress ─── */
  function updateProgress() {
    var totalCards = 0;
    var answered = 0;
    document.querySelectorAll('.card').forEach(function(card) {
      // 只统计有交互的题目
      var opts = card.querySelectorAll('.opt');
      var judgeOpts = card.querySelectorAll('.judge-opt');
      var fills = card.querySelectorAll('.fill-input');
      var toggleBtn = card.querySelector('.toggle-btn');
      if (opts.length > 0 || judgeOpts.length > 0 || fills.length > 0) {
        totalCards++;
        if (card.querySelector('.opt.selected') || card.querySelector('.judge-opt.selected')) {
          answered++;
        } else if (fills.length > 0) {
          var allFilled = true;
          fills.forEach(function(f) { if (!f.value.trim()) allFilled = false; });
          if (allFilled) answered++;
        }
      }
    });
    if (totalCards === 0) return;
    var pct = Math.round((answered / totalCards) * 100);
    var fill = document.getElementById('progressFill');
    var pctEl = document.getElementById('progressPct');
    if (fill) fill.style.width = pct + '%';
    if (pctEl) pctEl.textContent = pct + '%';
  }

  /* ─── Scroll top + sticky ─── */
  window.addEventListener('scroll', function() {
    var btn = document.getElementById('scrollTop');
    if (btn) {
      if (window.scrollY > 300) btn.classList.add('show');
      else btn.classList.remove('show');
    }
    var wrap = document.getElementById('progressWrap');
    if (wrap) {
      if (window.scrollY > 80) wrap.classList.add('scrolled');
      else wrap.classList.remove('scrolled');
    }
  });
})();
</script>
"""


def render_paper(document: dict[str, Any], title: str = "试卷") -> tuple[str, str]:
    """将 PaperDocument 渲染为 HTML 和 CSS。

    Returns:
        (presentation_html, theme_css)
    """
    doc_title = document.get("title", "") or title
    questions = document.get("questions", [])
    sections = document.get("sections", [])

    # 按章节分组题目
    section_questions: dict[str, list] = {s.get("id", ""): [] for s in sections}
    orphan_questions: list = []
    section_q_ids: dict[str, set] = {}
    for s in sections:
        section_q_ids[s.get("id", "")] = set(s.get("question_ids", []))

    for q in questions:
        qid = q.get("id", "")
        placed = False
        for sid, qids in section_q_ids.items():
            if qid in qids:
                section_questions.setdefault(sid, []).append(q)
                placed = True
                break
        if not placed:
            orphan_questions.append(q)

    # 如果没有章节，所有题目放到一个默认章节
    if not sections and questions:
        sections = [{"id": "default", "title": "", "question_ids": [q["id"] for q in questions]}]
        section_questions = {"default": questions}
        orphan_questions = []

    # 计算统计信息
    total_questions = len(questions)
    total_score = sum(q.get("score") or 0 for q in questions)

    html_parts = []

    # ── Hero ──
    html_parts.append(f"""<header class="hero">
  <div class="hero-content">
    <div class="hero-eyebrow">
      <div class="hero-badge"><span class="live-dot"></span> {_escape_html(doc_title)}</div>
    </div>
    <h1>{_escape_html(doc_title)}<br></h1>
    <p class="hero-sub">共 {total_questions} 题 · 满分 {total_score} 分</p>
    <div class="hero-meta">
      <span>{SVG_CLOCK} 120 分钟</span>
      <span>{SVG_SCORE} 满分 {total_score} 分</span>
      <span>{SVG_QUESTIONS} {len(sections)} 大题型</span>
    </div>
    <div class="hero-notice">
      📌 本试卷由 AI 自动生成，点击题目选项即可交互答题，点击「查看解析」展开完整答案与解析内容。
    </div>
  </div>
</header>""")

    # ── Progress Bar ──
    html_parts.append("""<div class="progress-wrap" id="progressWrap">
  <span class="progress-label">答题进度</span>
  <div class="progress-track"><div class="progress-fill" id="progressFill"></div></div>
  <span class="progress-pct" id="progressPct">0%</span>
</div>""")

    # ── Main Content ──
    html_parts.append('<main class="container">')

    # ── 渲染每个章节 ──
    q_counter = 0
    section_icons_list = ["A", "✓", "—", "?", "&gt;_"]
    for si, section in enumerate(sections):
        sec_title = section.get("title", "")
        sec_qs = section_questions.get(section.get("id", ""), [])
        if not sec_qs:
            continue

        # 确定章节的主要题型（用于图标）
        type_counts: dict[str, int] = {}
        for q in sec_qs:
            t = q.get("type", "subjective")
            type_counts[t] = type_counts.get(t, 0) + 1
        main_type = max(type_counts, key=type_counts.get) if type_counts else "subjective"
        icon = SECTION_ICONS.get(main_type, "?")
        icon_class = ""
        if main_type == "true_false":
            icon_class = " si-judge"
        elif main_type == "fill_blank":
            icon_class = " si-fill"
        elif main_type == "subjective":
            icon_class = " si-subjective"

        # 计算章节分值
        sec_score = sum(q.get("score") or 0 for q in sec_qs)

        # 章节分隔线（非第一个章节时添加）
        if si > 0 and sec_title:
            html_parts.append(f'<div class="section-divider"><span>{_escape_html(sec_title)}</span></div>')

        html_parts.append(f"""<section class="section" id="sec{si + 1}">
    <div class="section-header">
      <div class="section-icon{icon_class}">{icon}</div>
      <div class="section-title">{_escape_html(sec_title)} <small>共 {len(sec_qs)} 题 · {sec_score} 分</small></div>
    </div>""")

        for q in sec_qs:
            q_counter += 1
            q_type = q.get("type", "subjective")
            qid = q.get("id", str(q_counter))
            html_parts.append(_render_question(q, q_counter, q_type, qid))

        html_parts.append('</section>')

    # ── 渲染孤儿题目 ──
    if orphan_questions:
        html_parts.append('<section class="section"><div class="section-header"><div class="section-icon">?</div><div class="section-title">其他题目</div></div>')
        for q in orphan_questions:
            q_counter += 1
            q_type = q.get("type", "subjective")
            qid = q.get("id", str(q_counter))
            html_parts.append(_render_question(q, q_counter, q_type, qid))
        html_parts.append('</section>')

    # ── Footer ──
    html_parts.append(f"""<div class="paper-footer">
    <p>
      {_escape_html(doc_title)}<br>
      答案及解析仅供参考，祝考试顺利
    </p>
  </div>""")

    html_parts.append('</main>')

    # ── Scroll to Top ──
    html_parts.append(f"""<button class="scroll-top" id="scrollTop" onclick="window.scrollTo({{top:0,behavior:'smooth'}})" aria-label="回到顶部">
  {SVG_ARROW_UP}
</button>""")

    # ── 交互 JS ──
    html_parts.append(INTERACTIVE_JS)

    presentation_html = "\n".join(html_parts)
    return presentation_html, THEME_CSS