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
