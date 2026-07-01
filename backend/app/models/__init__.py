"""SQLAlchemy ORM 模型。

对应 SPEC 第 11 节核心数据模型：
Paper / SourceFile / ProcessingJob / PaperDraft / PublicationVersion / Asset / ModelProfile
"""
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ModelProfile(TimestampMixin, Base):
    """SPEC 11.7 - 模型服务配置。

    API Key 使用部署级主密钥信封加密存储。
    """

    __tablename__ = "model_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    protocol: Mapped[str] = mapped_column(String(50), default="openai_compatible")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    # 信封加密后的 API Key 密文
    encrypted_api_key: Mapped[str] = mapped_column(Text, nullable=False, default="")
    text_model: Mapped[str] = mapped_column(String(200), default="gpt-4o")
    multimodal_model: Mapped[str] = mapped_column(String(200), default="gpt-4o")
    # 能力标注（模型服务不支持探测时手工标注）
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    max_concurrency: Mapped[int] = mapped_column(Integer, default=4)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    allow_private_network: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="model_profile")


class Paper(TimestampMixin, Base):
    """SPEC 11.1 - 资料的稳定身份。"""

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    # faithful_transcription / lecture_to_quiz
    mode: Mapped[str] = mapped_column(String(50), default="faithful_transcription")
    # uploading / queued / parsing / modeling / pending_review / published / partial_failed / failed
    status: Mapped[str] = mapped_column(String(50), default="uploading", index=True)

    current_draft_id: Mapped[int | None] = mapped_column(
        ForeignKey("paper_drafts.id", use_alter=True), nullable=True
    )
    current_publication_id: Mapped[int | None] = mapped_column(
        ForeignKey("publication_versions.id", use_alter=True), nullable=True
    )

    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id"), nullable=True
    )

    source_file: Mapped["SourceFile | None"] = relationship(foreign_keys=[source_file_id])
    drafts: Mapped[list["PaperDraft"]] = relationship(
        back_populates="paper", foreign_keys="PaperDraft.paper_id"
    )
    publications: Mapped[list["PublicationVersion"]] = relationship(
        back_populates="paper", foreign_keys="PublicationVersion.paper_id"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="paper")


class SourceFile(TimestampMixin, Base):
    """SPEC 11.2 - 上传的源文件。

    默认上传后七天到期，由幂等清理任务删除。无公开路由。
    """

    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True)
    # 私有存储键，如 sources/2026/06/abc.pdf
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 文件签名（magic bytes 检测结果）
    detected_type: Mapped[str] = mapped_column(String(50), default="")
    # 到期时间，到期后由清理任务删除
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessingJob(TimestampMixin, Base):
    """SPEC 11.3 - 异步处理任务。"""

    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), nullable=False, index=True)
    model_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey("model_profiles.id"), nullable=True
    )
    # extract / generate_document / generate_presentation / sanitize / publish
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # queued / running / succeeded / failed / cancelled
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)
    # 幂等键，用于可重试阶段去重
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=True, index=True)
    # 阶段化进度
    stage: Mapped[str] = mapped_column(String(100), default="")
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    failed_pages: Mapped[list[int]] = mapped_column(JSON, default=list)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 模型调用摘要（脱敏后）
    call_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    paper: Mapped["Paper"] = relationship(back_populates="jobs")
    model_profile: Mapped["ModelProfile | None"] = relationship(back_populates="jobs")


class PaperDraft(TimestampMixin, Base):
    """SPEC 11.4 - 可编辑草稿。

    包含结构化 PaperDocument JSON、presentation.html、theme.css。
    """

    __tablename__ = "paper_drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    # 结构化内容 PaperDocument JSON
    document: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    presentation_html: Mapped[str] = mapped_column(Text, default="")
    theme_css: Mapped[str] = mapped_column(Text, default="")
    # 校验结果
    validation_result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    # 来源版本（从某个已发布版本创建新草稿时记录）
    source_publication_version: Mapped[int | None] = mapped_column(Integer, nullable=True)

    paper: Mapped["Paper"] = relationship(
        back_populates="drafts", foreign_keys=[paper_id]
    )


class PublicationVersion(TimestampMixin, Base):
    """SPEC 11.5 - 不可变发布版本。

    编译并净化后的快照，不能原地修改。
    """

    __tablename__ = "publication_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # 净化编译后的不可变快照
    compiled_html: Mapped[str] = mapped_column(Text, default="")
    compiled_css: Mapped[str] = mapped_column(Text, default="")
    # 结构化内容快照
    document_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    # 内容哈希，用于审计
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # 来源草稿版本
    source_draft_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    published_by: Mapped[str] = mapped_column(String(100), default="admin")
    is_withdrawn: Mapped[bool] = mapped_column(Boolean, default=False)

    paper: Mapped["Paper"] = relationship(
        back_populates="publications", foreign_keys=[paper_id]
    )


class Asset(TimestampMixin, Base):
    """SPEC 11.6 - 媒体资源。"""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int | None] = mapped_column(ForeignKey("papers.id"), nullable=True)
    media_type: Mapped[str] = mapped_column(String(50), nullable=False)  # image / table / audio
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    sha256: Mapped[str] = mapped_column(String(64), default="")
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    alt_text: Mapped[str] = mapped_column(String(500), default="")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
