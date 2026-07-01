"""FastAPI 应用入口。

对应 SPEC 第 13 节 API 边界。所有路由按资源分组。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .api import (
    assets,
    auth,
    drafts,
    jobs,
    model_profiles,
    papers,
    publications,
    public,
    uploads,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时确保存储目录存在
    settings.storage_path
    # 创建数据库表（本地开发模式，SQLite）
    Base.metadata.create_all(bind=engine)
    # 启动后台任务处理器（本地开发模式，无需 Redis）
    from .processing import process_queued_papers
    import asyncio
    task = asyncio.create_task(process_queued_papers())
    yield
    task.cancel()


app = FastAPI(
    title="TPaper API",
    description="AI 试卷转换工具 - 管理与公开 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

# CORS（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
async def health():
    """健康检查（Docker Compose 使用）。"""
    return {"status": "ok", "service": "tpaper-api"}


@app.get("/")
async def root():
    return {"name": "TPaper API", "version": "1.0.0", "docs": "/api/docs"}
