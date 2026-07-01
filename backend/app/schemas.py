"""Pydantic Schema：API 请求/响应模型与 PaperDocument 结构化校验。

对应 SPEC 第 12 节 PaperDocument Schema。
"""
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── 枚举 ──

class PaperMode(str, Enum):
    faithful_transcription = "faithful_transcription"
    lecture_to_quiz = "lecture_to_quiz"


class PaperStatus(str, Enum):
    uploading = "uploading"
    queued = "queued"
    parsing = "parsing"
    modeling = "modeling"
    pending_review = "pending_review"
    published = "published"
    partial_failed = "partial_failed"
    failed = "failed"


class QuestionType(str, Enum):
    single_choice = "single_choice"
    multi_choice = "multi_choice"
    true_false = "true_false"
    fill_blank = "fill_blank"
    subjective = "subjective"


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class ModelProtocol(str, Enum):
    openai_compatible = "openai_compatible"


# ── PaperDocument 结构化 Schema（SPEC 第 12 节）──

class MediaRef(BaseModel):
    asset_id: int | None = None
    storage_key: str | None = None
    alt_text: str = ""
    source_page: int | None = None


class QuestionOption(BaseModel):
    key: str = Field(..., description="选项标识，如 A/B/C/D")
    text: str


class Question(BaseModel):
    """题目稳定结构。"""
    id: str = Field(..., description="稳定 ID，文档内唯一")
    number: int | None = None
    type: QuestionType
    stem: str
    media: list[MediaRef] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0.0)
    # 选择题
    options: list[QuestionOption] = Field(default_factory=list)
    correct_keys: list[str] = Field(default_factory=list)

    @field_validator("options", mode="before")
    @classmethod
    def normalize_options(cls, v: Any) -> list[Any]:
        if v is None:
            return []
        return v

    @field_validator("correct_keys", mode="before")
    @classmethod
    def normalize_correct_keys(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return [str(x) for x in v]
    # 判断题
    true_false_answer: bool | None = None
    # 填空题
    acceptable_answers: list[list[str]] = Field(
        default_factory=list, description="每个空的可接受答案列表"
    )

    @field_validator("acceptable_answers", mode="before")
    @classmethod
    def normalize_acceptable_answers(cls, v: Any) -> list[list[str]]:
        """将 AI 可能生成的 list[str] 自动包装为 list[list[str]]。"""
        if not v:
            return []
        result = []
        for item in v:
            if isinstance(item, list):
                result.append([str(x) for x in item])
            else:
                result.append([str(item)])
        return result
    match_rule: str = Field(default="exact", description="exact / contains / regex")
    # 主观题
    reference_answer: str = ""
    scoring_points: list[str] = Field(default_factory=list)
    # 通用
    explanation: str = ""
    knowledge_points: list[str] = Field(default_factory=list)
    source_page: int | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    needs_review: bool = False
    is_ai_generated: bool = False


class Section(BaseModel):
    id: str
    title: str = ""
    source_page: int | None = None
    question_ids: list[str] = Field(default_factory=list)


class PaperDocument(BaseModel):
    """SPEC 第 12 节 - 结构化试卷文档。"""
    title: str
    language: str = "zh-CN"
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)

    @field_validator("questions")
    @classmethod
    def validate_questions(cls, v: list[Question]) -> list[Question]:
        ids = [q.id for q in v]
        if len(ids) != len(set(ids)):
            raise ValueError("题目 ID 必须唯一")
        return v

    def semantic_validate(self) -> list[str]:
        """语义校验，返回错误信息列表（空列表表示通过）。

        对应 SPEC 12：ID 唯一、答案引用有效、必填字段存在、
        媒体引用有效、分值非负、题型字段匹配。
        """
        errors: list[str] = []
        qids = {q.id for q in self.questions}

        for q in self.questions:
            # 题型字段匹配校验
            if q.type in (QuestionType.single_choice, QuestionType.multi_choice):
                if not q.options:
                    errors.append(f"题目 {q.id}：选择题缺少选项")
                valid_keys = {o.key for o in q.options}
                for ck in q.correct_keys:
                    if ck not in valid_keys:
                        errors.append(f"题目 {q.id}：正确答案 {ck} 不在选项中")
                if q.type == QuestionType.single_choice and len(q.correct_keys) > 1:
                    errors.append(f"题目 {q.id}：单选题只能有一个正确答案")
            elif q.type == QuestionType.true_false:
                if q.true_false_answer is None:
                    errors.append(f"题目 {q.id}：判断题缺少布尔答案")
            elif q.type == QuestionType.fill_blank:
                if not q.acceptable_answers:
                    errors.append(f"题目 {q.id}：填空题缺少可接受答案")
            elif q.type == QuestionType.subjective:
                if not q.reference_answer and not q.scoring_points and not q.explanation:
                    errors.append(f"题目 {q.id}：主观题缺少参考答案或评分要点")

            # 分值非负（Pydantic Field ge 已保证，这里冗余检查）
            if q.score < 0:
                errors.append(f"题目 {q.id}：分值不能为负")

        # 章节引用校验
        for s in self.sections:
            for qid in s.question_ids:
                if qid not in qids:
                    errors.append(f"章节 {s.id}：引用了不存在的题目 {qid}")

        return errors


