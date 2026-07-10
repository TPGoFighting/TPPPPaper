"""Celery 任务 v2：优化后的处理流程。

升级点：
1. 使用预处理 v2（PyMuPDF + 多模态LLM）
2. 合并提取+生成为单阶段
3. 按内容边界分块 + 滑动窗口
4. 优化超时和错误处理
"""
import asyncio
import json
import logging
from datetime import datetime

from worker.celery_app import celery_app
from app.config import settings
from app.models import Job, Paper, Asset, db, SourceFile
from app.repositories import JobRepository, PaperRepository

logger = logging.getLogger("tpaper.worker.tasks_v2")


def _run_async(coro):
    """在 Celery worker 中运行异步代码。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _get_model_adapter():
    """获取模型适配器。"""
    from app.models import ModelProfile
    from app.adapters import ModelAdapter
    
    profile = db.session.query(ModelProfile).filter_by(is_active=True).first()
    if not profile:
        raise RuntimeError("没有可用的模型配置")
    
    return ModelAdapter(
        base_url=profile.api_base,
        api_key=profile.api_key,
        model=profile.model_id,
        temperature=profile.temperature,
        timeout=profile.timeout_seconds or 180,
    )


def _update_job(job_id: int, status: str, progress: int = None, message: str = None):
    """更新任务状态。"""
    try:
        with db.session.begin():
            job = db.session.get(Job, job_id)
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                if message:
                    job.message = message
                job.updated_at = datetime.utcnow()
    except Exception as e:
        logger.error(f"更新任务状态失败: {e}")


def _generate_local_fallback(document: dict) -> str:
    """本地生成 HTML（当文档生成超时时的兜底方案）。"""
    title = document.get("title", "试卷")
    questions = document.get("questions", [])
    
    html_parts = [f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .question {{ margin-bottom: 24px; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; }}
        .question-header {{ font-weight: bold; margin-bottom: 8px; }}
        .options {{ margin-left: 20px; }}
        .option {{ margin: 4px 0; }}
        .answer {{ color: #059669; margin-top: 8px; }}
        .explanation {{ color: #6b7280; margin-top: 4px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
"""]
    
    for i, q in enumerate(questions, 1):
        stem = q.get("stem", "")
        options = q.get("options", [])
        correct = q.get("correct_keys", [])
        answer = q.get("reference_answer", "")
        explanation = q.get("explanation", "")
        
        html_parts.append(f"""
    <div class="question" data-question="{i}">
        <div class="question-header">第 {i} 题</div>
        <div class="stem">{stem}</div>
        <div class="options">
""")
        for opt in options:
            key = opt.get("key", "")
            text = opt.get("text", "")
            html_parts.append(f'            <div class="option">{key}. {text}</div>\n')
        html_parts.append("""        </div>
""")
        if correct:
            html_parts.append(f'        <div class="answer">正确答案：{", ".join(correct)}</div>\n')
        if answer:
            html_parts.append(f'        <div class="explanation">参考答案：{answer}</div>\n')
        if explanation:
            html_parts.append(f'        <div class="explanation">解析：{explanation}</div>\n')
        html_parts.append("    </div>\n")
    
    html_parts.append("""
</body>
</html>""")
    
    return "".join(html_parts)


