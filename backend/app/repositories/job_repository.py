"""ProcessingJob 数据访问层"""
from typing import Optional

from sqlalchemy.orm import Session

from ..models import ProcessingJob


class JobRepository:
    """ProcessingJob 数据访问抽象"""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, job_id: int) -> Optional[ProcessingJob]:
        """根据 ID 获取 Job"""
        return self.db.get(ProcessingJob, job_id)

    def list_by_paper(self, paper_id: int) -> list[ProcessingJob]:
        """列出某 Paper 的所有 Job"""
        return (
            self.db.query(ProcessingJob)
            .filter(ProcessingJob.paper_id == paper_id)
            .order_by(ProcessingJob.created_at.desc())
            .all()
        )

    def create(self, paper_id: int, job_type: str, model_profile_id: Optional[int] = None) -> ProcessingJob:
        """创建新 Job"""
        job = ProcessingJob(
            paper_id=paper_id,
            job_type=job_type,
            model_profile_id=model_profile_id,
            status="queued",
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def update_status(self, job_id: int, status: str) -> Optional[ProcessingJob]:
        """更新 Job 状态"""
        job = self.get_by_id(job_id)
        if job:
            job.status = status
            self.db.commit()
            self.db.refresh(job)
        return job

    def update_progress(
        self,
        job_id: int,
        stage: str,
        current_page: int,
        total_pages: int,
        failed_pages: Optional[list[int]] = None,
    ) -> Optional[ProcessingJob]:
        """更新 Job 进度"""
        job = self.get_by_id(job_id)
        if job:
            job.stage = stage
            job.current_page = current_page
            job.total_pages = total_pages
            if failed_pages is not None:
                job.failed_pages = failed_pages
            self.db.commit()
            self.db.refresh(job)
        return job

    def mark_failed(self, job_id: int, error_message: str) -> Optional[ProcessingJob]:
        """标记 Job 失败"""
        job = self.get_by_id(job_id)
        if job:
            job.status = "failed"
            job.error_message = error_message
            self.db.commit()
            self.db.refresh(job)
        return job

    def cancel(self, job_id: int) -> Optional[ProcessingJob]:
        """取消 Job"""
        job = self.get_by_id(job_id)
        if job:
            job.status = "cancelled"
            self.db.commit()
            self.db.refresh(job)
        return job
