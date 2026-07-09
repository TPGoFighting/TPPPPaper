"""Celery 应用实例配置。

使用 Redis 作为 broker 和 result backend。
"""
import os
from celery import Celery

redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "tpaper",
    broker=redis_url,
    backend=redis_url,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_soft_time_limit=600,
    task_time_limit=900,
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=512000,
)

# 任务路由
celery_app.conf.task_routes = {
    "worker.tasks.process_paper": {"queue": "tpaper"},
    "worker.tasks.*": {"queue": "tpaper"},
}
