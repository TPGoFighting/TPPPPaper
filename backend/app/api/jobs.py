"""任务路由。对应 SPEC 13: /api/jobs/*"""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import ProcessingJob
from ..schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/paper/{paper_id}", response_model=list[JobOut])
async def list_jobs_by_paper(paper_id: int, db: DBSession, _: AdminUser):
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.paper_id == paper_id)
        .order_by(ProcessingJob.created_at.desc())
        .all()
    )


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: DBSession, _: AdminUser):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    return job


@router.post("/{job_id}/cancel", status_code=202)
async def cancel_job(job_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    if job.status in ("succeeded", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="任务已结束")
    job.status = "cancelled"
    db.commit()
    return {"status": "cancelled"}


@router.post("/{job_id}/retry", status_code=202)
async def retry_job(job_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    """重试失败阶段。"""
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="只能重试失败任务")
    job.status = "queued"
    job.retry_count += 1
    db.commit()
    from ..queue import enqueue_job
    await enqueue_job(job_id=job.id)
    return {"status": "queued", "retry_count": job.retry_count}
