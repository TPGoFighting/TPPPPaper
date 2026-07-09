"""TPaper Worker：异步任务处理。

对应 SPEC 第 14 节 AI 处理流水线：
预处理 → 两阶段模型处理 → 网页生成 → 净化 → 校验恢复

从 Redis 队列消费任务，与 API 共享 app 包。
"""
import asyncio
import base64
import json
import logging
import sys
from datetime import datetime, timezone

# 复用 backend 的 app 包
sys.path.insert(0, "/app/backend")

from app.config import settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    ModelProfile, Paper, PaperDraft, ProcessingJob, SourceFile,
)
from app.security import decrypt_secret, sanitize_html, sanitize_css  # noqa: E402
from app.storage import get_storage  # noqa: E402
from app.adapters import (  # noqa: E402
    OpenAICompatibleAdapter, build_document_prompt, build_extraction_prompt,
    build_presentation_prompt,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tpaper.worker")


# ── 文档预处理（SPEC 14.1）──

def preprocess_pdf(content: bytes) -> dict:
    """PDF 预处理：提取文本、版面块和图片。

    MVP 简化实现：尝试用 pypdf 提取文本；文本不足时用 pymupdf 渲染页面为图片供多模态识别。
    """
    extracted_pages = []
    try:
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(content))
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            extracted_pages.append({
                "page": i + 1,
                "text": text,
                "needs_multimodal": len(text.strip()) < 50,  # 文本不足
            })
    except ImportError:
        logger.warning("pypdf 未安装，PDF 文本提取不可用")
        extracted_pages = [{"page": 1, "text": "", "needs_multimodal": True}]
    except Exception as e:
        logger.error(f"PDF 解析失败: {e}")
        extracted_pages = [{"page": 1, "text": "", "needs_multimodal": True, "error": str(e)}]

    # 对需要多模态的页面，并行 Tesseract OCR 提取文字
    needs_ocr = [p for p in extracted_pages if p.get("needs_multimodal") and not p.get("text", "").strip()]
    if needs_ocr:
        try:
            import fitz  # pymupdf
            import pytesseract
            from PIL import Image
            import io as _io
            from concurrent.futures import ThreadPoolExecutor, as_completed

            doc = fitz.open(stream=content, filetype="pdf")
            mat = fitz.Matrix(2, 2)

            def _ocr_page(page_info: dict) -> dict:
                page_idx = page_info["page"] - 1
                if page_idx < 0 or page_idx >= len(doc):
                    return page_info
                page = doc[page_idx]
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                img = Image.open(_io.BytesIO(img_bytes))
                ocr_text = pytesseract.image_to_string(img, lang="chi_sim+chi_tra+eng")
                if ocr_text.strip():
                    page_info["text"] = ocr_text.strip()
                    page_info["needs_multimodal"] = False
                page_info["image_b64"] = base64.b64encode(img_bytes).decode()
                page_info["mime"] = "image/png"
                return page_info

            max_workers = min(8, len(needs_ocr))
            logger.info(f"并行 OCR: {len(needs_ocr)} pages, workers={max_workers}")
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = {pool.submit(_ocr_page, p): p for p in needs_ocr}
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result.get("text"):
                            logger.info(f"第 {result['page']} 页 OCR 提取: {len(result['text'])} chars")
                        else:
                            logger.warning(f"第 {result['page']} 页 OCR 未提取到文字")
                    except Exception as e:
                        p = futures[future]
                        logger.error(f"第 {p['page']} 页 OCR 失败: {e}")

            doc.close()
        except ImportError as e:
            logger.warning(f"OCR 依赖未安装: {e}")
        except Exception as e:
            logger.error(f"PDF OCR 失败: {e}")

    return {"pages": extracted_pages, "page_count": len(extracted_pages)}


