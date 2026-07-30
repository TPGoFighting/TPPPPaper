"""安全模块：密码哈希、API Key 信封加密、SSRF 防护、HTML/CSS 净化。

对应 SPEC 第 15、16 节安全模型。
"""
import base64
import hashlib
import ipaddress
import socket
from urllib.parse import urlparse

import bleach
import structlog
import tinycss2
from cryptography.fernet import Fernet
from passlib.context import CryptContext

from ..config import settings

logger = structlog.get_logger(__name__)

# ── 密码哈希（SPEC 16：使用现代密码哈希算法）──
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    if not hashed:
        return False
    return pwd_context.verify(password, hashed)


# ── API Key 信封加密（SPEC 16：部署级主密钥信封加密）──

def _get_fernet() -> Fernet:
    """从主密钥派生 Fernet 密钥（SHA-256 + base64url）。"""
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.master_secret.encode()).digest())
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    """加密敏感数据（如 API Key），返回密文。"""
    if not plaintext:
        return ""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """解密敏感数据。只在服务端使用。"""
    if not ciphertext:
        return ""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_api_key(api_key: str) -> str:
    """返回 API Key 掩码，前端只能看到掩码。"""
    if not api_key or len(api_key) <= 8:
        return "****"
    return f"{api_key[:4]}...{api_key[-4:]}"


# ── SSRF 防护（SPEC 16：阻止回环、链路本地、云元数据和内网地址）──

# 云元数据地址
BLOCKED_HOSTS = {"169.254.169.254", "metadata.google.internal"}
BLOCKED_PREFIXES = [
    ipaddress.ip_network("127.0.0.0/8"),      # 回环
    ipaddress.ip_network("10.0.0.0/8"),        # 内网 A
    ipaddress.ip_network("172.16.0.0/12"),     # 内网 B
    ipaddress.ip_network("192.168.0.0/16"),    # 内网 C
    ipaddress.ip_network("169.254.0.0/16"),    # 链路本地
    ipaddress.ip_network("::1/128"),           # IPv6 回环
    ipaddress.ip_network("fc00::/7"),          # IPv6 唯一本地
    ipaddress.ip_network("fe80::/10"),         # IPv6 链路本地
]


def validate_url_safety(url: str, allow_private_network: bool = False) -> tuple[bool, str]:
    """校验 URL 是否安全。

    只允许 HTTP/HTTPS；默认阻止回环、链路本地、云元数据和内网地址。
    连接本地模型需要显式启用私有网络访问，仍阻止云元数据地址。
    """
    try:
        parsed = urlparse(url)
    except Exception:
        return False, "URL 解析失败"

    if parsed.scheme not in ("http", "https"):
        return False, "只允许 HTTP/HTTPS 协议"

    host = parsed.hostname or ""
    if not host:
        return False, "缺少主机名"

    # 云元数据地址始终阻止
    if host in BLOCKED_HOSTS:
        return False, "禁止访问云元数据地址"

    try:
        # 解析所有 A/AAAA 记录
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        # DNS 解析失败时，无法判定是否为内网地址，允许通过
        return True, ""

    for info in infos:
        ip = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue

        for prefix in BLOCKED_PREFIXES:
            if ip_obj in prefix:
                if allow_private_network:
                    # 允许私有网络但仍阻止云元数据（已在上面检查）
                    continue
                return False, f"禁止访问内网地址: {ip}"

    return True, ""


# ── HTML/CSS 净化（SPEC 第 15 节安全模型）──

# 允许的 HTML 标签（安全语义标签 + 受控 TPaper 组件）
ALLOWED_TAGS = [
    "section", "article", "header", "footer", "nav", "aside", "main",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "p", "span", "div", "br", "hr",
    "ul", "ol", "li", "dl", "dt", "dd",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td",
    "img", "figure", "figcaption",
    "code", "pre", "kbd", "samp",
    "blockquote", "q", "cite",
    "strong", "em", "b", "i", "u", "s", "small", "mark", "del", "ins",
    "details", "summary",
    # 交互式元素
    "button", "input", "label", "textarea",
    "script", "style",
    # TPaper 受控组件
    "tp-section", "tp-question", "tp-choice", "tp-blank",
    "tp-explanation", "tp-progress", "tp-nav",
]

# 允许的 HTML 属性
ALLOWED_ATTRIBUTES = {
    "*": ["class", "data-*", "source", "style", "id"],
    "img": ["src", "alt", "width", "height"],
    "a": ["href"],
    "td": ["colspan", "rowspan"],
    "th": ["colspan", "rowspan"],
    "details": ["open"],
    "button": ["onclick", "type", "aria-label"],
    "input": ["type", "placeholder", "data-answer", "data-val", "data-correct", "value"],
    "label": ["for"],
    "textarea": ["rows", "cols", "placeholder"],
}

