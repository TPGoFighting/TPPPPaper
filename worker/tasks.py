"""TPaper Celery Tasks — 任务定义。

处理流水线：预处理 → 提取(Map-Reduce) → 文档生成 → 渲染 → 净化
"""
import asyncio
import json
import logging
import sys
import time

# 确保 backend app 包可导入
sys.path.insert(0, "/app/backend")

from worker.celery_app import celery_app
from worker.pipeline.preprocess import preprocess
from worker.pipeline.extract import extract_all, split_into_chunks
from worker.pipeline.generate import generate_document
from worker.pipeline.render import render_presentation
from worker.pipeline.sanitize import sanitize, ensure_publishable_document, build_fallback_document

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tpaper.tasks")


def _run_async(coro):
    """在 Celery worker 中运行异步代码。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_db():
    from app.database import SessionLocal
    return SessionLocal()


def _get_adapters(profile):
    from app.security import decrypt_secret
    from app.adapters import OpenAICompatibleAdapter

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
    return text_adapter, vision_adapter


def _update_job(db, job, **kwargs):
    """更新 ProcessingJob 字段并提交。"""
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()


CHUNK_SIZE = 15  # 每个分块处理的页数


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_paper(self, paper_id: int, source_file_id: int):
    """主处理任务 — 分块编排 pipeline。

    策略：预处理 → 分块提取 → 合并 → 生成文档 → 渲染 → 净化
    """
    from app.models import ModelProfile, Paper, PaperDraft, ProcessingJob, SourceFile

    db = _get_db()
    try:
        paper = db.get(Paper, paper_id)
        source = db.get(SourceFile, source_file_id)
        if not paper or not source:
            logger.error(f"Paper {paper_id} 或 SourceFile {source_file_id} 不存在")
            return

        # 获取活跃模型 Profile
        profile = db.query(ModelProfile).filter(ModelProfile.is_active.is_(True)).first()
        text_adapter = None
        vision_adapter = None
        if profile:
            text_adapter, vision_adapter = _get_adapters(profile)

        # 创建任务记录
        job = ProcessingJob(
            paper_id=paper_id,
            model_profile_id=profile.id if profile else None,
            job_type="parse",
            status="running",
            stage="preprocessing",
            idempotency_key=f"paper-{paper_id}-parse",
        )
        db.add(job)
        paper.status = "parsing"
        db.commit()

        start_time = time.monotonic()

        # ── 阶段 1: 预处理 ──
        logger.info(f"[Paper {paper_id}] 预处理...")
        preprocessed = _run_async(_preprocess(source))
        total_pages = preprocessed["page_count"]
        _update_job(db, job, total_pages=total_pages, stage="extracting")
        source.page_count = total_pages
        db.commit()

        if text_adapter:
            try:
                # ── 阶段 2: 分块提取 ──
                logger.info(f"[Paper {paper_id}] 分块提取 (共{total_pages}页, 每块{CHUNK_SIZE}页)...")
                extracted = _run_async(_extract_chunked(
                    text_adapter, preprocessed,
                    vision_adapter if profile and profile.supports_vision else None,
                    total_pages, job, db,
                ))
                _update_job(db, job, stage="generating_document", current_page=total_pages)

                # ── 阶段 3: 生成 PaperDocument ──
                logger.info(f"[Paper {paper_id}] 生成结构化文档...")
                paper.status = "modeling"
                db.commit()
                document = _run_async(generate_document(text_adapter, extracted, paper.mode))
            except Exception as model_error:
                logger.warning(f"[Paper {paper_id}] 模型生成失败，改用本地兜底: {model_error}")
                document = build_fallback_document(paper.title, preprocessed, paper.mode)
                job.error_code = type(model_error).__name__
                job.error_message = str(model_error)[:500]
        else:
            logger.warning(f"[Paper {paper_id}] 未配置模型 Profile，使用本地兜底")
            _update_job(db, job, stage="generating_document", current_page=total_pages)
            document = build_fallback_document(paper.title, preprocessed, paper.mode)

        # ── 阶段 4: 网页渲染 ──
        _update_job(db, job, stage="generating_presentation")
        logger.info(f"[Paper {paper_id}] 生成网页...")
        document = ensure_publishable_document(document)
        html, css = _run_async(render_presentation(text_adapter, document))

        # ── 阶段 5: 净化 + 校验 ──
        _update_job(db, job, stage="sanitizing")
        clean_html, clean_css, validation_errors, is_valid = sanitize(html, css, document)

        # 创建草稿
        last_draft = (
            db.query(PaperDraft)
            .filter(PaperDraft.paper_id == paper_id)
            .order_by(PaperDraft.version.desc())
            .first()
        )
        next_draft_version = (last_draft.version + 1) if last_draft else 1

        draft = PaperDraft(
            paper_id=paper_id,
            version=next_draft_version,
            document=document,
            presentation_html=clean_html,
            theme_css=clean_css,
            is_valid=is_valid,
            validation_result={"errors": validation_errors, "is_valid": is_valid},
        )
        db.add(draft)
        db.flush()

        elapsed = int((time.monotonic() - start_time) * 1000)
        paper.current_draft_id = draft.id
        paper.status = "pending_review"
        _update_job(db, job,
            status="succeeded",
            stage="done",
            call_summary={
                "model": profile.text_model if profile else "local_fallback",
                "pages_processed": total_pages,
                "elapsed_ms": elapsed,
            },
        )
        logger.info(f"[Paper {paper_id}] 处理完成，进入待审核 ({elapsed}ms)")

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


async def _preprocess(source):
    """异步包装预处理。"""
    return preprocess(source)


async def _extract_chunked(adapter, preprocessed, vision_adapter, total_pages, job, db):
    """分块提取，每块处理 CHUNK_SIZE 页。

    优势：
    1. 单块处理时间短，不会触发超时
    2. 每块完成后更新进度，前端可实时显示
    3. 单块失败不影响其他块
    """
    all_extracted = []
    chunks = []
    for i in range(0, total_pages, CHUNK_SIZE):
        chunks.append((i, min(i + CHUNK_SIZE, total_pages)))

    logger.info(f"分成 {len(chunks)} 块处理")

    for chunk_idx, (start_page, end_page) in enumerate(chunks):
        logger.info(f"处理块 {chunk_idx + 1}/{len(chunks)}: 页 {start_page + 1}-{end_page}")

        # 创建当前块的预处理数据（只包含当前块的页面）
        chunk_preprocessed = {
            "pages": preprocessed["pages"][start_page:end_page],
            "page_count": end_page - start_page,
            "images": preprocessed.get("images", [])[start_page:end_page] if preprocessed.get("images") else [],
        }

        # 提取当前块
        chunk_extracted = await extract_all(adapter, chunk_preprocessed, concurrency=4)

        # 重新编号题目
        offset = len(all_extracted)
        for item in chunk_extracted:
            if "number" in item:
                item["number"] += offset

        all_extracted.extend(chunk_extracted)

        # 更新进度
        _update_job(db, job, current_page=end_page)
        logger.info(f"块 {chunk_idx + 1} 完成，累计 {len(all_extracted)} 个提取项")

    return all_extracted
