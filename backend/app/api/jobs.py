"""任务路由。对应 SPEC 13: /api/jobs/*"""
import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import AdminUser, CSRFProtected, DBSession
from ..repositories import JobRepository
from ..schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/paper/{paper_id}", response_model=list[JobOut])
async def list_jobs_by_paper(paper_id: int, db: DBSession, _: AdminUser):
    repo = JobRepository(db)
    return repo.list_by_paper(paper_id)


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: DBSession, _: AdminUser):
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    return job


@router.post("/{job_id}/cancel", status_code=202)
async def cancel_job(job_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    if job.status in ("succeeded", "failed", "cancelled"):
        raise HTTPException(status_code=400, detail="任务已结束")
    repo.cancel(job_id)
    return {"status": "cancelled"}


@router.post("/{job_id}/retry", status_code=202)
async def retry_job(job_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    """重试失败阶段。"""
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")
    if job.status != "failed":
        raise HTTPException(status_code=400, detail="只能重试失败任务")

    repo.update_status(job_id, "queued")
    job = repo.get_by_id(job_id)  # 重新获取以获取最新的 retry_count

    from ..queue import enqueue_job
    await enqueue_job(job_id=job_id)
    return {"status": "queued", "retry_count": job.retry_count}


@router.get("/{job_id}/stream")
async def stream_job_progress(job_id: int, db: DBSession, _: AdminUser):
    """SSE 实时推送任务进度。"""
    repo = JobRepository(db)
    job = repo.get_by_id(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="未找到")

    async def event_generator():
        while True:
            db2 = None
            try:
                from ..database import SessionLocal
                db2 = SessionLocal()
                job_repo = JobRepository(db2)
                j = job_repo.get_by_id(job_id)
                if not j:
                    break
                data = {
                    "job_id": j.id,
                    "status": j.status,
                    "stage": j.stage,
                    "current_page": j.current_page,
                    "total_pages": j.total_pages,
                    "failed_pages": j.failed_pages or [],
                    "error_message": j.error_message,
                }
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                if j.status in ("succeeded", "failed", "cancelled"):
                    break
            finally:
                if db2:
                    db2.close()
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
