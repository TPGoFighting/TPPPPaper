"""Schema validation tests — SPEC §5, §6.

Covers:
- PaperDocument Pydantic validation (required fields, types, constraints)
- Semantic validation (correct_keys vs options, type-specific requirements)
- Fault injection (duplicate IDs, missing fields, invalid references)
- Section → question reference integrity
- Auto-wrapping of acceptable_answers
"""

import pytest
from pydantic import ValidationError


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _make_question(**overrides):
    """Create a minimal valid question dict, with optional overrides."""
    base = {
        "id": "q1",
        "type": "single_choice",
        "stem": "What is 1+1?",
        "options": [{"key": "A", "text": "1"}, {"key": "B", "text": "2"}],
        "correct_keys": ["B"],
        "explanation": "Basic arithmetic",
    }
    base.update(overrides)
    return base


def _make_document(**overrides):
    """Create a minimal valid PaperDocument dict, with optional overrides."""
    base = {
        "title": "Test Paper",
        "questions": [_make_question()],
        "sections": [{"id": "s1", "title": "Section 1", "question_ids": ["q1"]}],
    }
    base.update(overrides)
    return base


# ─── Pydantic Validation ─────────────────────────────────────────────────────


class TestPaperDocumentValidation:
    """Test basic Pydantic field validation."""

    def test_valid_document(self):
        from app.schemas import PaperDocument

        doc = PaperDocument(**_make_document())
        assert doc.title == "Test Paper"
        assert len(doc.questions) == 1

    def test_missing_title_raises(self):
        from app.schemas import PaperDocument

        data = _make_document()
        del data["title"]
        with pytest.raises(ValidationError):
            PaperDocument(**data)

    def test_empty_title_allowed(self):
        from app.schemas import PaperDocument

        doc = PaperDocument(**_make_document(title=""))
        assert doc.title == ""

    def test_default_language(self):
        from app.schemas import PaperDocument

        doc = PaperDocument(**_make_document())
        assert doc.language == "zh-CN"

    def test_duplicate_question_ids_rejected(self):
        from app.schemas import PaperDocument

        data = _make_document(
            questions=[
                _make_question(id="q1"),
                _make_question(id="q1"),  # duplicate
            ]
        )
        with pytest.raises(ValidationError, match="唯一"):
            PaperDocument(**data)

    def test_metadata_defaults_to_empty_dict(self):
        from app.schemas import PaperDocument

        doc = PaperDocument(**_make_document())
        assert doc.metadata == {}

    def test_sections_default_to_empty(self):
        from app.schemas import PaperDocument

        doc = PaperDocument(title="Test")
        assert doc.sections == []
        assert doc.questions == []


class TestQuestionValidation:
    """Test Question model field validation."""

    def test_valid_single_choice(self):
        from app.schemas import Question

        q = Question(**_make_question())
        assert q.type == "single_choice"
        assert q.correct_keys == ["B"]

    def test_missing_stem_raises(self):
        from app.schemas import Question

        data = _make_question()
        del data["stem"]
        with pytest.raises(ValidationError):
            Question(**data)

    def test_missing_type_raises(self):
        from app.schemas import Question

        data = _make_question()
        del data["type"]
        with pytest.raises(ValidationError):
            Question(**data)

    def test_invalid_question_type_raises(self):
        from app.schemas import Question

        with pytest.raises(ValidationError):
            Question(**_make_question(type="essay"))

    def test_negative_score_rejected(self):
        from app.schemas import Question

        with pytest.raises(ValidationError):
            Question(**_make_question(score=-1.0))

    def test_confidence_range(self):
        from app.schemas import Question

        # Valid
        q = Question(**_make_question(confidence=0.5))
        assert q.confidence == 0.5

        # Out of range
        with pytest.raises(ValidationError):
            Question(**_make_question(confidence=1.5))

        with pytest.raises(ValidationError):
            Question(**_make_question(confidence=-0.1))

    def test_options_none_normalized_to_empty_list(self):
        from app.schemas import Question

        q = Question(**_make_question(options=None))
        assert q.options == []

    def test_correct_keys_none_normalized(self):
        from app.schemas import Question

        q = Question(**_make_question(correct_keys=None))
        assert q.correct_keys == []

    def test_correct_keys_string_wrapped_in_list(self):
        from app.schemas import Question

        q = Question(**_make_question(correct_keys="A"))
        assert q.correct_keys == ["A"]

    def test_acceptable_answers_auto_wrap(self):
        """list[str] should be auto-wrapped into list[list[str]]."""
        from app.schemas import Question

        q = Question(
            id="fb1",
            type="fill_blank",
            stem="Capital of France?",
            acceptable_answers=["Paris", "paris"],
        )
        # Should be wrapped: [["Paris", "paris"]]
        assert len(q.acceptable_answers) == 2
        assert q.acceptable_answers[0] == ["Paris"]
        assert q.acceptable_answers[1] == ["paris"]


# ─── Semantic Validation ──────────────────────────────────────────────────────


