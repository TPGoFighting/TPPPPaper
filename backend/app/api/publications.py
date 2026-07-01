"""发布路由。对应 SPEC 13: /api/publications/*

对应 SPEC 7.5：发布前必须通过结构化校验、组件引用校验、
HTML/CSS 安全校验和响应式基础检查。每次发布产生不可变 PublicationVersion。
"""
import hashlib

from fastapi import APIRouter, Depends, HTTPException

from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import Paper, PaperDraft, PublicationVersion
from ..schemas import PublicationOut, PublishIn
from ..security import content_hash, sanitize_css, sanitize_html

router = APIRouter(prefix="/publications", tags=["publications"])


@router.post("/precheck")
async def precheck(draft_id: int, db: DBSession, _: AdminUser):
    """发布预检：校验结构、净化 HTML/CSS，返回被删除项。"""
    draft = db.get(PaperDraft, draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="草稿未找到")

    issues: list[str] = []
    removed: list[str] = []

    # 1. 结构化校验
    from ..schemas import PaperDocument
    try:
        doc = PaperDocument.model_validate(draft.document)
        errors = doc.semantic_validate()
        issues.extend(errors)
    except Exception as e:
        issues.append(f"文档结构错误: {e}")

    # 2. HTML/CSS 安全校验
    clean_html, html_removed = sanitize_html(draft.presentation_html)
    clean_css, css_removed = sanitize_css(draft.theme_css, scope_selector="")
    removed.extend(html_removed)
    removed.extend(css_removed)

    # 3. 响应式基础检查（简化：检查是否包含 viewport 相关 CSS 或媒体查询）
    has_responsive = "@media" in draft.theme_css or "viewport" in draft.theme_css.lower()
    if not has_responsive:
        issues.append("建议添加响应式 @media 规则")

    return {
        "can_publish": len([i for i in issues if "错误" in i or "缺少" in i or "必须" in i]) == 0,
        "issues": issues,
        "removed": removed,
        "clean_html_preview": clean_html[:500],
    }


@router.post("", response_model=PublicationOut, status_code=201)
async def publish(body: PublishIn, db: DBSession, admin: AdminUser, _: CSRFProtected):
    """发布：编译、净化并冻结新版本。"""
    draft = db.get(PaperDraft, body.draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="草稿未找到")
    if not draft.is_valid:
        raise HTTPException(status_code=400, detail="草稿未通过校验，无法发布")

    paper = db.get(Paper, draft.paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="资料未找到")

    # 净化编译
    clean_html, _ = sanitize_html(draft.presentation_html)
    clean_css, _ = sanitize_css(draft.theme_css, scope_selector="")
    doc_str = __import__("json").dumps(draft.document, ensure_ascii=False, sort_keys=True)
    chash = content_hash(clean_html, clean_css, doc_str)

    # 计算新版本号
    last_version = (
        db.query(PublicationVersion)
        .filter(PublicationVersion.paper_id == paper.id)
        .order_by(PublicationVersion.version.desc())
        .first()
    )
    new_version = (last_version.version + 1) if last_version else 1

    pub = PublicationVersion(
        paper_id=paper.id,
        version=new_version,
        compiled_html=clean_html,
        compiled_css=clean_css,
        document_snapshot=draft.document,
        content_hash=chash,
        source_draft_version=draft.version,
        published_by=admin,
    )
    db.add(pub)
    db.flush()

    # 更新 Paper 指向最新发布
    paper.current_publication_id = pub.id
    paper.status = "published"
    db.commit()
    db.refresh(pub)
    return pub


@router.get("/{publication_id}", response_model=PublicationOut)
async def get_publication(publication_id: int, db: DBSession, _: AdminUser):
    pub = db.get(PublicationVersion, publication_id)
    if not pub:
        raise HTTPException(status_code=404, detail="未找到")
    return pub


@router.get("/paper/{paper_id}", response_model=list[PublicationOut])
async def list_publications(paper_id: int, db: DBSession, _: AdminUser):
    return (
        db.query(PublicationVersion)
        .filter(PublicationVersion.paper_id == paper_id)
        .order_by(PublicationVersion.version.desc())
        .all()
    )


@router.post("/{publication_id}/withdraw", status_code=202)
async def withdraw(publication_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    """撤回发布。撤回后公开 slug 返回明确的不可用页面。"""
    pub = db.get(PublicationVersion, publication_id)
    if not pub:
        raise HTTPException(status_code=404, detail="未找到")
    pub.is_withdrawn = True

    paper = db.get(Paper, pub.paper_id)
    if paper and paper.current_publication_id == pub.id:
        paper.current_publication_id = None
        paper.status = "pending_review"
    db.commit()
    return {"withdrawn": True}
