"""安全加固测试：速率限制、CSRF token、上传大小限制、文件类型检测。

对应安全检查清单 §7.2 短期安全加固。
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))


# ── 速率限制测试 ──

class TestRateLimiter:
    """滑动窗口速率限制器测试。"""

    def test_allows_requests_within_limit(self):
        from app.deps import _SlidingWindowLimiter

        limiter = _SlidingWindowLimiter(max_requests=5, window_seconds=60)
        for i in range(5):
            allowed, remaining = limiter.is_allowed("test-ip")
            assert allowed, f"Request {i+1} should be allowed"
            assert remaining == 5 - i - 1

    def test_blocks_requests_over_limit(self):
        from app.deps import _SlidingWindowLimiter

        limiter = _SlidingWindowLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("test-ip")
        allowed, retry_after = limiter.is_allowed("test-ip")
        assert not allowed
        assert retry_after > 0

    def test_different_ips_have_separate_limits(self):
        from app.deps import _SlidingWindowLimiter

        limiter = _SlidingWindowLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("ip-a")
        limiter.is_allowed("ip-a")
        # ip-a 已满
        allowed_a, _ = limiter.is_allowed("ip-a")
        assert not allowed_a
        # ip-b 仍然可用
        allowed_b, _ = limiter.is_allowed("ip-b")
        assert allowed_b

    def test_reset_clears_all(self):
        from app.deps import _SlidingWindowLimiter

        limiter = _SlidingWindowLimiter(max_requests=1, window_seconds=60)
        limiter.is_allowed("test-ip")
        allowed, _ = limiter.is_allowed("test-ip")
        assert not allowed
        limiter.reset()
        allowed, _ = limiter.is_allowed("test-ip")
        assert allowed


class TestRateLimitDependencies:
    """速率限制 FastAPI 依赖测试。"""

    def test_login_rate_limit_raises_429(self):
        from app.deps import _login_limiter, rate_limit_login

        _login_limiter.reset()
        # 用完配额
        for _ in range(_login_limiter.max_requests):
            _login_limiter.is_allowed("test-ip")

        # 模拟请求
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "test-ip"

        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            rate_limit_login(request)
        assert exc_info.value.status_code == 429
        assert "Retry-After" in exc_info.value.headers

    def test_api_rate_limit_allows_normal_traffic(self):
        from app.deps import _api_limiter, rate_limit_api

        _api_limiter.reset()
        request = MagicMock()
        request.headers = {}
        request.client = MagicMock()
        request.client.host = "normal-ip"

        # 正常流量不应被限制
        rate_limit_api(request)  # 不应抛出异常


# ── CSRF Token 测试 ──

class TestCSRFToken:
    """CSRF 双重提交 Cookie 模式测试。"""

    def test_generate_csrf_token_is_unique(self):
        from app.deps import generate_csrf_token

        t1 = generate_csrf_token()
        t2 = generate_csrf_token()
        assert t1 != t2
        assert len(t1) > 20  # 足够的熵

    def test_csrf_passes_with_matching_token(self):
        from app.deps import require_csrf

        token = "test-csrf-token-123"
        request = MagicMock()
        request.method = "POST"
        request.cookies = {"tpaper_csrf": token}

        # 匹配 token 应通过
        require_csrf(request, x_csrf_token=token)

    def test_csrf_fails_with_mismatched_token(self):
        from app.deps import require_csrf
        from fastapi import HTTPException

        request = MagicMock()
        request.method = "POST"
        request.cookies = {"tpaper_csrf": "correct-token"}

        with pytest.raises(HTTPException) as exc_info:
            require_csrf(request, x_csrf_token="wrong-token")
        assert exc_info.value.status_code == 403
        assert "不匹配" in exc_info.value.detail

    def test_csrf_fallback_to_header_only(self):
        from app.deps import require_csrf

        request = MagicMock()
        request.method = "POST"
        request.cookies = {}  # 没有 CSRF cookie

        # 回退到 X-Requested-With 头
        require_csrf(request, x_requested_with="XMLHttpRequest")

    def test_csrf_fails_without_any_protection(self):
        from app.deps import require_csrf
        from fastapi import HTTPException

        request = MagicMock()
        request.method = "POST"
        request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            require_csrf(request)
        assert exc_info.value.status_code == 403

    def test_csrf_skips_safe_methods(self):
        from app.deps import require_csrf

        request = MagicMock()
        for method in ("GET", "HEAD", "OPTIONS"):
            request.method = method
            request.cookies = {}
            # 不应抛出异常
            require_csrf(request)

    def test_set_csrf_cookie(self):
        from app.deps import set_csrf_cookie

        response = MagicMock()
        token = set_csrf_cookie(response)
        assert len(token) > 20
        response.set_cookie.assert_called_once()
        call_kwargs = response.set_cookie.call_args.kwargs
        assert call_kwargs["key"] == "tpaper_csrf"
        assert call_kwargs["httponly"] is False  # JS 需要读取


# ── 上传文件大小限制测试 ──

class TestUploadSizeLimit:
    """上传文件大小限制验证测试。"""

    def test_config_has_upload_limit(self):
        from app.config import settings

        assert settings.upload_max_size_mb > 0
        assert settings.upload_max_size_mb <= 500  # 合理上限

    def test_allowed_extensions_are_restrictive(self):
        from app.api.uploads import ALLOWED_EXTENSIONS

        assert ".pdf" in ALLOWED_EXTENSIONS
        assert ".docx" in ALLOWED_EXTENSIONS
        assert ".exe" not in ALLOWED_EXTENSIONS
        assert ".sh" not in ALLOWED_EXTENSIONS
        assert ".py" not in ALLOWED_EXTENSIONS
        assert ".php" not in ALLOWED_EXTENSIONS

    def test_allowed_mimes_match_extensions(self):
        from app.api.uploads import ALLOWED_EXTENSIONS, ALLOWED_MIMES

        assert "application/pdf" in ALLOWED_MIMES
        assert "image/png" in ALLOWED_MIMES
        assert "image/jpeg" in ALLOWED_MIMES
        assert "text/html" not in ALLOWED_MIMES
        assert "application/javascript" not in ALLOWED_MIMES

    def test_file_signatures_cover_all_allowed_types(self):
        from app.api.uploads import ALLOWED_MIMES, FILE_SIGNATURES

        detected_mimes = set(FILE_SIGNATURES.values())
        for mime in ALLOWED_MIMES:
            assert mime in detected_mimes, (
                f"MIME type {mime} has no magic bytes signature — "
                f"file type detection will fail for this type"
            )


# ── 文件类型检测（防伪造 MIME）测试 ──

class TestFileTypeDetection:
    """文件类型检测测试：验证 magic bytes 能正确识别文件类型。"""

    def test_detect_pdf(self):
        from app.api.uploads import detect_file_type

        pdf_header = b"%PDF-1.4\nsome content"
        assert detect_file_type(pdf_header) == "application/pdf"

    def test_detect_docx(self):
        from app.api.uploads import detect_file_type

        # DOCX 是 ZIP 格式，以 PK\x03\x04 开头
        docx_header = b"PK\x03\x04\x14\x00\x00\x00"
        assert detect_file_type(docx_header) == (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_detect_png(self):
        from app.api.uploads import detect_file_type

        png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
        assert detect_file_type(png_header) == "image/png"

    def test_detect_jpeg(self):
        from app.api.uploads import detect_file_type

        jpeg_header = b"\xff\xd8\xff\xe0" + b"\x00" * 20
        assert detect_file_type(jpeg_header) == "image/jpeg"

    def test_reject_unknown_type(self):
        from app.api.uploads import detect_file_type

        # 随机数据不应匹配任何已知类型
        unknown = b"random binary data that is not a known format"
        assert detect_file_type(unknown) == ""

    def test_reject_html_disguised_as_pdf(self):
        from app.api.uploads import detect_file_type

        # HTML 内容伪装成 PDF（扩展名为 .pdf 但内容不对）
        fake_pdf = b"<html><body>This is not a PDF</body></html>"
        detected = detect_file_type(fake_pdf)
        assert detected != "application/pdf", (
            "HTML content should not be detected as PDF"
        )

    def test_reject_javascript_disguised_as_image(self):
        from app.api.uploads import detect_file_type

        fake_image = b"alert('xss');"
        detected = detect_file_type(fake_image)
        assert detected not in ("image/png", "image/jpeg"), (
            "JavaScript content should not be detected as image"
        )

    def test_reject_exe_disguised_as_docx(self):
        from app.api.uploads import detect_file_type

        # ELF binary 伪装成 DOCX
        fake_docx = b"\x7fELF\x02\x01\x01\x00"
        detected = detect_file_type(fake_docx)
        assert detected != (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ), "ELF binary should not be detected as DOCX"


# ── 安全检查清单验证 ──

class TestSecurityChecklist:
    """安全检查清单 §7 自动化验证。"""

    def test_env_not_in_git(self):
        """确认 .env 在 .gitignore 中。"""
        gitignore = ROOT / ".gitignore"
        assert gitignore.exists(), ".gitignore 文件不存在"
        content = gitignore.read_text()
        assert ".env" in content, ".env 未被 gitignore"

    def test_master_secret_has_min_length(self):
        """master_secret 有最小长度要求。"""
        from app.config import Settings

        field_info = Settings.model_fields["master_secret"]
        assert field_info.metadata, "master_secret 应有元数据约束"
        # Pydantic v2 用 Field(min_length=32)
        assert any(
            getattr(m, "min_length", None) == 32
            for m in field_info.metadata
        ), "master_secret 最小长度应为 32"

    def test_session_secret_has_min_length(self):
        """session_secret 有最小长度要求。"""
        from app.config import Settings

        field_info = Settings.model_fields["session_secret"]
        assert any(
            getattr(m, "min_length", None) == 32
            for m in field_info.metadata
        ), "session_secret 最小长度应为 32"

    def test_rate_limit_config_exists(self):
        """速率限制配置存在且合理。"""
        from app.config import settings

        assert settings.rate_limit_login_per_minute > 0
        assert settings.rate_limit_login_per_minute <= 30, "登录限制应较严格"
        assert settings.rate_limit_api_per_minute > 0
        assert settings.rate_limit_api_per_minute <= 600, "API 限制应合理"

    def test_cors_not_wildcard(self):
        """CORS origins 不应为 *。"""
        from app.config import settings

        assert "*" not in settings.cors_origins, "CORS origins 不应允许所有来源"
        assert len(settings.cors_origins) > 0, "CORS origins 不应为空"

    def test_login_endpoint_has_rate_limit(self):
        """登录接口必须有速率限制。"""
        from app.api.auth import login
        import inspect

        sig = inspect.signature(login)
        param_names = list(sig.parameters.keys())
        assert "_rate_limit" in param_names, (
            "login 端点缺少 RateLimitLogin 依赖"
        )

    def test_logout_endpoint_has_csrf(self):
        """登出接口必须有 CSRF 防护。"""
        from app.api.auth import logout
        import inspect

        sig = inspect.signature(logout)
        param_names = list(sig.parameters.keys())
        assert "_csrf" in param_names, (
            "logout 端点缺少 CSRFProtected 依赖"
        )

    def test_all_state_changing_endpoints_have_csrf(self):
        """自动化扫描所有写/修改状态 (POST/PUT/PATCH/DELETE) API 端点，必须包含 CSRF 防护。"""
        import inspect
        from app.main import app
        from app.deps import CSRFProtected

        # 免除 CSRF 的特例（例如无需 CSRF 的纯匿名/公开/登录端点）
        EXEMPT_PATHS = {"/api/auth/login", "/api/public/submit-answers"}

        missing_csrf_endpoints = []
        for route in app.routes:
            methods = getattr(route, "methods", set())
            path = getattr(route, "path", "")
            if any(m in methods for m in ("POST", "PUT", "PATCH", "DELETE")):
                if path in EXEMPT_PATHS:
                    continue
                endpoint_fn = getattr(route, "endpoint", None)
                if not endpoint_fn:
                    continue
                sig = inspect.signature(endpoint_fn)
                params = sig.parameters.values()
                has_csrf = any(
                    p.annotation == CSRFProtected or "csrf" in p.name.lower() or "CSRF" in str(p.annotation)
                    for p in params
                )
                if not has_csrf:
                    missing_csrf_endpoints.append(f"{methods} {path} ({endpoint_fn.__name__})")

        assert not missing_csrf_endpoints, f"发现缺少 CSRFProtected 依赖的状态变更接口: {missing_csrf_endpoints}"


class TestPreprocessThreadSafety:
    """PDF 多线程预处理线程安全性测试。"""

    def test_multithreaded_pdf_ocr_preprocessing(self):
        """验证多线程并行 OCR 时不会发生句柄竞争或 Segfault。"""
        try:
            import fitz
        except ImportError:
            pytest.skip("PyMuPDF 未安装")

        from worker.pipeline.preprocess import preprocess_pdf

        # 创建一个 3 页的简单测试 PDF 内存流
        doc = fitz.open()
        for i in range(3):
            page = doc.new_page()
            # 插入少于 50 字符以触发 needs_multimodal/OCR 分支
            page.insert_text((50, 50), f"P{i+1}")
        pdf_bytes = doc.tobytes()
        doc.close()

        # 调用预处理，在多线程下测试 OCR 渲染逻辑
        res = preprocess_pdf(pdf_bytes, include_page_images=True)
        assert res["page_count"] == 3
        assert len(res["pages"]) == 3


class TestModelProfileTestConnection:
    """测试模型配置 test_connection 接口。"""

    @pytest.mark.asyncio
    async def test_test_connection_via_profile_id(self, db_session):
        from app.database import Base
        from app.models import ModelProfile
        from app.api.model_profiles import test_connection
        from app.schemas import TestConnectionIn
        from app.security import encrypt_secret

        Base.metadata.create_all(bind=db_session.get_bind())

        profile = ModelProfile(
            name="TestProfile",
            protocol="openai_compatible",
            base_url="https://api.openai.com/v1",
            encrypted_api_key=encrypt_secret("sk-fake-key-for-test"),
            text_model="gpt-4o",
            multimodal_model="gpt-4o",
        )
        db_session.add(profile)
        db_session.commit()
        db_session.refresh(profile)

        # 模拟通过 profile_id 测试（不穿明文 api_key）
        body = TestConnectionIn(profile_id=profile.id)

        # mock adapter 方法
        from unittest.mock import AsyncMock, patch
        with patch("app.api.model_profiles.OpenAICompatibleAdapter") as MockAdapter:
            mock_inst = AsyncMock()
            mock_inst.test_connection.return_value = MagicMock(
                success=True, model="gpt-4o", latency_ms=120, usage={}, error=""
            )
            MockAdapter.return_value = mock_inst

            res = await test_connection(body=body, db=db_session, _=MagicMock(), __=MagicMock())
            assert res["success"] is True
            assert res["latency_ms"] == 120
            # 验证正确的 API key 已从数据库自动解密并传递给 adapter
            MockAdapter.assert_called_once()
            assert MockAdapter.call_args.kwargs["api_key"] == "sk-fake-key-for-test"


class TestMetricsSecurity:
    """测试 Metrics 接口安全防护。"""

    def test_dashboard_metrics_unauthorized(self, unauth_client):
        # 1. 未授权请求必须拒绝 (401 Unauthorized)
        res_unauth = unauth_client.get("/api/metrics/dashboard")
        assert res_unauth.status_code == 401

    def test_dashboard_metrics_authorized(self, test_client):
        # 2. 已授权管理员请求返回 200 OK 并聚合指标
        res_auth = test_client.get("/api/metrics/dashboard")
        assert res_auth.status_code == 200
        data = res_auth.json()
        assert "generated_at" in data
        assert "paper_status" in data
        assert "job_metrics" in data


class TestWorkerPipelineRobustness:
    """测试 Celery Worker 任务容错与事务回滚救援机制。"""

    def test_process_paper_exception_rollback(self, db_session):
        pytest.importorskip("celery")
        from unittest.mock import patch
        from app.database import Base
        from app.models import Paper, SourceFile
        from worker.tasks import process_paper

        Base.metadata.create_all(bind=db_session.get_bind())

        source = SourceFile(
            original_filename="test.pdf",
            stored_filename="test.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            file_hash="fakehash",
        )
        db_session.add(source)
        db_session.commit()

        paper = Paper(
            title="Rollback Test Paper",
            slug="rollback-test-paper",
            mode="faithful_transcription",
            status="parsing",
            source_file_id=source.id,
        )
        db_session.add(paper)
        db_session.commit()

        # 模拟在 _run_async 中抛出 pipeline 致命异常
        with patch("worker.tasks._run_async", side_effect=RuntimeError("Simulated Pipeline Crash")):
            with patch("worker.tasks._get_db", return_value=db_session):
                process_paper(paper.id, source.id)

        # 验证事务经由 db.rollback() 恢复，且 paper.status="failed"，并保存了 error_message
        db_session.refresh(paper)
        assert paper.status == "failed"
        assert "Simulated Pipeline Crash" in paper.error_message


class TestDraftUpdateAndAIModify:
    """测试草稿更新联动渲染与 AI 局部修题 XML 隔离机制。"""

    @pytest.mark.asyncio
    async def test_update_draft_auto_rerenders_html(self, db_session):
        from app.database import Base
        from app.models import Paper, PaperDraft
        from app.api.drafts import update_draft
        from app.schemas import DraftUpdate

        Base.metadata.create_all(bind=db_session.get_bind())

        paper = Paper(title="Draft Test", slug="draft-test", mode="faithful_transcription")
        db_session.add(paper)
        db_session.commit()

        initial_doc = {
            "title": "Draft Test",
            "sections": [{"id": "s1", "title": "Sec 1", "question_ids": ["q1"]}],
            "questions": [{
                "id": "q1",
                "number": 1,
                "type": "single_choice",
                "stem": "Old Question Stem",
                "score": 5,
                "options": [{"key": "A", "content": "Opt A"}],
                "correct_keys": ["A"],
                "explanation": "Exp",
                "needs_review": False,
                "is_ai_generated": False,
            }],
        }

        draft = PaperDraft(
            paper_id=paper.id,
            version=1,
            document=initial_doc,
            presentation_html="<p>Old Presentation</p>",
            theme_css="",
            is_valid=True,
            validation_result={"errors": [], "is_valid": True},
        )
        db_session.add(draft)
        db_session.commit()

        updated_doc = dict(initial_doc)
        updated_doc["questions"][0]["stem"] = "New Question Stem Updated"

        body = DraftUpdate(document=updated_doc)
        res = await update_draft(
            draft_id=draft.id,
            body=body,
            db=db_session,
            _=MagicMock(),
            __=MagicMock(),
        )

        # 验证 presentation_html 已从旧值自动联动重渲染包含最新 Stem 的 HTML
        assert "New Question Stem Updated" in res.presentation_html
        assert "Old Presentation" not in res.presentation_html

    @pytest.mark.asyncio
    async def test_ai_modify_uses_xml_data_fencing(self, db_session):
        from unittest.mock import AsyncMock, patch
        from app.database import Base
        from app.models import ModelProfile, Paper, PaperDraft
        from app.api.drafts import ai_modify
        from app.security import encrypt_secret

        Base.metadata.create_all(bind=db_session.get_bind())

        profile = ModelProfile(
            name="TestProfile",
            protocol="openai_compatible",
            base_url="https://api.openai.com/v1",
            encrypted_api_key=encrypt_secret("sk-fake-key"),
            text_model="gpt-4o",
            is_active=True,
        )
        db_session.add(profile)

        paper = Paper(title="AI Modify Test", slug="ai-modify-test", mode="faithful_transcription")
        db_session.add(paper)
        db_session.commit()

        doc = {
            "questions": [{
                "id": "q1",
                "number": 1,
                "stem": "Question 1",
            }],
        }
        draft = PaperDraft(paper_id=paper.id, version=1, document=doc, presentation_html="", theme_css="")
        db_session.add(draft)
        db_session.commit()

        body = {"question_id": "q1", "instruction": "改成选择题"}

        with patch("app.adapters.OpenAICompatibleAdapter") as MockAdapter:
            mock_inst = AsyncMock()
            mock_inst.chat.return_value = MagicMock(
                success=True, content='{"id": "q1", "stem": "Modified Question"}'
            )
            MockAdapter.return_value = mock_inst

            await ai_modify(draft_id=draft.id, body=body, db=db_session, _=MagicMock(), __=MagicMock())

            MockAdapter.return_value.chat.assert_called_once()
            called_messages = MockAdapter.return_value.chat.call_args[0][0]
            user_msg = called_messages[1]["content"]
            # 验证原题目与指令包含在 XML 隔离数据标签中
            assert "<original_question>" in user_msg
            assert "</original_question>" in user_msg
            assert "<admin_instruction>" in user_msg
            assert "</admin_instruction>" in user_msg


class TestUploadMimeAliasValidation:
    """测试上传接口 MIME 别名容错与二进制签名防伪造。"""

    @pytest.mark.asyncio
    async def test_upload_mime_alias_allowed(self, db_session):
        from unittest.mock import AsyncMock, patch
        from app.database import Base
        from app.api.uploads import upload_file

        Base.metadata.create_all(bind=db_session.get_bind())

        # 模拟真实的 PDF 二进制头，但客户端传递 image/jpg 或 octet-stream 兼容别名
        pdf_bytes = b"%PDF-1.4\nTest PDF Content"
        mock_file = MagicMock()
        mock_file.filename = "test.pdf"
        mock_file.content_type = "application/octet-stream"
        mock_file.read = AsyncMock(return_value=pdf_bytes)

        with patch("app.queue.enqueue_parse_job", new_callable=AsyncMock):
            res = await upload_file(
                db=db_session,
                admin="testadmin",
                _=MagicMock(),
                file=mock_file,
                mode="faithful_transcription",
            )
            assert "paper_id" in res
            assert "slug" in res


class TestPublicPageTitleXSSEscaping:
    """测试公开复习页面 Title 字段的 XSS 防护。"""

    def test_get_public_page_escapes_title(self, unauth_client, db_session):
        from app.database import Base
        from app.models import Paper, PublicationVersion

        Base.metadata.create_all(bind=db_session.get_bind())

        xss_title = "Test Paper </title><script>alert('xss')</script>"
        paper = Paper(
            title=xss_title,
            slug="xss-test-paper",
            mode="faithful_transcription",
        )
        db_session.add(paper)
        db_session.commit()

        pub = PublicationVersion(
            paper_id=paper.id,
            version=1,
            compiled_html="<div>Test Content</div>",
            compiled_css="body { color: red; }",
            content_hash="fakehash",
            published_by="testadmin",
        )
        db_session.add(pub)
        db_session.commit()

        paper.current_publication_id = pub.id
        db_session.commit()

        res = unauth_client.get(f"/api/public/papers/{paper.slug}/page")
        assert res.status_code == 200
        # 验证包含转义后的 HTML 实体，而不包含未转义的 </title><script> 标签
        assert "&lt;/title&gt;&lt;script&gt;" in res.text
        assert "</title><script>" not in res.text


class TestAssetFileNotFoundGracefulDegradation:
    """测试资产文件物理丢失时的优雅降级（404 而非 500）。"""

    def test_missing_physical_asset_returns_404(self, unauth_client, test_client, db_session):
        from app.database import Base
        from app.models import Asset

        Base.metadata.create_all(bind=db_session.get_bind())

        # 创建一条数据库纪录，但底层不存在真正的物理文件
        asset = Asset(
            paper_id=None,
            storage_key="non_existent_path/fake_file.png",
            media_type="image/png",
            is_public=True,
        )
        db_session.add(asset)
        db_session.commit()

        # 1. 验证公开访问接口捕获 FileNotFoundError 优雅降级返回 404（非 500）
        res_public = unauth_client.get(f"/api/assets/{asset.id}/public")
        assert res_public.status_code == 404
        assert "媒体文件未找到" in res_public.json()["detail"]

        # 2. 验证管理员私有访问接口捕获 FileNotFoundError 优雅降级返回 404（非 500）
        res_admin = test_client.get(f"/api/assets/{asset.id}")
        assert res_admin.status_code == 404
        assert "媒体文件未找到" in res_admin.json()["detail"]


class TestPublicationRealtimeGuard:
    """测试发布接口的实时结构校验关卡。"""

    @pytest.mark.asyncio
    async def test_publish_rejects_invalid_document_realtime(self, db_session):
        from fastapi import HTTPException
        from app.database import Base
        from app.models import Paper, PaperDraft
        from app.api.publications import publish
        from app.schemas import PublishIn

        Base.metadata.create_all(bind=db_session.get_bind())

        paper = Paper(title="Publish Guard Test", slug="pub-guard-test", mode="faithful_transcription")
        db_session.add(paper)
        db_session.commit()

        # 包含引用的题目在 questions 列表中缺失的非法草稿
        invalid_doc = {
            "title": "Publish Guard Test",
            "sections": [{"id": "s1", "title": "Sec 1", "question_ids": ["missing_q"]}],
            "questions": [],
        }

        draft = PaperDraft(
            paper_id=paper.id,
            version=1,
            document=invalid_doc,
            presentation_html="<p>Test</p>",
            theme_css="",
            is_valid=True,  # 静态标记即便为 True，发布实时校验依然拦截
        )
        db_session.add(draft)
        db_session.commit()

        body = PublishIn(draft_id=draft.id)
        with pytest.raises(HTTPException) as exc_info:
            await publish(body=body, db=db_session, admin="testadmin", _=MagicMock())

        assert exc_info.value.status_code == 400
        assert "草稿未通过结构校验" in str(exc_info.value.detail)


class TestAnthropicAdapterImageURLSupport:
    """测试 Anthropic 协议适配器多模态 HTTP/HTTPS URL 完整转换。"""

    def test_anthropic_messages_supports_http_image_urls(self):
        from app.adapters import OpenAICompatibleAdapter

        adapter = OpenAICompatibleAdapter(
            base_url="https://api.anthropic.com/v1",
            api_key="test-key",
            model="claude-3-5-sonnet-20241022",
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "分析试卷图片"},
                    {"type": "image_url", "image_url": {"url": "https://example.com/paper.png"}},
                ],
            }
        ]

        sys_prompt, converted = adapter._to_anthropic_messages(messages, response_format_json=False)
        assert len(converted) == 1
        content_items = converted[0]["content"]
        assert len(content_items) == 2
        assert content_items[1]["type"] == "image"
        assert content_items[1]["source"]["type"] == "url"
        assert content_items[1]["source"]["url"] == "https://example.com/paper.png"


class TestMiddlewareExceptionLogging:
    """测试 HTTP 请求中间件对未捕获异常的记录与追踪。"""

    @pytest.mark.asyncio
    async def test_middleware_handles_unhandled_exception(self):
        from unittest.mock import AsyncMock, patch
        from app.main import request_logging_middleware

        mock_request = MagicMock()
        mock_request.headers.get.return_value = "req-12345"
        mock_request.method = "GET"
        mock_request.url.path = "/api/test-crash"

        async def broken_call_next(req):
            raise RuntimeError("Database connection crashed")

        with patch("app.main.logger.error") as mock_log_error:
            with pytest.raises(RuntimeError) as exc_info:
                await request_logging_middleware(mock_request, broken_call_next)

            assert "Database connection crashed" in str(exc_info.value)
            mock_log_error.assert_called_once()
            call_kwargs = mock_log_error.call_args[1]
            assert call_kwargs["request_id"] == "req-12345"
            assert call_kwargs["error"] == "Database connection crashed"