# ── API 响应 Schema ──

class PaperOut(BaseModel):
    id: int
    title: str
    slug: str
    mode: PaperMode
    status: PaperStatus
    current_draft_id: int | None = None
    current_publication_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ModelProfileOut(BaseModel):
    id: int
    name: str
    protocol: ModelProtocol
    base_url: str
    text_model: str
    multimodal_model: str
    supports_vision: bool
    timeout_seconds: int
    max_concurrency: int
    max_retries: int
    allow_private_network: bool
    is_active: bool
    # API Key 掩码，前端只看到掩码
    api_key_masked: str = ""

    class Config:
        from_attributes = True


class ModelProfileCreate(BaseModel):
    name: str
    protocol: ModelProtocol = ModelProtocol.openai_compatible
    base_url: str
    api_key: str = Field(default="", description="API 密钥，存储前加密")
    text_model: str = "gpt-4o"
    multimodal_model: str = "gpt-4o"
    supports_vision: bool = False
    timeout_seconds: int = 60
    max_concurrency: int = 4
    max_retries: int = 3
    allow_private_network: bool = False


class ModelProfileUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    api_key: str | None = Field(default=None, description="API 密钥，留空不修改")
    text_model: str | None = None
    multimodal_model: str | None = None
    supports_vision: bool | None = None
    timeout_seconds: int | None = None
    max_concurrency: int | None = None
    max_retries: int | None = None
    allow_private_network: bool | None = None
    is_active: bool | None = None


class SourceFileOut(BaseModel):
    id: int
    original_filename: str
    mime_type: str
    size_bytes: int
    page_count: int | None = None
    expires_at: datetime
    deleted_at: datetime | None = None

    class Config:
        from_attributes = True


class JobOut(BaseModel):
    id: int
    paper_id: int
    job_type: str
    status: JobStatus
    stage: str
    current_page: int
    total_pages: int
    failed_pages: list[int]
    retry_count: int
    error_code: str | None = None
    error_message: str | None = None
    call_summary: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DraftOut(BaseModel):
    id: int
    paper_id: int
    version: int
    document: dict[str, Any]
    presentation_html: str
    theme_css: str
    validation_result: dict[str, Any]
    is_valid: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DraftUpdate(BaseModel):
    document: dict[str, Any] | None = None
    presentation_html: str | None = None
    theme_css: str | None = None


class PublicationOut(BaseModel):
    id: int
    paper_id: int
    version: int
    compiled_html: str
    compiled_css: str
    content_hash: str
    source_draft_version: int | None = None
    published_at: datetime
    published_by: str
    is_withdrawn: bool

    class Config:
        from_attributes = True


class UploadInit(BaseModel):
    filename: str
    mime_type: str
    size_bytes: int
    mode: PaperMode


class UploadComplete(BaseModel):
    upload_id: str
    sha256: str


class LoginIn(BaseModel):
    username: str
    password: str


class TestConnectionIn(BaseModel):
    base_url: str
    api_key: str = Field(description="API 密钥")
    model: str = "gpt-4o"
    allow_private_network: bool = False


class PublishIn(BaseModel):
    draft_id: int


class PaperCreate(BaseModel):
    title: str
    mode: PaperMode = PaperMode.faithful_transcription