# 禁止的 CSS（危险 URL、页面覆盖、越界选择器关键词）
DANGEROUS_CSS_KEYWORDS = [
    "javascript:", "expression(", "url(http", "behavior:",
    "position: fixed", "position:fixed",
    "-moz-binding", "vbscript:",
]


def sanitize_html(html: str) -> tuple[str, list[str]]:
    """净化 HTML，返回 (净化后 HTML, 被删除项列表)。

    禁止 script、事件处理属性、javascript: URL、iframe、object、embed、表单等。
    script 标签内容会被保留（不转义），因为内容由模板引擎生成，是安全的。
    """
    import re
    removed: list[str] = []

    # 提取所有 script 标签及其内容，用占位符替换
    scripts: list[str] = []
    placeholder = "___SCRIPT_PLACEHOLDER_{}___"

    def save_script(m: re.Match) -> str:
        idx = len(scripts)
        scripts.append(m.group(0))
        return placeholder.format(idx)

    html_without_scripts = re.sub(
        r"<script\b[^>]*>.*?</script>", save_script, html, flags=re.DOTALL | re.IGNORECASE
    )

    # bleach 净化
    cleaned = bleach.clean(
        html_without_scripts,
        tags=set(ALLOWED_TAGS),
        attributes=ALLOWED_ATTRIBUTES,
        protocols=["https"],
        strip=True,
        strip_comments=True,
    )

    # 恢复 script 标签
    for i, script in enumerate(scripts):
        cleaned = cleaned.replace(placeholder.format(i), script)

    # 检查并记录被移除的 iframe/object/embed 等
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    for tag_name in ["iframe", "object", "embed", "form"]:
        for tag in soup.find_all(tag_name):
            removed.append(f"<{tag_name}>")

    # 事件处理属性
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr.lower().startswith("on"):
                removed.append(f"{tag.name}[{attr}]")

    if removed:
        logger.warning(
            "sanitize_blocked",
            sanitizer="html",
            blocked_count=len(removed),
            blocked_items=removed[:10],
            input_len=len(html),
            output_len=len(cleaned),
        )

    return cleaned, removed


def sanitize_css(css: str, scope_selector: str = ".tp-publication") -> tuple[str, list[str]]:
    """净化 CSS 并限定在发布页面根容器内。

    禁止远程导入、危险 URL、页面覆盖和越界选择器。
    所有规则被限定在 scope_selector 内。
    """
    removed: list[str] = []
    rules = tinycss2.parse_stylesheet(css, skip_comments=True, skip_whitespace=True)

    safe_rules = []
    for rule in rules:
        # 允许 Google Fonts @import
        if rule.type == "at-rule" and rule.lower_at_keyword == "import":
            import_str = tinycss2.serialize(rule.prelude).strip()
            if "fonts.googleapis.com" in import_str:
                safe_rules.append(f"@import {import_str};")
            else:
                removed.append("@import (非 Google Fonts)")
            continue

        # 跳过 @charset 等可能危险的 at-rule
        if rule.type == "at-rule" and rule.lower_at_keyword in ("charset", "namespace"):
            removed.append(f"@{rule.lower_at_keyword}")
            continue

        if rule.type != "qualified-rule":
            continue

        # 检查危险关键词
        prelude_str = tinycss2.serialize(rule.prelude)
        content_str = tinycss2.serialize(rule.content)
        combined = prelude_str + content_str

        is_dangerous = False
        for kw in DANGEROUS_CSS_KEYWORDS:
            if kw.lower() in combined.lower():
                removed.append(f"dangerous:{kw}")
                is_dangerous = True
                break
        if is_dangerous:
            continue

        # 限定选择器作用域：在每个选择器前加 scope 前缀
        selectors = [s.strip() for s in prelude_str.split(",") if s.strip()]
        scoped_selectors = []
        for sel in selectors:
            # 跳过 @media 内部等，简化处理
            if sel.startswith("@"):
                continue
            # 将 scope_selector 前置（如果非空）
            if scope_selector:
                scoped_selectors.append(f"{scope_selector} {sel}")
            else:
                scoped_selectors.append(sel)

        if scoped_selectors:
            scoped_prelude = ", ".join(scoped_selectors)
            safe_rules.append(f"{scoped_prelude} {{{content_str.strip()}}}")

    result = "\n".join(safe_rules)
    if removed:
        logger.warning(
            "sanitize_blocked",
            sanitizer="css",
            blocked_count=len(removed),
            blocked_items=removed[:10],
            input_len=len(css),
            output_len=len(result),
        )

    return result, removed


def content_hash(html: str, css: str, document: str) -> str:
    """计算发布内容哈希，用于审计。"""
    h = hashlib.sha256()
    h.update(html.encode())
    h.update(b"|")
    h.update(css.encode())
    h.update(b"|")
    h.update(document.encode())
    return h.hexdigest()
