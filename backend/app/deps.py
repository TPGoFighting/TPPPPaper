"""FastAPI 依赖注入：认证、CSRF、分页、速率限制。"""
import hmac
import secrets
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .security import verify_password


# ── 速率限制 ──

class _SlidingWindowLimiter:
    """基于 IP 的滑动窗口速率限制器。"""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, key: str) -> tuple[bool, int]:
        """检查是否允许请求。返回 (allowed, remaining)。"""
        now = time.monotonic()
        cutoff = now - self.window_seconds
        # 清理过期记录
        self._requests[key] = [
            t for t in self._requests[key] if t > cutoff
        ]
        if len(self._requests[key]) >= self.max_requests:
            retry_after = int(self._requests[key][0] + self.window_seconds - now) + 1
            return False, retry_after
        self._requests[key].append(now)
        return True, self.max_requests - len(self._requests[key])

    def reset(self) -> None:
        """重置所有记录（测试用）。"""
        self._requests.clear()


# 全局速率限制器实例
_login_limiter = _SlidingWindowLimiter(
    max_requests=settings.rate_limit_login_per_minute,
    window_seconds=60,
)
_api_limiter = _SlidingWindowLimiter(
    max_requests=settings.rate_limit_api_per_minute,
    window_seconds=60,
)


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP（支持反向代理）。"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit_login(request: Request) -> None:
    """登录接口速率限制：防止暴力破解。"""
    ip = _get_client_ip(request)
    allowed, remaining_or_retry = _login_limiter.is_allowed(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录请求过于频繁，请 {remaining_or_retry} 秒后重试",
            headers={"Retry-After": str(remaining_or_retry)},
        )


def rate_limit_api(request: Request) -> None:
    """通用 API 速率限制。"""
    ip = _get_client_ip(request)
    allowed, remaining_or_retry = _api_limiter.is_allowed(ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"请求过于频繁，请 {remaining_or_retry} 秒后重试",
            headers={"Retry-After": str(remaining_or_retry)},
        )


# ── 认证 ──

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


# ── CSRF 防护 ──

_CSRF_COOKIE_NAME = "tpaper_csrf"
_CSRF_HEADER_NAME = "x-csrf-token"


def get_csrf_token(request: Request) -> str | None:
    """从 Cookie 获取 CSRF token。"""
    return request.cookies.get(_CSRF_COOKIE_NAME)


def generate_csrf_token() -> str:
    """生成新的 CSRF token。"""
    return secrets.token_urlsafe(32)


def require_csrf(
    request: Request,
    x_requested_with: Annotated[str | None, Header()] = None,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> None:
    """CSRF 防护：双重提交 Cookie 模式。

    对应 SPEC 16：所有状态修改接口需要 CSRF 防护。
    验证方式：Cookie 中的 token 必须与请求头中的 token 一致。
    回退兼容：如果没有 CSRF cookie，回退到 X-Requested-With 头检查。
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    csrf_cookie = request.cookies.get(_CSRF_COOKIE_NAME)
    if csrf_cookie and x_csrf_token:
        # 双重提交模式：比较 cookie 和 header 中的 token
        if not hmac.compare_digest(csrf_cookie, x_csrf_token):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token 不匹配",
            )
        return

    # 回退兼容：旧的 header-only 模式
    if not x_requested_with:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="缺少 CSRF 保护头",
        )


def set_csrf_cookie(response) -> str:
    """在响应中设置 CSRF cookie，返回 token 供前端使用。"""
    token = generate_csrf_token()
    response.set_cookie(
        key=_CSRF_COOKIE_NAME,
        value=token,
        httponly=False,  # 前端 JS 需要读取
        samesite="lax",
        secure=settings.env == "prod",
        path="/",
    )
    return token


# ── 便捷类型别名 ──

DBSession = Annotated[Session, Depends(get_db)]
AdminUser = Annotated[str, Depends(require_auth)]
CSRFProtected = Annotated[None, Depends(require_csrf)]
RateLimitLogin = Annotated[None, Depends(rate_limit_login)]
RateLimitAPI = Annotated[None, Depends(rate_limit_api)]


def constant_time_eq(a: str, b: str) -> bool:
    """常量时间字符串比较，防止时序攻击。"""
    return hmac.compare_digest(a.encode(), b.encode())
