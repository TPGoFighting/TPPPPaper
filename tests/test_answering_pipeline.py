import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.schemas import PaperDocument
from worker.pipeline.answering import apply_answer_payload, build_answer_prompt, research_questions
from worker.pipeline.sanitize import ensure_publishable_document


def _document():
    return {
        "title": "操作系统测试",
        "sections": [{"id": "s1", "title": "", "question_ids": ["q_1", "q_2"]}],
        "questions": [
            {
                "id": "q_1", "number": 1, "type": "single_choice",
                "stem": "successful fork() returns?", "score": 1,
                "options": [{"key": "A", "text": "always 0"}, {"key": "E", "text": "different"}],
                "source_page": 2,
            },
            {
                "id": "q_2", "number": 2, "type": "subjective",
                "stem": "What is an MMU?", "score": 3, "source_page": 7,
            },
        ],
    }


def test_answer_payload_keeps_source_question_and_records_web_evidence():
    document = _document()
    payload = {
        "answers": [
            {
                "id": "q_1", "correct_keys": ["E"], "explanation": "父子进程的返回值不同。",
                "knowledge_points": ["fork"], "confidence": 0.95,
                "answer_origin": "web_researched", "needs_review": False,
                "answer_sources": [{"title": "man fork", "url": "https://man7.org/linux/man-pages/man2/fork.2.html", "snippet": "fork return values"}],
            },
            {
                "id": "q_2", "reference_answer": "MMU 是地址翻译硬件。",
                "scoring_points": ["定义", "虚拟地址到物理地址转换"],
                "explanation": "它执行地址转换并支持保护。", "knowledge_points": ["virtual memory"],
                "confidence": 0.9, "answer_origin": "model_knowledge", "needs_review": False,
                "answer_sources": [],
            },
        ]
    }

    result = apply_answer_payload(document, payload, research_used=True)

    assert result["questions"][0]["stem"] == "successful fork() returns?"
    assert result["questions"][0]["options"][1]["key"] == "E"
    assert result["questions"][0]["correct_keys"] == ["E"]
    assert result["questions"][0]["answer_sources"][0]["url"].startswith("https://")
    assert result["questions"][1]["reference_answer"].startswith("MMU")
    assert result["questions"][1]["needs_review"] is True
    assert PaperDocument.model_validate(result).semantic_validate() == []


def test_missing_answers_are_not_replaced_with_fake_defaults():
    document = ensure_publishable_document(_document())
    errors = PaperDocument.model_validate(document).semantic_validate()

    assert document["questions"][0].get("correct_keys", []) == []
    assert document["questions"][1].get("reference_answer", "") == ""
    assert any("缺少正确答案" in error for error in errors)
    assert any("缺少参考答案" in error for error in errors)


def test_prompt_separates_model_knowledge_from_web_research():
    prompt = build_answer_prompt(_document()["questions"], {})
    assert "不得把模型推导的答案说成原卷答案" in prompt[0]["content"]
    assert "model_knowledge" in prompt[0]["content"]
    assert "q_1" in prompt[1]["content"]


def test_unconfigured_research_does_not_issue_network_requests():
    assert asyncio.run(research_questions(_document()["questions"], provider="", api_key="")) == {}
