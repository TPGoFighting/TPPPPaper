# 变更日志 — 2026-07-09

## 概述

本次部署完成了 TPaper 项目的**架构重设计**，将原本的单体 in-process 轮询架构升级为 **Celery 分布式任务队列 + 模块化流水线**，并修复了多个影响生产可用性的关键问题。

---

## 一、架构重设计（Celery Worker + 模块化流水线）

### 变更背景

原先架构中，PDF 解析任务在 API 进程内以 `asyncio.create_task()` 方式执行，存在以下问题：
- API 进程重启或崩溃会导致正在处理的任务丢失
- 任务处理与请求处理共享资源，互相影响
- 无法水平扩展处理能力

### 新架构

```
用户请求 → Nginx → Web (Next.js) → API (FastAPI) → Redis (Broker) → Worker (Celery)
                                    ↑                                    ↓
                                    └────── 结果回写 DB ←───── 5 阶段流水线
```

**5 个 Docker 服务：**
| 服务 | 说明 |
|------|------|
| `tpaper-postgres-1` | PostgreSQL 数据库 |
| `tpaper-redis-1` | Redis（Celery broker + result backend）|
| `tpaper-api-1` | FastAPI API 服务 |
| `tpaper-worker-1` | Celery Worker（4 并发 prefork）|
| `tpaper-web-1` | Next.js 前端 |

### 新增文件

| 文件 | 说明 |
|------|------|
| `worker/celery_app.py` | Celery 实例配置，Redis broker，`tpaper` 队列 |
| `worker/tasks.py` | Celery 任务定义，`process_paper(paper_id, source_file_id)` |
| `worker/pipeline/preprocess.py` | PDF/DOCX/图片预处理 + 并行 OCR |
| `worker/pipeline/extract.py` | 并行 LLM 提取（Semaphore(4) 并发控制）|
| `worker/pipeline/generate.py` | 分块文档生成（chunk_size=10）+ 合并 |
| `worker/pipeline/render.py` | HTML/CSS 渲染 |
| `worker/pipeline/sanitize.py` | HTML/CSS 净化 + 校验 |
| `worker/pyproject.toml` | Worker 依赖（celery, pymupdf, pytesseract 等）|

### 修改文件

| 文件 | 变更 |
|------|------|
| `backend/app/main.py` | 移除 in-process 轮询，Redis 可用时仅通过 Celery 分发任务 |
| `backend/app/queue.py` | 改用 `Celery.send_task()` 分发任务到 `tpaper` 队列 |
| `docker/Dockerfile.api` | 新增复制 `worker/` 包，API 可调用 Celery 分发 |
| `docker/Dockerfile.worker` | Celery worker 启动脚本 + tesseract-ocr + 中文语言包 |
| `docker-compose.yml` | 新增 `worker` 和 `redis` 服务 |

---

## 二、修复：Celery 任务队列路由错误

### 问题

`queue.py` 中 `_celery_send()` 创建的 Celery 客户端未指定队列名，任务被发送到默认的 `celery` 队列，而 Worker 只监听 `tpaper` 队列，导致**任务永远不会被执行**。

### 修复

```python
# backend/app/queue.py
def _celery_send(task_name: str, args: tuple) -> None:
    from celery import Celery
    app = Celery("tpaper-client", broker=settings.redis_url)
    app.send_task(task_name, args=args, queue="tpaper")  # ← 新增 queue 参数
```

### 验证

Worker 日志确认任务被正确接收并执行：
```
[2026-07-09 14:10:16] Task worker.tasks.process_paper[8bd321da] received
[2026-07-09 14:10:21] [Paper 6] 预处理...
[2026-07-09 14:10:25] 并行 OCR: 58 pages, workers=8
...
[2026-07-09 14:20:19] Task worker.tasks.process_paper[8bd321da] succeeded
```

---

## 三、修复：管理后台缺少认证守卫

### 问题

`web/src/app/admin/layout.tsx` 缺少登录验证，未登录用户可直接访问 `/admin` 页面。

### 修复

在 admin layout 中添加 session 检查，未登录时重定向到 `/login`。

---

## 四、增强：扫描件 PDF 支持

### 变更

- `preprocess_pdf()` 新增 PyMuPDF 渲染 + Tesseract OCR 支持
- 并行 OCR：`ThreadPoolExecutor(max_workers=8)` 加速扫描件处理
- Docker 镜像安装 `tesseract-ocr` + `tesseract-ocr-chi-sim` + `tesseract-ocr-chi-tra`

### 验证

58 页扫描件 PDF（现代管理科学试卷）OCR 处理耗时约 8 分钟，每个页面平均 8-10 秒。

---

## 五、增强：并行 LLM 提取 + 分块生成

### 变更

- `extract.py`：使用 `asyncio.Semaphore(4)` 控制并发，同时最多 4 个页面并行调用 LLM
- `generate.py`：当提取结果超过 10 题时自动分块，每块独立生成子文档，最后合并（`_merge_documents()`）
- 题目编号自动重排

---

## 六、增强：模型适配器重试 + 速率限制

### 变更（`backend/app/adapters/__init__.py`）

- `RateLimiter(10, 60)`：每分钟最多 10 次请求
- `_call_with_retry(max_retries=3)`：指数退避重试
- 支持的可重试错误：超时、429（速率限制）、529（过载）、503（服务不可用）

---

## 七、增强：SSE 实时进度推送

### 变更

- 新增 `GET /api/jobs/{job_id}/stream` 端点
- 返回 `text/event-stream` 格式的处理进度
- 前端可通过 EventSource 订阅

---

## 公网测试结果

| 测试项 | 结果 |
|--------|------|
| 首页 `https://tpaper.tpgofighting.top/` | ✅ 200 |
| 登录页 `/login` | ✅ 200 |
| 管理后台 `/admin` | ✅ 200 |
| API 登录 `POST /api/auth/login` | ✅ 成功 |
| 论文列表 `GET /api/papers` | ✅ 返回 5 篇论文 |
| 论文详情 `GET /api/papers/6` | ✅ pending_review |
| Celery 任务分发 | ✅ Worker 成功接收并处理 |
| 58 页扫描件 OCR | ✅ 全部完成 |
| LLM 提取 | ✅ 部分页面成功（超时后自动 fallback）|
| 文档生成 | ✅ 生成 12 题兜底草稿 |

---

## 提交记录

| Commit | 说明 |
|--------|------|
| `f9eea9e` | refactor: architecture redesign - Celery worker + modular pipeline + SSE |
| `dc7f866` | fix: send Celery tasks to 'tpaper' queue instead of default 'celery' queue |

---

## 已知问题

1. **58 页扫描件处理超时**：Celery soft time limit 为 600s，对于大文档不够。58 页 OCR 耗时约 8 分钟，剩余时间不足以完成所有页面的 LLM 提取。建议将 `task_soft_time_limit` 提升至 1800s（30 分钟）。

2. **LLM JSON 解析失败**：部分页面 LongCat 返回的 JSON 格式不正确，已被 fallback 逻辑处理。

3. **API 健康检查端点**：`/health` 仅在 API 容器内部可访问（端口 8000 未映射到宿主机），Nginx 仅代理 Web 容器的 3000 端口。
