"""媒体资源路由。对应 SPEC 13: /api/assets/{id}

经过访问策略控制的媒体读取。
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..config import settings
from ..deps import AdminUser, DBSession
from ..models import Asset
from ..storage import get_storage

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("/{asset_id}")
async def get_asset(asset_id: int, db: DBSession, _: AdminUser):
    """管理员读取私有媒体。"""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="未找到")
    storage = get_storage()
    namespace = settings.assets_namespace
    data = storage.get(namespace, asset.storage_key)
    return Response(
        content=data,
        media_type=asset.media_type if asset.media_type.startswith("image/") else "application/octet-stream",
    )


@router.get("/{asset_id}/public")
async def get_public_asset(asset_id: int, db: DBSession):
    """访客读取公开媒体（仅 is_public=True）。"""
    asset = db.get(Asset, asset_id)
    if not asset or not asset.is_public:
        raise HTTPException(status_code=404, detail="未找到")
    storage = get_storage()
    data = storage.get(settings.assets_namespace, asset.storage_key)
    return Response(
        content=data,
        media_type=asset.media_type if asset.media_type.startswith("image/") else "application/octet-stream",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
