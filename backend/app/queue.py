"""任务队列抽象。

使用 Celery 分发任务到 Redis broker。
API 容器安装了 worker 包，可直接调用 send_task。
"""
from .config import settings


def _celery_send(task_name: str, args: tuple) -> None:
    """通过 Celery send_task 发送任务（不要求任务在本地定义）。"""
    from celery import Celery
    app = Celery("tpaper-client", broker=settings.redis_url)
    app.send_task(task_name, args=args, queue="tpaper")


async def enqueue_parse_job(paper_id: int, source_file_id: int) -> None:
    """入队解析任务。"""
    if not settings.redis_url:
        return
    try:
        _celery_send("worker.tasks.process_paper", (paper_id, source_file_id))
    except Exception:
        pass


async def enqueue_job(job_id: int) -> None:
    """入队已有任务的重试。"""
    if not settings.redis_url:
        return
    try:
        from .database import SessionLocal
        from .models import ProcessingJob

        db = SessionLocal()
        try:
            job = db.get(ProcessingJob, job_id)
            if job and job.paper:
                _celery_send(
                    "worker.tasks.process_paper",
                    (job.paper_id, job.paper.source_file_id),
                )
        finally:
            db.close()
    except Exception:
        pass
