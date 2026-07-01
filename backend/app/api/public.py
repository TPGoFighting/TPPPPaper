"""公开读取路由。对应 SPEC 13: /api/public/papers/{slug}

访客通过 /p/{slug} 访问已发布页面，无需登录。
只读取已发布快照，不暴露草稿与源文件。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from ..deps import DBSession
from ..models import Paper, PublicationVersion

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/papers/{slug}")
async def get_public_paper(slug: str, db: DBSession):
    """公开不可变内容读取。"""
    paper = db.query(Paper).filter(Paper.slug == slug).first()
    if not paper or not paper.current_publication_id:
        raise HTTPException(status_code=404, detail="页面不可用或已撤回")

    pub = db.get(PublicationVersion, paper.current_publication_id)
    if not pub or pub.is_withdrawn:
        raise HTTPException(status_code=404, detail="页面已撤回")

    return {
        "slug": slug,
        "title": paper.title,
        "version": pub.version,
        "content_hash": pub.content_hash,
        "published_at": pub.published_at,
        "compiled_html": pub.compiled_html,
        "compiled_css": pub.compiled_css,
        "document": pub.document_snapshot,
    }


@router.get("/papers/{slug}/page", response_class=HTMLResponse)
async def get_public_page(slug: str, db: DBSession):
    """渲染公开复习页（内嵌编译后的 HTML/CSS）。"""
    paper = db.query(Paper).filter(Paper.slug == slug).first()
    if not paper or not paper.current_publication_id:
        return HTMLResponse(
            content="<h1>页面不可用</h1><p>此链接已失效或已被撤回。</p>",
            status_code=404,
        )

    pub = db.get(PublicationVersion, paper.current_publication_id)
    if not pub or pub.is_withdrawn:
        return HTMLResponse(
            content="<h1>页面已撤回</h1><p>此内容已不再公开。</p>",
            status_code=404,
        )

    # 严格 CSP（允许交互式试卷必要的脚本和样式）
    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{paper.title}</title>
<style>
{pub.compiled_css}
</style>
</head>
<body>
{pub.compiled_html}
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={
            "Content-Security-Policy": (
                "default-src 'self'; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "img-src 'self' data:; "
                "script-src 'unsafe-inline'; "
                "object-src 'none'; "
                "base-uri 'none'"
            ),
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Referrer-Policy": "no-referrer",
        },
    )