def preprocess_docx(content: bytes) -> dict:
    """DOCX 预处理：提取段落、表格和媒体。"""
    try:
        from docx import Document
        import io
        doc = Document(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return {
            "pages": [{"page": 1, "text": "\n".join(paragraphs), "needs_multimodal": False}],
            "page_count": 1,
        }
    except ImportError:
        logger.warning("python-docx 未安装")
        return {"pages": [{"page": 1, "text": "", "needs_multimodal": True}], "page_count": 1}
    except Exception as e:
        logger.error(f"DOCX 解析失败: {e}")
        return {"pages": [{"page": 1, "text": "", "needs_multimodal": True}], "page_count": 1}


def preprocess_image(content: bytes, mime: str) -> dict:
    """图片预处理：直接进入多模态识别。"""
    b64 = base64.b64encode(content).decode()
    return {
        "pages": [{"page": 1, "text": "", "needs_multimodal": True, "image_b64": b64, "mime": mime}],
        "page_count": 1,
    }


def preprocess(source_file: SourceFile) -> dict:
    """根据类型分发预处理。"""
    storage = get_storage()
    content = storage.get(settings.source_files_namespace, source_file.storage_key)

    if source_file.mime_type == "application/pdf":
        return preprocess_pdf(content)
    elif "wordprocessing" in source_file.mime_type:
        return preprocess_docx(content)
    elif source_file.mime_type.startswith("image/"):
        return preprocess_image(content, source_file.mime_type)
    else:
        return {"pages": [{"page": 1, "text": "", "needs_multimodal": True}], "page_count": 1}


# ── 两阶段模型处理（SPEC 14.2）──

async def stage1_extract(adapter: OpenAICompatibleAdapter, preprocessed: dict) -> list[dict]:
    """第一阶段：来源提取。"""
    extracted = []
    for page in preprocessed["pages"]:
        if page.get("needs_multimodal") and page.get("image_b64"):
            # 多模态提取
            prompt = f"提取第 {page['page']} 页的所有文字、题目结构和图表信息。返回 JSON。"
            result = await adapter.chat_with_image(
                prompt, page["image_b64"], page.get("mime", "image/png")
            )
        else:
            msgs = build_extraction_prompt(page.get("text", ""), page["page"])
            result = await adapter.chat(msgs, response_format_json=True)

        if result.success:
            try:
                extracted.append(json.loads(result.content))
            except json.JSONDecodeError:
                # 自动修复一次（SPEC 14.4）
                extracted.append({"page": page["page"], "text": result.content, "confidence": 0.5})
        else:
            logger.warning(f"第 {page['page']} 页提取失败: {result.error}")
            extracted.append({"page": page["page"], "text": "", "error": result.error})
    return extracted


async def stage2_generate_document(
    adapter: OpenAICompatibleAdapter, extracted: list[dict], mode: str
) -> dict:
    """第二阶段：生成 PaperDocument。"""
    msgs = build_document_prompt(extracted, mode)
    result = await adapter.chat(msgs, response_format_json=True)
    if not result.success:
        raise RuntimeError(f"文档生成失败: {result.error}")
    try:
        return json.loads(result.content)
    except json.JSONDecodeError as e:
        # SPEC 14.4: JSON 不合法时自动进行一次结构修复
        logger.warning(f"JSON 解析失败，尝试修复: {e}")
        # 简单修复：提取第一个 { 到最后一个 }
        content = result.content
        start = content.find("{")
        end = content.rfind("}")
        if start >= 0 and end > start:
            return json.loads(content[start : end + 1])
        raise


# ── 网页生成（SPEC 14.3）──

async def stage3_generate_presentation(adapter: OpenAICompatibleAdapter, document: dict) -> tuple[str, str]:
    """生成受控 HTML 与 CSS。"""
    msgs = build_presentation_prompt(json.dumps(document, ensure_ascii=False))
    result = await adapter.chat(msgs, response_format_json=True)
    if not result.success:
        raise RuntimeError(f"网页生成失败: {result.error}")
    try:
        data = json.loads(result.content)
        return data.get("presentation_html", ""), data.get("theme_css", "")
    except json.JSONDecodeError:
        return result.content, ""


# ── 主处理流程 ──

async def process_paper(paper_id: int, source_file_id: int) -> None:
    """处理一份资料的完整流水线。"""
    db = SessionLocal()
    try:
        paper = db.get(Paper, paper_id)
        source = db.get(SourceFile, source_file_id)
        if not paper or not source:
            logger.error(f"Paper {paper_id} 或 SourceFile {source_file_id} 不存在")
            return

        # 获取活跃模型 Profile
        profile = db.query(ModelProfile).filter(ModelProfile.is_active.is_(True)).first()
        if not profile:
            paper.status = "failed"
            db.commit()
            logger.error("无可用模型 Profile")
            return

        api_key = decrypt_secret(profile.encrypted_api_key) if profile.encrypted_api_key else ""
        text_adapter = OpenAICompatibleAdapter(
            base_url=profile.base_url,
            api_key=api_key,
            model=profile.text_model,
            timeout=profile.timeout_seconds,
            allow_private_network=profile.allow_private_network,
        )
        vision_adapter = OpenAICompatibleAdapter(
            base_url=profile.base_url,
            api_key=api_key,
            model=profile.multimodal_model,
            timeout=profile.timeout_seconds,
            allow_private_network=profile.allow_private_network,
        )

        # 创建任务记录
        job = ProcessingJob(
            paper_id=paper_id,
            model_profile_id=profile.id,
            job_type="parse",
            status="running",
            stage="preprocessing",
            idempotency_key=f"paper-{paper_id}-parse",
        )
        db.add(job)
        paper.status = "parsing"
        db.commit()

        # 阶段 1：预处理
        logger.info(f"[Paper {paper_id}] 预处理...")
        preprocessed = preprocess(source)
        job.total_pages = preprocessed["page_count"]
        job.stage = "extracting"
        source.page_count = preprocessed["page_count"]
        db.commit()

        # 阶段 2：来源提取
        logger.info(f"[Paper {paper_id}] 来源提取...")
        extracted = await stage1_extract(
            vision_adapter if profile.supports_vision else text_adapter, preprocessed
        )
        job.stage = "generating_document"
        job.current_page = preprocessed["page_count"]
        db.commit()

        # 阶段 3：生成 PaperDocument
        logger.info(f"[Paper {paper_id}] 生成结构化文档...")
        paper.status = "modeling"
        db.commit()
        document = await stage2_generate_document(text_adapter, extracted, paper.mode)

        # 阶段 4：网页生成
        job.stage = "generating_presentation"
        db.commit()
        logger.info(f"[Paper {paper_id}] 生成网页...")
        html, css = await stage3_generate_presentation(text_adapter, document)

        # 阶段 5：净化
        job.stage = "sanitizing"
        db.commit()
        clean_html, _ = sanitize_html(html)
        clean_css, _ = sanitize_css(css)

        # 创建草稿
        draft = PaperDraft(
            paper_id=paper_id,
            version=1,
            document=document,
            presentation_html=clean_html,
            theme_css=clean_css,
            is_valid=False,
            validation_result={"errors": [], "is_valid": False},
        )
        db.add(draft)
        db.flush()

        paper.current_draft_id = draft.id
        paper.status = "pending_review"
        job.status = "succeeded"
        job.stage = "done"
        job.call_summary = {
            "model": profile.text_model,
            "pages_processed": preprocessed["page_count"],
        }
        db.commit()
        logger.info(f"[Paper {paper_id}] 处理完成，进入待审核")

    except Exception as e:
        logger.exception(f"[Paper {paper_id}] 处理失败")
        paper = db.get(Paper, paper_id)
        if paper:
            paper.status = "failed"
        if 'job' in locals():
            job.status = "failed"
            job.error_code = type(e).__name__
            job.error_message = str(e)[:500]
        db.commit()
    finally:
        db.close()


# ── 队列消费循环 ──

async def consume_queue() -> None:
    """从 Redis 队列消费任务。"""
    import redis.asyncio as aioredis

    r = aioredis.from_url(settings.redis_url)
    logger.info(f"Worker 启动，监听队列 tpaper:jobs (concurrency={settings.worker_concurrency})")

    # 简单并发控制
    semaphore = asyncio.Semaphore(settings.worker_concurrency)

    async def handle_task(task_data: dict):
        async with semaphore:
            if task_data.get("type") == "parse":
                await process_paper(
                    paper_id=task_data["paper_id"],
                    source_file_id=task_data["source_file_id"],
                )
            elif task_data.get("type") == "retry":
                # 重试已有任务
                db = SessionLocal()
                try:
                    job = db.get(ProcessingJob, task_data["job_id"])
                    if job:
                        await process_paper(job.paper_id, job.paper.source_file_id)
                finally:
                    db.close()

    while True:
        try:
            # BLPOP 阻塞读取
            result = await r.blpop("tpaper:jobs", timeout=30)
            if result is None:
                continue
            _, raw = result
            task_data = json.loads(raw)
            logger.info(f"收到任务: {task_data}")
            asyncio.create_task(handle_task(task_data))
        except Exception as e:
            logger.error(f"队列消费异常: {e}")
            await asyncio.sleep(1)


async def cleanup_expired_sources() -> None:
    """清理到期源文件（SPEC 16：七天后由幂等清理任务删除）。"""
    db = SessionLocal()
    try:
        storage = get_storage()
        now = datetime.now(timezone.utc)
        expired = (
            db.query(SourceFile)
            .filter(SourceFile.expires_at < now)
            .filter(SourceFile.deleted_at.is_(None))
            .all()
        )
        for sf in expired:
            try:
                storage.delete(settings.source_files_namespace, sf.storage_key)
                sf.deleted_at = now
                logger.info(f"已删除到期源文件: {sf.original_filename}")
            except Exception as e:
                logger.error(f"清理失败: {e}")
        db.commit()
    finally:
        db.close()


async def main() -> None:
    """Worker 主循环：消费队列 + 定时清理。"""
    # 每 6 小时执行一次清理
    async def cleanup_loop():
        while True:
            await asyncio.sleep(6 * 3600)
            await cleanup_expired_sources()

    asyncio.create_task(cleanup_loop())
    await consume_queue()


if __name__ == "__main__":
    asyncio.run(main())