class TestSemanticValidation:
    """Test PaperDocument.semantic_validate() — cross-field rules."""

    def _validate(self, doc_dict):
        from app.schemas import PaperDocument

        doc = PaperDocument(**doc_dict)
        return doc.semantic_validate()

    # --- Choice questions ---

    def test_single_choice_valid(self):
        errors = self._validate(
            _make_document(questions=[_make_question(answer_origin="model_knowledge")])
        )
        assert len(errors) == 0

    def test_single_choice_no_options(self):
        errors = self._validate(
            _make_document(questions=[_make_question(options=[])])
        )
        assert any("选项" in e for e in errors)

    def test_single_choice_no_correct_keys(self):
        errors = self._validate(
            _make_document(questions=[_make_question(correct_keys=[])])
        )
        assert any("答案" in e for e in errors)

    def test_single_choice_multiple_correct_keys(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        type="single_choice",
                        correct_keys=["A", "B"],
                        options=[
                            {"key": "A", "text": "1"},
                            {"key": "B", "text": "2"},
                        ],
                    )
                ]
            )
        )
        assert any("单选" in e for e in errors)

    def test_correct_keys_reference_nonexistent_option(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        correct_keys=["C"],
                        options=[
                            {"key": "A", "text": "1"},
                            {"key": "B", "text": "2"},
                        ],
                    )
                ]
            )
        )
        assert any("C" in e for e in errors)

    def test_multi_choice_multiple_correct_keys_ok(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        id="mq1",
                        type="multi_choice",
                        correct_keys=["A", "B"],
                        options=[
                            {"key": "A", "text": "1"},
                            {"key": "B", "text": "2"},
                            {"key": "C", "text": "3"},
                        ],
                        answer_origin="model_knowledge",
                    )
                ],
                sections=[{"id": "s1", "title": "S1", "question_ids": ["mq1"]}],
            )
        )
        assert len(errors) == 0

    # --- True/False ---

    def test_true_false_missing_answer(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        id="tf1",
                        type="true_false",
                        options=[],
                        correct_keys=[],
                        true_false_answer=None,
                    )
                ]
            )
        )
        assert any("判断" in e or "布尔" in e for e in errors)

    def test_true_false_valid(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        id="tf1",
                        type="true_false",
                        options=[],
                        correct_keys=[],
                        true_false_answer=True,
                        answer_origin="model_knowledge",
                    )
                ],
                sections=[{"id": "s1", "title": "S1", "question_ids": ["tf1"]}],
            )
        )
        assert len(errors) == 0

    # --- Fill in the blank ---

    def test_fill_blank_no_answers(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        id="fb1",
                        type="fill_blank",
                        options=[],
                        correct_keys=[],
                        acceptable_answers=[],
                    )
                ]
            )
        )
        assert any("填空" in e or "可接受" in e for e in errors)

    # --- Subjective ---

    def test_subjective_no_reference(self):
        errors = self._validate(
            _make_document(
                questions=[
                    _make_question(
                        id="sub1",
                        type="subjective",
                        options=[],
                        correct_keys=[],
                        reference_answer="",
                        scoring_points=[],
                    )
                ]
            )
        )
        assert any("主观" in e or "参考" in e for e in errors)

    # --- Section reference integrity ---

    def test_section_references_nonexistent_question(self):
        errors = self._validate(
            _make_document(
                sections=[
                    {"id": "s1", "title": "S1", "question_ids": ["q1", "q999"]}
                ]
            )
        )
        assert any("q999" in e for e in errors)

    def test_valid_section_references(self):
        errors = self._validate(
            _make_document(
                sections=[{"id": "s1", "title": "S1", "question_ids": ["q1"]}]
            )
        )
        # No section reference errors
        assert not any("不存在的题目" in e for e in errors)

    # --- Explanation and answer_origin are hard errors ---

    def test_missing_explanation_is_error(self):
        errors = self._validate(
            _make_document(questions=[_make_question(explanation="")])
        )
        assert any("解析" in e for e in errors)

    def test_needs_review_is_error(self):
        errors = self._validate(
            _make_document(questions=[_make_question(answer_origin="needs_review")])
        )
        assert any("尚未可靠生成" in e for e in errors)


class TestUniqueSlugGeneration:
    """测试 PaperRepository.generate_unique_slug 的规范与递增逻辑。"""

    def test_generate_unique_slug_increment(self, db_session):
        from app.database import Base
        from app.repositories import PaperRepository

        Base.metadata.create_all(bind=db_session.get_bind())
        repo = PaperRepository(db_session)

        # 1. 初始生成
        slug1 = repo.generate_unique_slug("期末考试试卷")
        repo.create(title="期末考试试卷", slug=slug1)
        assert slug1 == "qi-mo-kao-shi-shi-juan" or slug1 == "paper"

        # 2. 第二次同名生成
        slug2 = repo.generate_unique_slug("期末考试试卷")
        repo.create(title="期末考试试卷", slug=slug2)
        assert slug2 == f"{slug1}-1"

        # 3. 第三次同名生成，确保递增为 -2 而非 -1-2
        slug3 = repo.generate_unique_slug("期末考试试卷")
        assert slug3 == f"{slug1}-2"
