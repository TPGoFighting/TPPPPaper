"""FastAPI 应用入口。

对应 SPEC 第 13 节 API 边界。所有路由按资源分组。
"""
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .logging_config import get_logger, setup_logging
from .api import (
    assets,
    auth,
    drafts,
    jobs,
    metrics,
    model_profiles,
    papers,
    publications,
    public,
    uploads,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("app_startup", service="tpaper-api")
    # 启动时确保存储目录存在
    settings.storage_path
    # 创建数据库表（本地开发模式，SQLite）
    Base.metadata.create_all(bind=engine)
    # 如果环境变量提供了默认模型配置，启动时自动写入或更新，便于本地跑通全链路。
    if settings.default_model_base_url and settings.default_model_api_key:
        from .database import SessionLocal
        from .models import ModelProfile
        from .security import encrypt_secret

        db = SessionLocal()
        try:
            profile = (
                db.query(ModelProfile)
                .filter(ModelProfile.name == settings.default_model_profile_name)
                .first()
            )
            if not profile:
                profile = ModelProfile(name=settings.default_model_profile_name)
                db.add(profile)
            profile.base_url = settings.default_model_base_url
            profile.encrypted_api_key = encrypt_secret(settings.default_model_api_key)
            profile.text_model = settings.default_model_name
            profile.multimodal_model = settings.default_model_name
            profile.is_active = True
            profile.allow_private_network = False
            db.commit()
        finally:
            db.close()

    # 开发模式：Redis 不可用时启动进程内轮询
    use_inprocess = not settings.redis_url
    task = None
    if use_inprocess:
        from .processing import process_queued_papers
        import asyncio
        task = asyncio.create_task(process_queued_papers())

    yield

    if task:
        task.cancel()


app = FastAPI(
    title="TPaper API",
    description="AI 试卷转换工具 - 管理与公开 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """记录每个 HTTP 请求的方法、路径、状态码和耗时。"""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        duration_ms = int((time.monotonic() - start) * 1000)
        logger.error(
            "api_request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            request_id=request_id,
            error=str(exc),
        )
        raise
    duration_ms = int((time.monotonic() - start) * 1000)
    # 跳过健康检查的日志噪音
    if request.url.path not in ("/health", "/"):
        logger.info(
            "api_request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
            request_id=request_id,
        )
    response.headers["X-Request-ID"] = request_id
    return response


# 注册路由
api_prefix = settings.api_prefix
app.include_router(auth.router, prefix=api_prefix)
app.include_router(model_profiles.router, prefix=api_prefix)
app.include_router(uploads.router, prefix=api_prefix)
app.include_router(papers.router, prefix=api_prefix)
app.include_router(jobs.router, prefix=api_prefix)
app.include_router(drafts.router, prefix=api_prefix)
app.include_router(publications.router, prefix=api_prefix)
app.include_router(public.router, prefix=api_prefix)
app.include_router(assets.router, prefix=api_prefix)
app.include_router(metrics.router, prefix=api_prefix)


@app.get("/health")
async def health():
    """健康检查（Docker Compose 使用）。"""
    return {"status": "ok", "service": "tpaper-api"}


@app.get("/")
async def root():
    return {"name": "TPaper API", "version": "1.0.0", "docs": "/api/docs"}
