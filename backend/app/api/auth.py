"""认证路由。对应 SPEC 13: /api/auth/*"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from itsdangerous import URLSafeTimedSerializer

from ..config import settings
from ..deps import AdminUser, CSRFProtected, DBSession, RateLimitLogin, require_auth, set_csrf_cookie
from ..schemas import LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


def _create_session_cookie(username: str) -> str:
    serializer = URLSafeTimedSerializer(settings.session_secret, salt="tpaper-session")
    return serializer.dumps({"username": username})


@router.post("/login")
async def login(body: LoginIn, response: Response, _rate_limit: RateLimitLogin = None):
    """管理员登录（含速率限制）。"""
    # MVP：从环境变量配置的管理员账号校验
    expected_user = settings.admin_username
    if body.username != expected_user or not settings.admin_password_hash:
        # 开发环境：允许默认密码 admin/admin（仅未配置 hash 时）
        if settings.env == "dev" and body.username == "admin" and body.password == "admin":
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )
    else:
        from ..security import verify_password
        if not verify_password(body.password, settings.admin_password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

    session_id = _create_session_cookie(body.username)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=(settings.env == "prod"),
        samesite="lax",
        path="/",
    )
    # 登录成功时下发 CSRF token
    set_csrf_cookie(response)
    return {"username": body.username, "logged_in": True}


@router.post("/logout")
async def logout(response: Response, _csrf: CSRFProtected = None):
    """登出，清除会话 Cookie。"""
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie("tpaper_csrf", path="/")
    return {"logged_out": True}


@router.get("/me")
async def me(username: AdminUser):
    """获取当前登录管理员。"""
    return {"username": username, "role": "admin"}
