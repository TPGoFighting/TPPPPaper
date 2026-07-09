"""SourceFile 数据访问层"""
from typing import Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import SourceFile


class SourceFileRepository:
    """SourceFile 数据访问抽象"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, source_file_id: int) -> Optional[SourceFile]:
        """根据 ID 获取 SourceFile"""
        return self.db.get(SourceFile, source_file_id)

    def get_by_paper(self, paper_id: int) -> Optional[SourceFile]:
        """根据 paper_id 获取 SourceFile"""
        return self.db.query(SourceFile).filter(SourceFile.paper_id == paper_id).first()

    def create(
        self,
        paper_id: int,
        storage_key: str,
        original_filename: str,
        mime_type: str,
        size_bytes: int,
        sha256: str,
        detected_type: str = "",
        page_count: Optional[int] = None,
        expires_at: Optional[datetime] = None,
    ) -> SourceFile:
        """创建新 SourceFile"""
        if expires_at is None:
            from ..storage import default_expiry
            expires_at = default_expiry()

        source = SourceFile(
            paper_id=paper_id,
            storage_key=storage_key,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=sha256,
            detected_type=detected_type,
            page_count=page_count,
            expires_at=expires_at,
        )
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def update_page_count(self, source_file_id: int, page_count: int) -> Optional[SourceFile]:
        """更新页数"""
        source = self.get_by_id(source_file_id)
        if source:
            source.page_count = page_count
            self.db.commit()
            self.db.refresh(source)
        return source

    def soft_delete(self, source_file_id: int) -> Optional[SourceFile]:
        """软删除（设置 deleted_at）"""
        source = self.get_by_id(source_file_id)
        if source:
            source.deleted_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(source)
        return source
