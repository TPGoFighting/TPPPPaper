"""Paper 数据访问层"""
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Paper, PaperDraft, ProcessingJob, PublicationVersion, SourceFile, Asset


class PaperRepository:
    """Paper 数据访问抽象"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, paper_id: int) -> Optional[Paper]:
        """根据 ID 获取 Paper"""
        return self.db.get(Paper, paper_id)

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
        """列出所有 Paper，支持筛选、搜索和分页

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

        # 分页
        papers = (
            query.order_by(Paper.updated_at.desc())
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
