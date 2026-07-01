"""模型配置路由。对应 SPEC 13: /api/model-profiles/*"""
from fastapi import APIRouter, Depends, HTTPException

from ..deps import AdminUser, CSRFProtected, DBSession
from ..models import ModelProfile
from ..schemas import (
    ModelProfileCreate,
    ModelProfileOut,
    ModelProfileUpdate,
    TestConnectionIn,
)
from ..security import decrypt_secret, encrypt_secret, mask_api_key
from ..adapters import OpenAICompatibleAdapter

router = APIRouter(prefix="/model-profiles", tags=["model-profiles"])


def _to_out(profile: ModelProfile) -> ModelProfileOut:
    out = ModelProfileOut.model_validate(profile)
    if profile.encrypted_api_key:
        out.api_key_masked = mask_api_key(decrypt_secret(profile.encrypted_api_key))
    return out


@router.get("", response_model=list[ModelProfileOut])
async def list_profiles(db: DBSession, _: AdminUser):
    profiles = db.query(ModelProfile).order_by(ModelProfile.created_at.desc()).all()
    return [_to_out(p) for p in profiles]


@router.post("", response_model=ModelProfileOut, status_code=201)
async def create_profile(body: ModelProfileCreate, db: DBSession, _: AdminUser, __: CSRFProtected):
    if db.query(ModelProfile).filter(ModelProfile.name == body.name).first():
        raise HTTPException(status_code=409, detail="名称已存在")
    profile = ModelProfile(
        name=body.name,
        protocol=body.protocol.value,
        base_url=body.base_url,
        encrypted_api_key=encrypt_secret(body.api_key) if body.api_key else "",
        text_model=body.text_model,
        multimodal_model=body.multimodal_model,
        supports_vision=body.supports_vision,
        timeout_seconds=body.timeout_seconds,
        max_concurrency=body.max_concurrency,
        max_retries=body.max_retries,
        allow_private_network=body.allow_private_network,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return _to_out(profile)


@router.get("/{profile_id}", response_model=ModelProfileOut)
async def get_profile(profile_id: int, db: DBSession, _: AdminUser):
    profile = db.get(ModelProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="未找到")
    return _to_out(profile)


@router.patch("/{profile_id}", response_model=ModelProfileOut)
async def update_profile(
    profile_id: int, body: ModelProfileUpdate, db: DBSession, _: AdminUser, __: CSRFProtected
):
    profile = db.get(ModelProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="未找到")
    data = body.model_dump(exclude_unset=True)
    if "api_key" in data:
        api_key = data.pop("api_key")
        if api_key:
            profile.encrypted_api_key = encrypt_secret(api_key)
    for k, v in data.items():
        setattr(profile, k, v)
    db.commit()
    db.refresh(profile)
    return _to_out(profile)


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(profile_id: int, db: DBSession, _: AdminUser, __: CSRFProtected):
    profile = db.get(ModelProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="未找到")
    db.delete(profile)
    db.commit()


@router.post("/test-connection")
async def test_connection(body: TestConnectionIn, _: AdminUser):
    """测试模型连接。"""
    adapter = OpenAICompatibleAdapter(
        base_url=body.base_url,
        api_key=body.api_key,
        model=body.model,
        allow_private_network=body.allow_private_network,
    )
    result = await adapter.test_connection()
    return {
        "success": result.success,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "usage": result.usage,
        "error": result.error,
    }
