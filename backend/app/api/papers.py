"""资料路由。对应 SPEC 13: /api/papers/*"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import Paper
from ..schemas import PaperCreate, PaperOut, PaperStatus

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=list[PaperOut])
async def list_papers(
    db: DBSession,
    _: AdminUser,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None),
):
    """管理首页：列出资料，支持状态筛选与标题搜索。"""
    query = db.query(Paper)
    if status_filter:
        query = query.filter(Paper.status == status_filter)
    if q:
        query = query.filter(Paper.title.ilike(f"%{q}%"))
    return query.order_by(Paper.updated_at.desc()).all()


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(paper_id: int, db: DBSession, _: AdminUser):
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="未找到")
    return paper


@router.post("", response_model=PaperOut, status_code=201)
async def create_paper(body: PaperCreate, db: DBSession, _: AdminUser, __: CSRFProtected):
    import slugify
    slug = slugify.slugify(body.title)[:60] or "paper"
    suffix = 1
    while db.query(Paper).filter(Paper.slug == slug).first():
        slug = f"{slug}-{suffix}"
        suffix += 1
    paper = Paper(title=body.title, slug=slug, mode=body.mode.value, status="uploading")
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return paper


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(paper_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    from ..models import PaperDraft, ProcessingJob, PublicationVersion
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="未找到")
    # 删除关联源文件
    from ..storage import get_storage
    from ..config import settings
    storage = get_storage()
    if paper.source_file and paper.source_file.storage_key:
        try:
            storage.delete(settings.source_files_namespace, paper.source_file.storage_key)
        except Exception:
            pass
    # 手动级联删除关联记录
    db.query(PaperDraft).filter(PaperDraft.paper_id == paper_id).delete()
    db.query(ProcessingJob).filter(ProcessingJob.paper_id == paper_id).delete()
    db.query(PublicationVersion).filter(PublicationVersion.paper_id == paper_id).delete()
    db.delete(paper)
    db.commit()


@router.post("/{paper_id}/reprocess", status_code=202)
async def reprocess(paper_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    """重新解析。"""
    paper = db.get(Paper, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="未找到")
    if not paper.source_file_id:
        raise HTTPException(status_code=400, detail="无源文件")
    paper.status = "queued"
    db.commit()
    from ..queue import enqueue_parse_job
    await enqueue_parse_job(paper_id=paper.id, source_file_id=paper.source_file_id)
    return {"status": "queued"}
