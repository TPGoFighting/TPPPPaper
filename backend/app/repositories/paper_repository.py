"""Paper 数据访问层"""
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..models import Paper, PaperDraft, ProcessingJob, PublicationVersion, SourceFile, Asset


class PaperRepository:
    """Paper 数据访问抽象"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, paper_id: int) -> Optional[Paper]:
        """根据 ID 获取 Paper，支持预加载关联模型"""
        return (
            self.db.query(Paper)
            .options(
                selectinload(Paper.source_file),
                selectinload(Paper.drafts),
                selectinload(Paper.jobs),
            )
            .filter(Paper.id == paper_id)
            .first()
        )

    def get_by_slug(self, slug: str) -> Optional[Paper]:
        """根据 slug 获取 Paper"""
        return self.db.query(Paper).filter(Paper.slug == slug).first()

    def list_all(
        self,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[Paper], int]:
        """列出所有 Paper，支持筛选、搜索、预加载和分页

        Returns:
            (papers, total_count) 元组
        """
        query = self.db.query(Paper)

        if status_filter:
            query = query.filter(Paper.status == status_filter)
        if search_query:
            query = query.filter(Paper.title.ilike(f"%{search_query}%"))

        # 获取总数
        total = query.count()

        # 分页与关联预加载（解决 N+1 查询）
        papers = (
            query.options(
                selectinload(Paper.source_file),
                selectinload(Paper.drafts),
                selectinload(Paper.jobs),
            )
            .order_by(Paper.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

        return papers, total

    def create(self, title: str, slug: str, mode: str = "faithful_transcription") -> Paper:
        """创建新 Paper"""
        paper = Paper(title=title, slug=slug, mode=mode, status="uploading")
        self.db.add(paper)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def update_status(self, paper_id: int, status: str) -> Optional[Paper]:
        """更新 Paper 状态"""
        paper = self.get_by_id(paper_id)
        if paper:
            paper.status = status
            self.db.commit()
            self.db.refresh(paper)
        return paper

    def update_draft(self, paper_id: int, draft_id: int) -> Optional[Paper]:
        """更新 Paper 的当前草稿"""
        paper = self.get_by_id(paper_id)
        if paper:
            paper.current_draft_id = draft_id
            self.db.commit()
            self.db.refresh(paper)
        return paper

    def slug_exists(self, slug: str) -> bool:
        """检查 slug 是否已存在"""
        return self.db.query(Paper).filter(Paper.slug == slug).first() is not None

    def generate_unique_slug(self, raw_name: str) -> str:
        """根据名称或文件名生成规范且唯一的 slug（如 paper, paper-1, paper-2）。"""
        import slugify

        base_slug = slugify.slugify(raw_name)[:60] or "paper"
        slug = base_slug
        suffix = 1
        while self.slug_exists(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        return slug

    def delete(self, paper_id: int) -> bool:
        """删除 Paper 及其所有关联记录

        使用 cascade 关系自动删除关联的:
        - SourceFile
        - PaperDraft
        - PublicationVersion
        - ProcessingJob
        - Asset
        """
        paper = self.get_by_id(paper_id)
        if not paper:
            return False

        # 删除关联的存储文件
        from ..storage import get_storage
        from ..config import settings
        storage = get_storage()
        if paper.source_file and paper.source_file.storage_key:
            try:
                storage.delete(settings.source_files_namespace, paper.source_file.storage_key)
            except Exception:
                pass

        # 级联删除（由 SQLAlchemy cascade 处理）
        self.db.delete(paper)
        self.db.commit()
        return True
