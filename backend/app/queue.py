"""任务队列抽象。

Redis 可用时使用 Celery，否则静默降级（由 API 进程内轮询处理）。
"""
import json
from typing import Any

from .config import settings


async def enqueue_parse_job(paper_id: int, source_file_id: int) -> None:
    """入队解析任务。优先使用 Celery，降级到 Redis LPUSH。"""
    # 尝试 Celery
    try:
        from worker.tasks import process_paper
        process_paper.delay(paper_id, source_file_id)
        return
    except Exception:
        pass

    # 降级：直接 Redis LPUSH（兼容旧 worker）
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.lpush(
            "tpaper:jobs",
            json.dumps({
                "type": "parse",
                "paper_id": paper_id,
                "source_file_id": source_file_id,
            }),
        )
        await r.close()
    except Exception:
        # 开发环境无 Redis 时静默降级，由进程内轮询处理
        pass


async def enqueue_job(job_id: int) -> None:
    """入队已有任务的重试。"""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.lpush(
            "tpaper:jobs",
            json.dumps({"type": "retry", "job_id": job_id}),
        )
        await r.close()
    except Exception:
        pass
