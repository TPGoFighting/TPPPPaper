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
    # 任务跟踪
    task_track_started=True,
    task_acks_late=True,  # 任务完成后才确认，防止worker崩溃导致任务丢失
    worker_prefetch_multiplier=1,  # 长任务场景：每次只预取1个任务
    result_expires=3600,
    # 超时配置 - 增加到15分钟软限制，20分钟硬限制
    task_soft_time_limit=900,   # 15分钟软限制（触发SoftTimeLimitExceeded）
    task_time_limit=1200,       # 20分钟硬限制（强制终止）
    # Worker 配置
    worker_max_tasks_per_child=100,
    worker_max_memory_per_child=512000,
    # Redis 配置 - 防止长任务丢失
    broker_transport_options={
        "visibility_timeout": 3600,  # 1小时，防止长任务被broker误认为丢失
    },
    result_backend_transport_options={
        "socket_connect_timeout": 10,
        "socket_timeout": 10,
        "retry_on_timeout": True,
    },
)

# 任务路由
celery_app.conf.task_routes = {
    "worker.tasks.process_paper": {"queue": "tpaper"},
    "worker.tasks.*": {"queue": "tpaper"},
}
