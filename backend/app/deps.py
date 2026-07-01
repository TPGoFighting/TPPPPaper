"""FastAPI 依赖注入：认证、CSRF、分页。"""
import hmac
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .security import verify_password


def get_session_id(request: Request) -> str | None:
    """从 Cookie 读取会话 ID。"""
    return request.cookies.get(settings.session_cookie_name)


def require_auth(request: Request) -> str:
    """管理员认证依赖。

    使用 Secure、HttpOnly、SameSite Cookie 会话。
    MVP 使用 itsdangerous 签名的 Cookie 会话。
    """
    session_id = get_session_id(request)
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未登录",
        )
    # 验证签名会话
    from itsdangerous import BadSignature, URLSafeTimedSerializer

    serializer = URLSafeTimedSerializer(settings.session_secret, salt="tpaper-session")
    try:
        data = serializer.loads(session_id, max_age=settings.session_max_age_seconds)
        username = data.get("username")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效会话")
        return username
    except BadSignature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已过期或无效",
        )


def require_csrf(
    request: Request,
    x_requested_with: Annotated[str | None, Header()] = None,
) -> None:
    """CSRF 防护：状态修改接口需要 X-Requested-With 头。

    对应 SPEC 16：所有状态修改接口需要 CSRF 防护。
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    # 简单 CSRF 防护：要求自定义头（跨域简单请求无法携带自定义头）
    if not x_requested_with:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少 CSRF 保护头",
        )


# 便捷类型别名
DBSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[str, Depends(require_auth)]
CSRFProtected = Annotated[None, Depends(require_csrf)]


def constant_time_eq(a: str, b: str) -> bool:
    """常量时间字符串比较，防止时序攻击。"""
    return hmac.compare_digest(a.encode(), b.encode())
