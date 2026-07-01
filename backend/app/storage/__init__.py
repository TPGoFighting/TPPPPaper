"""存储抽象与本地私有卷实现。

对应 SPEC 第 9 节：MVP 使用本地私有存储卷并通过存储接口抽象，
未来可替换为 S3-compatible 存储。源文件与发布媒体使用不同命名空间。
"""
import hashlib
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Protocol

from ..config import settings


class StorageBackend(Protocol):
    """存储后端抽象接口。"""

    def put(self, namespace: str, key: str, data: bytes) -> str:
        """写入文件，返回完整存储键。"""
        ...

    def get(self, namespace: str, key: str) -> bytes:
        ...

    def delete(self, namespace: str, key: str) -> None:
        ...

    def exists(self, namespace: str, key: str) -> bool:
        ...

    def path(self, namespace: str, key: str) -> Path:
        ...


class LocalStorage:
    """本地私有卷存储实现。"""

    def __init__(self, root: Path | None = None):
        self.root = root or settings.storage_path

    def _ensure_dir(self, namespace: str) -> Path:
        d = self.root / namespace
        d.mkdir(parents=True, exist_ok=True)
        return d

    def put(self, namespace: str, key: str, data: bytes) -> str:
        self._ensure_dir(namespace)
        full = self.root / namespace / key
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)
        return f"{namespace}/{key}"

    def get(self, namespace: str, key: str) -> bytes:
        full = self.root / namespace / key
        return full.read_bytes()

    def delete(self, namespace: str, key: str) -> None:
        full = self.root / namespace / key
        if full.exists():
            full.unlink()

    def exists(self, namespace: str, key: str) -> bool:
        return (self.root / namespace / key).exists()

    def path(self, namespace: str, key: str) -> Path:
        return self.root / namespace / key


# 单例
_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage()
    return _storage


def generate_storage_key(filename: str, content: bytes | None = None) -> str:
    """生成基于日期和哈希的存储键。"""
    now = datetime.now(timezone.utc)
    if content:
        digest = hashlib.sha256(content).hexdigest()[:16]
    else:
        digest = hashlib.sha256(filename.encode()).hexdigest()[:16]
    ext = Path(filename).suffix
    return f"{now.strftime('%Y/%m/%d')}/{digest}{ext}"


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def default_expiry() -> datetime:
    """源文件默认到期时间：上传后七天。"""
    return datetime.now(timezone.utc) + timedelta(days=settings.source_retention_days)
