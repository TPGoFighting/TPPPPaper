"""应用配置。

从环境变量读取，提供部署级默认值。敏感值（主密钥、管理员密码哈希）
只存在环境变量或容器 Secret 中，不写入代码或数据库。
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── 运行环境 ──
    app_name: str = "TPaper"
    env: str = Field(default="dev", description="dev / prod")
    debug: bool = False
    api_prefix: str = "/api"
    public_base_url: str = "http://localhost:3000"

    # ── 数据库 ──
    database_url: str = "sqlite:///./tpaper.db"

    # ── Redis ──
    redis_url: str = ""

    # ── 安全 ──
    # 部署级主密钥，用于 API Key 信封加密；生产必须通过环境变量注入
    master_secret: str = Field(default="change-me-in-production-32bytes!", min_length=32)
    # 会话签名密钥（itsdangerous）
    session_secret: str = Field(default="change-me-session-secret-32bytes!", min_length=32)
    session_cookie_name: str = "tpaper_session"
    session_max_age_seconds: int = 60 * 60 * 12  # 12 小时

    # ── 管理员 ──
    # 首次启动时从环境变量引导的管理员账号
    admin_username: str = "admin"
    admin_password_hash: str = ""  # passlib bcrypt 哈希

    # ── 存储卷 ──
    storage_root: str = "./data/storage"
    source_files_namespace: str = "sources"
    assets_namespace: str = "assets"
    rendered_namespace: str = "rendered"

    # ── 源文件保留 ──
    source_retention_days: int = 7

    # ── 上传限制 ──
    upload_max_size_mb: int = 50
    upload_max_pages: int = 200

    # ── CORS（开发环境）──
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # ── 可选默认模型配置（仅从环境变量注入，绝不写死密钥）──
    default_model_profile_name: str = "LongCat"
    default_model_base_url: str = ""
    default_model_api_key: str = ""
    default_model_name: str = "LongCat-2.0"

    # ── Worker ──
    worker_concurrency: int = 4

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_root)
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
