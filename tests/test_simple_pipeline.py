import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from worker.pipeline.answering import build_answer_prompt
from worker.pipeline.simple_pipeline import build_simple_prompt


def test_faithful_prompt_attaches_visual_page_with_page_marker():
    prompt = build_simple_prompt(
        "=== 第 2 页 ===\\n设有两个序列。",
        "faithful_transcription",
        visual_pages=[{"page": 2, "image_b64": "aGVsbG8=", "mime": "image/png"}],
    )

    assert "图片中的公式、表格、图形" in prompt[0]["content"]
    content = prompt[1]["content"]
    assert isinstance(content, list)
    assert any("第 2 页" in part.get("text", "") for part in content)
    assert any(part.get("image_url", {}).get("url", "").endswith("aGVsbG8=") for part in content)


def test_text_only_prompt_remains_plain_text():
    prompt = build_simple_prompt("题目文本", "faithful_transcription")
    assert isinstance(prompt[1]["content"], str)


def test_answer_prompt_requires_exact_algorithm_semantics():
    prompt = build_answer_prompt([], {})
    assert "逐行核对填空或代码的语义" in prompt[0]["content"]
    assert "剪去对称分支" in prompt[0]["content"]
