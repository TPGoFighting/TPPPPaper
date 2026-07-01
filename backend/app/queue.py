"""任务队列抽象。

MVP 使用 Redis（arq）作为任务队列。此处提供入队接口，
实际执行在 worker 进程中。
"""
from typing import Any

from .config import settings


async def enqueue_parse_job(paper_id: int, source_file_id: int) -> None:
    """入队解析任务。"""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.lpush(
            "tpaper:jobs",
            __import__("json").dumps({
                "type": "parse",
                "paper_id": paper_id,
                "source_file_id": source_file_id,
            }),
        )
        await r.close()
    except Exception:
        # 开发环境无 Redis 时静默降级
        pass


async def enqueue_job(job_id: int) -> None:
    """入队已有任务的重试。"""
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.redis_url)
        await r.lpush(
            "tpaper:jobs",
            __import__("json").dumps({"type": "retry", "job_id": job_id}),
        )
        await r.close()
    except Exception:
        pass
