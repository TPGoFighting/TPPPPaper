"""简化版 Celery Tasks — 使用新架构。

新架构：
1. PDF → 文本提取（快速，无 LLM）
2. 文本 → LLM → PaperDocument JSON（单次调用）
3. JSON → 模板渲染 → HTML
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
from worker.pipeline.simple_pipeline import simple_extract_and_generate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("tpaper.tasks_simple")


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
    return text_adapter


def _update_job(db, job, **kwargs):
    """更新 ProcessingJob 字段并提交。"""
    for k, v in kwargs.items():
        setattr(job, k, v)
    db.commit()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_paper_simple(self, paper_id: int, source_file_id: int):
    """简化版处理任务 — 单次 LLM 调用 + 模板渲染。

    新架构：
    1. 预处理：PDF → 文本
    2. 生成：文本 → LLM → PaperDocument JSON
    3. 渲染：JSON → HTML
    """
    from app.models import ModelProfile, Paper, PaperDraft, ProcessingJob, SourceFile
    from app.presentation import render_paper

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
        if profile:
            text_adapter = _get_adapters(profile)

        # 创建任务记录
        job = ProcessingJob(
            paper_id=paper_id,
            model_profile_id=profile.id if profile else None,
            job_type="parse",
            status="running",
            stage="preprocessing",
            idempotency_key=f"paper-{paper_id}-parse-simple",
        )
        db.add(job)
        paper.status = "parsing"
        db.commit()

        start_time = time.monotonic()

        # ── 阶段 1: 预处理 ──
        logger.info(f"[Paper {paper_id}] 预处理...")
        preprocessed = _run_async(_preprocess(source))
        total_pages = preprocessed["page_count"]
        _update_job(db, job, total_pages=total_pages, stage="generating")
        source.page_count = total_pages
        db.commit()

        if text_adapter:
            try:
                # ── 阶段 2: 单次 LLM 调用生成 PaperDocument ──
                logger.info(f"[Paper {paper_id}] 调用 LLM 生成 PaperDocument...")
                paper.status = "modeling"
                db.commit()
                document = _run_async(simple_extract_and_generate(
                    text_adapter, preprocessed, paper.mode
                ))
                _update_job(db, job, stage="rendering")
            except Exception as model_error:
                logger.warning(f"[Paper {paper_id}] 模型生成失败，改用本地兜底: {model_error}")
                document = _build_fallback_document(paper.title, preprocessed, paper.mode)
                job.error_code = type(model_error).__name__
                job.error_message = str(model_error)[:500]
        else:
            logger.warning(f"[Paper {paper_id}] 未配置模型 Profile，使用本地兜底")
            _update_job(db, job, stage="generating", current_page=total_pages)
            document = _build_fallback_document(paper.title, preprocessed, paper.mode)

        # ── 阶段 3: 模板渲染 ──
        logger.info(f"[Paper {paper_id}] 模板渲染 HTML...")
        html, css = render_paper(document)

        # ── 阶段 4: 保存草稿 ──
        _update_job(db, job, stage="saving")
        from worker.pipeline.sanitize import sanitize
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
                "questions_generated": len(document.get("questions", [])),
                "elapsed_ms": elapsed,
            },
        )
        logger.info(f"[Paper {paper_id}] 处理完成: {len(document.get('questions', []))} 题 ({elapsed}ms)")

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


def _build_fallback_document(title: str, preprocessed: dict, mode: str) -> dict:
    """构建本地兜底文档。"""
    pages = preprocessed.get("pages", [])
    questions = []

    for page in pages:
        text = page.get("text", "")
        if not text.strip():
            continue

        # 简单分割文本为题目
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if len(line) > 10:  # 忽略太短的行
                questions.append({
                    "id": f"q_{len(questions) + 1}",
                    "number": len(questions) + 1,
                    "type": "subjective",
                    "stem": line,
                    "score": 5,
                    "options": [],
                    "correct_keys": [],
                    "explanation": "这是系统在模型不可用时生成的兜底草稿，请人工审核。",
                    "needs_review": True,
                    "is_ai_generated": False,
                })

    return {
        "title": title,
        "language": "zh-CN",
        "metadata": {},
        "sections": [{
            "id": "default",
            "title": "",
            "question_ids": [q["id"] for q in questions],
        }],
        "questions": questions[:50],  # 最多50题
    }
