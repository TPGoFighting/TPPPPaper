"""上传路由。对应 SPEC 13: /api/uploads/*

校验扩展名、MIME 和文件签名；存储到私有卷。
"""
import hashlib
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..config import settings
from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import Paper, SourceFile
from ..security import validate_url_safety  # noqa: F401
from ..storage import compute_sha256, default_expiry, generate_storage_key, get_storage

router = APIRouter(prefix="/uploads", tags=["uploads"])

# 允许的文件类型与签名（magic bytes）
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".png", ".jpg", ".jpeg"}
ALLOWED_MIMES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/png",
    "image/jpeg",
}
FILE_SIGNATURES = {
    b"%PDF": "application/pdf",
    b"PK\x03\x04": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    b"\x89PNG": "image/png",
    b"\xff\xd8\xff": "image/jpeg",
}


def detect_file_type(data: bytes) -> str:
    """通过文件签名检测真实类型，防止伪造类型。"""
    for sig, mime in FILE_SIGNATURES.items():
        if data.startswith(sig):
            return mime
    return ""


@router.post("/init")
async def init_upload(
    _: AdminUser,
    __: CSRFProtected,
    filename: str,
    mime_type: str,
    size_bytes: int,
    mode: str = "faithful_transcription",
):
    """上传初始化：校验参数并返回上传凭证。"""
    from pathlib import Path
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    if mime_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail="MIME 类型不被允许")
    if size_bytes > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"文件超过上限 {settings.upload_max_size_mb}MB",
        )
    return {
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "mode": mode,
        "max_size_mb": settings.upload_max_size_mb,
        "max_pages": settings.upload_max_pages,
    }


@router.post("/file")
async def upload_file(
    db: DBSession,
    admin: AdminUser,
    _: CSRFProtected,
    file: UploadFile = File(...),
    mode: str = "faithful_transcription",
):
    """直接上传文件（MVP 使用直传，不分片）。"""
    content = await file.read()
    if len(content) > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件超过上限")

    # 文件签名校验：以二进制 Magic Bytes 检测结果为最高权威标准
    detected = detect_file_type(content)
    if not detected:
        raise HTTPException(status_code=400, detail="文件签名不匹配，类型可能被伪造")

    if file.content_type and file.content_type != "application/octet-stream":
        allowed_aliases = {
            "image/jpeg": {"image/jpeg", "image/jpg", "image/pjpeg"},
            "image/png": {"image/png"},
            "application/pdf": {"application/pdf"},
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "application/docx",
                "application/x-docx",
                "application/wps-office.docx",
                "application/msword",
                "application/zip",
            },
        }
        valid_mimes = allowed_aliases.get(detected, {detected})
        if file.content_type not in valid_mimes:
            raise HTTPException(
                status_code=400,
                detail=f"文件签名({detected})与声明类型({file.content_type})不符",
            )

    sha = compute_sha256(content)
    storage_key = generate_storage_key(file.filename, content)
    storage = get_storage()
    storage.put(settings.source_files_namespace, storage_key, content)

    # 创建 Paper 与 SourceFile
    from ..models import Paper as PaperModel
    from ..repositories import PaperRepository

    repo = PaperRepository(db)
    slug = repo.generate_unique_slug(file.filename)

    paper = PaperModel(
        title=file.filename.rsplit(".", 1)[0],
        slug=slug,
        mode=mode,
        status="queued",
    )
    db.add(paper)
    db.flush()

    source = SourceFile(
        paper_id=paper.id,
        storage_key=storage_key,
        original_filename=file.filename,
        mime_type=detected,
        size_bytes=len(content),
        sha256=sha,
        detected_type=detected,
        expires_at=default_expiry(),
    )
    db.add(source)
    db.flush()
    paper.source_file_id = source.id
    db.commit()

    # 入队处理任务（MVP：直接标记为 queued，由 worker 拉取）
    from ..queue import enqueue_parse_job
    await enqueue_parse_job(paper_id=paper.id, source_file_id=source.id)

    return {"paper_id": paper.id, "slug": paper.slug, "source_file_id": source.id}