@celery_app.task(bind=True, max_retries=2, queue="tpaper")
def process_paper_v2(self, job_id: int):
    """处理试卷任务 v2：优化后的流程。"""
    from worker.pipeline.preprocess_v2 import (
        preprocess_v2, split_by_content_boundaries, split_with_overlap
    )
    from worker.pipeline.extract_v2 import extract_and_generate, extract_and_generate_with_vision
    
    logger.info(f"开始处理任务 {job_id}")
    _update_job(job_id, "processing", 0, "开始处理...")
    
    try:
        # 获取任务信息
        with db.session.begin():
            job = db.session.get(Job, job_id)
            if not job:
                logger.error(f"任务 {job_id} 不存在")
                return
            paper_id = job.paper_id
        
        # 获取试卷和源文件
        with db.session.begin():
            paper = db.session.get(Paper, paper_id)
            if not paper:
                logger.error(f"试卷 {paper_id} 不存在")
                _update_job(job_id, "failed", 0, "试卷不存在")
                return
            
            source_file = db.session.query(SourceFile).filter_by(
                storage_key=paper.source_file_key
            ).first()
            
            if not source_file:
                logger.error(f"源文件不存在: {paper.source_file_key}")
                _update_job(job_id, "failed", 0, "源文件不存在")
                return
        
        # Step 1: 预处理（PyMuPDF + 多模态LLM）
        _update_job(job_id, "processing", 10, "正在预处理文档...")
        preprocessed = _run_async(_preprocess_async(source_file))
        total_pages = preprocessed.get("page_count", 0)
        logger.info(f"预处理完成: {total_pages} 页")
        
        # Step 2: 按内容边界分块
        _update_job(job_id, "processing", 20, "正在分析文档结构...")
        pages = preprocessed.get("pages", [])
        
        # 使用内容边界分块（保留跨页上下文）
        chunks = split_with_overlap(pages, window_size=200)
        logger.info(f"分块完成: {len(chunks)} 块")
        
        # Step 3: 提取+生成（单阶段）
        _update_job(job_id, "processing", 30, "正在提取内容...")
        
        def progress_callback(message, progress):
            # 进度范围：30-80
            actual_progress = 30 + int(progress * 0.5)
            _update_job(job_id, "processing", min(actual_progress, 80), message)
        
        adapter = _get_model_adapter()
        
        # 检查是否需要多模态处理
        has_vision_pages = any(p.get("needs_multimodal") for p in pages)
        
        if has_vision_pages:
            document = _run_async(
                extract_and_generate_with_vision(adapter, chunks, progress_callback)
            )
        else:
            document = _run_async(
                extract_and_generate(adapter, chunks, progress_callback)
            )
        
        logger.info(f"提取完成: {len(document.get('questions', []))} 道题")
        
        # Step 4: 生成 HTML
        _update_job(job_id, "processing", 85, "正在生成 HTML...")
        
        try:
            from worker.pipeline.render import render_presentation
            presentation_html, theme_css = _run_async(
                render_presentation(adapter, document)
            )
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{document.get('title', '试卷')}</title>
    <style>{theme_css}</style>
</head>
<body>
{presentation_html}
</body>
</html>"""
        except Exception as e:
            logger.warning(f"HTML 渲染失败，使用本地生成: {e}")
            html_content = _generate_local_fallback(document)
        
        # Step 5: 保存结果
        _update_job(job_id, "processing", 90, "正在保存结果...")
        
        with db.session.begin():
            # 保存 HTML 文件
            asset = Asset(
                paper_id=paper_id,
                kind="html",
                filename=f"paper_{paper_id}.html",
                content_type="text/html",
                size_bytes=len(html_content.encode()),
            )
            db.session.add(asset)
            db.session.flush()
            
            storage = _get_storage()
            storage.put(settings.assets_namespace, asset.storage_key, html_content.encode())
            
            # 更新试卷状态
            paper.status = "ready"
            paper.updated_at = datetime.utcnow()
            
            # 更新任务状态
            _update_job(job_id, "completed", 100, f"处理完成: {len(document.get('questions', []))} 道题")
        
        logger.info(f"任务 {job_id} 完成")
        
    except Exception as e:
        logger.error(f"任务 {job_id} 失败: {e}", exc_info=True)
        _update_job(job_id, "failed", 0, f"处理失败: {str(e)[:200]}")
        raise


async def _preprocess_async(source_file):
    """异步预处理。"""
    from worker.pipeline.preprocess_v2 import preprocess_v2
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        lambda: preprocess_v2(source_file, use_vision=True)
    )
