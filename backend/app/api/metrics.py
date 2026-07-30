"""运营指标 API — Dashboard 数据聚合。

提供任务成功率、处理时间、文件类型分布等关键指标。
对应 Phase 4 可观测性改造。
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, case, extract

from ..deps import AdminUser, DBSession
from ..models import Paper, SourceFile, ProcessingJob, PublicationVersion

router = APIRouter(tags=["metrics"])


# ── Response Schemas ──

class StatusDistribution(BaseModel):
    uploading: int = 0
    queued: int = 0
    parsing: int = 0
    modeling: int = 0
    pending_review: int = 0
    published: int = 0
    partial_failed: int = 0
    failed: int = 0


class JobMetrics(BaseModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    running: int = 0
    queued: int = 0
    cancelled: int = 0
    success_rate: float = 0.0
    avg_retry_count: float = 0.0


class ProcessingTimeMetrics(BaseModel):
    avg_seconds: float | None = None
    min_seconds: float | None = None
    max_seconds: float | None = None
    p50_seconds: float | None = None
    p95_seconds: float | None = None


class FileTypeDistribution(BaseModel):
    mime_type: str
    count: int
    avg_size_bytes: float
    avg_page_count: float


class ActivitySummary(BaseModel):
    papers_last_24h: int = 0
    papers_last_7d: int = 0
    jobs_succeeded_24h: int = 0
    jobs_failed_24h: int = 0
    publications_last_7d: int = 0


class DashboardMetrics(BaseModel):
    """Dashboard 主指标聚合。"""
    generated_at: str
    paper_status: StatusDistribution
    job_metrics: JobMetrics
    processing_time: ProcessingTimeMetrics
    file_types: list[FileTypeDistribution]
    activity: ActivitySummary
    total_papers: int
    total_publications: int


@router.get("/metrics/dashboard", response_model=DashboardMetrics)
async def dashboard_metrics(db: DBSession, _: AdminUser):
    """返回 Dashboard 所需的聚合指标（需要管理员权限）。"""
    now = datetime.now(timezone.utc)

    # ── Paper 状态分布 ──
    paper_status_rows = (
        db.query(Paper.status, func.count(Paper.id))
        .group_by(Paper.status)
        .all()
    )
    status_map = {row[0]: row[1] for row in paper_status_rows}
    paper_status = StatusDistribution(**status_map)
    total_papers = sum(status_map.values())

    # ── Job 指标 ──
    job_status_rows = (
        db.query(ProcessingJob.status, func.count(ProcessingJob.id))
        .group_by(ProcessingJob.status)
        .all()
    )
    job_map = {row[0]: row[1] for row in job_status_rows}
    total_jobs = sum(job_map.values())
    succeeded = job_map.get("succeeded", 0)
    failed = job_map.get("failed", 0)

    avg_retry = db.query(func.avg(ProcessingJob.retry_count)).scalar() or 0.0

    job_metrics = JobMetrics(
        total=total_jobs,
        succeeded=succeeded,
        failed=failed,
        running=job_map.get("running", 0),
        queued=job_map.get("queued", 0),
        cancelled=job_map.get("cancelled", 0),
        success_rate=round(succeeded / total_jobs * 100, 1) if total_jobs > 0 else 0.0,
        avg_retry_count=round(float(avg_retry), 2),
    )

    # ── 处理时间（从已完成 Job 的 created_at → updated_at 推导）──
    terminal_jobs = (
        db.query(
            ProcessingJob.status,
            ProcessingJob.created_at,
            ProcessingJob.updated_at,
        )
        .filter(ProcessingJob.status.in_(["succeeded", "failed"]))
        .all()
    )
    durations = []
    for job in terminal_jobs:
        if job.created_at and job.updated_at:
            delta = (job.updated_at - job.created_at).total_seconds()
            if delta > 0:
                durations.append(delta)

    if durations:
        durations.sort()
        n = len(durations)
        processing_time = ProcessingTimeMetrics(
            avg_seconds=round(sum(durations) / n, 1),
            min_seconds=round(durations[0], 1),
            max_seconds=round(durations[-1], 1),
            p50_seconds=round(durations[n // 2], 1),
            p95_seconds=round(durations[int(n * 0.95)], 1),
        )
    else:
        processing_time = ProcessingTimeMetrics()

    # ── 文件类型分布 ──
    file_type_rows = (
        db.query(
            SourceFile.mime_type,
            func.count(SourceFile.id),
            func.avg(SourceFile.size_bytes),
            func.avg(SourceFile.page_count),
        )
        .group_by(SourceFile.mime_type)
        .all()
    )
    file_types = [
        FileTypeDistribution(
            mime_type=row[0] or "unknown",
            count=row[1],
            avg_size_bytes=round(float(row[2] or 0), 0),
            avg_page_count=round(float(row[3] or 0), 1),
        )
        for row in file_type_rows
    ]

    # ── 活跃度摘要 ──
    cutoff_24h = now - timedelta(hours=24)
    cutoff_7d = now - timedelta(days=7)

    papers_24h = db.query(func.count(Paper.id)).filter(Paper.created_at >= cutoff_24h).scalar() or 0
    papers_7d = db.query(func.count(Paper.id)).filter(Paper.created_at >= cutoff_7d).scalar() or 0
    jobs_ok_24h = (
        db.query(func.count(ProcessingJob.id))
        .filter(ProcessingJob.status == "succeeded", ProcessingJob.updated_at >= cutoff_24h)
        .scalar() or 0
    )
    jobs_fail_24h = (
        db.query(func.count(ProcessingJob.id))
        .filter(ProcessingJob.status == "failed", ProcessingJob.updated_at >= cutoff_24h)
        .scalar() or 0
    )
    pubs_7d = (
        db.query(func.count(PublicationVersion.id))
        .filter(PublicationVersion.published_at >= cutoff_7d)
        .scalar() or 0
    )

    activity = ActivitySummary(
        papers_last_24h=papers_24h,
        papers_last_7d=papers_7d,
        jobs_succeeded_24h=jobs_ok_24h,
        jobs_failed_24h=jobs_fail_24h,
        publications_last_7d=pubs_7d,
    )

    # ── 总发布数 ──
    total_publications = db.query(func.count(PublicationVersion.id)).scalar() or 0

    return DashboardMetrics(
        generated_at=now.isoformat(),
        paper_status=paper_status,
        job_metrics=job_metrics,
        processing_time=processing_time,
        file_types=file_types,
        activity=activity,
        total_papers=total_papers,
        total_publications=total_publications,
    )
