"""资料路由。对应 SPEC 13: /api/papers/*"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import Paper
from ..repositories import PaperRepository
from ..schemas import PaperCreate, PaperOut, PaperStatus

router = APIRouter(prefix="/papers", tags=["papers"])


@router.get("", response_model=list[PaperOut])
async def list_papers(
    db: DBSession,
    _: AdminUser,
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """管理首页：列出资料，支持状态筛选、标题搜索和分页。"""
    repo = PaperRepository(db)
    papers, total = repo.list_all(
        status_filter=status_filter,
        search_query=q,
        page=page,
        size=size,
    )
    return papers


@router.get("/{paper_id}", response_model=PaperOut)
async def get_paper(paper_id: int, db: DBSession, _: AdminUser):
    repo = PaperRepository(db)
    paper = repo.get_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="未找到")
    return paper


@router.post("", response_model=PaperOut, status_code=201)
async def create_paper(body: PaperCreate, db: DBSession, _: AdminUser, __: CSRFProtected):
    import slugify
    repo = PaperRepository(db)

    slug = slugify.slugify(body.title)[:60] or "paper"
    suffix = 1
    while repo.slug_exists(slug):
        slug = f"{slug}-{suffix}"
        suffix += 1

    return repo.create(title=body.title, slug=slug, mode=body.mode.value)


@router.delete("/{paper_id}", status_code=204)
async def delete_paper(paper_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    repo = PaperRepository(db)
    if not repo.delete(paper_id):
        raise HTTPException(status_code=404, detail="未找到")


@router.post("/{paper_id}/reprocess", status_code=202)
async def reprocess(paper_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    """重新解析。"""
    repo = PaperRepository(db)
    paper = repo.get_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="未找到")
    if not paper.source_file_id:
        raise HTTPException(status_code=400, detail="无源文件")

    repo.update_status(paper_id, "queued")

    from ..queue import enqueue_parse_job
    await enqueue_parse_job(paper_id=paper.id, source_file_id=paper.source_file_id)
    return {"status": "queued"}
