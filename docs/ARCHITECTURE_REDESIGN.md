# TPaper 架构重设计方案

**日期：** 2026-07-09  
**状态：** 设计阶段，待用户确认后实施  
**原则：** 第一性原理 + Map-Reduce 分治 + 生产级可靠性

---

## 1. 问题重述（第一性原理）

**本质任务**：将一份 PDF/DOCX/图片 → 可交互的在线考试网页。

**不可约简的四个阶段**：

| 阶段 | 输入 | 输出 | 资源特征 |
|------|------|------|----------|
| **预处理** | 原始文件 | 页面级文本+图片 | CPU 密集（OCR） |
| **提取** | 页面内容 | 结构化题目 JSON | LLM API 密集 |
| **文档生成** | 提取结果 | PaperDocument JSON | LLM API 密集（大上下文） |
| **渲染+净化** | PaperDocument | HTML + CSS | CPU 密集（确定性） |

**核心矛盾**：大文档（58页）的处理需要**分治**（Map-Reduce），但当前架构是**单体串行**。

---

## 2. 当前架构问题诊断

### 2.1 架构图（现状）

```
┌─────────────────────────────────────────────────────┐
│                    API Process                       │
│  ┌─────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ FastAPI  │  │ 处理轮询  │  │  processing.py   │  │
│  │ Routes   │→ │ (3s间隔) │→ │  (单体 async)    │  │
│  └─────────┘  └──────────┘  └───────────────────┘  │
│                      │                               │
│              ┌───────┴───────┐                       │
│              │   PostgreSQL   │                       │
│              └───────────────┘                       │
└─────────────────────────────────────────────────────┘
```

### 2.2 问题清单

| # | 问题 | 根因 | 严重度 |
|---|------|------|--------|
| 1 | 大文档超时 | 单次 LLM 调用处理全部内容，无分治 | **致命** |
| 2 | 提取串行 |58页逐页调用模型，无并行 | **严重** |
| 3 | 无真实任务队列 | Redis 不可用时回退到 DB 轮询 | **严重** |
| 4 | 无实时进度 | 前端5秒轮询，用户体验差 | 中等 |
| 5 | Worker 未集成 | docker-compose 未启动 worker | 中等 |
| 6 | 模型调用无重试 | 失败直接 fallback 到本地兜底 | 中等 |
| 7 | 无速率限制 | 可能压垮模型 API | 低 |
| 8 | 处理和 API 耦合 | 同一进程，计算密集操作影响 API 响应 | 中等 |

---

## 3. 目标架构设计

### 3.1 架构图（目标）

```
                         ┌──────────────┐
                         │   Nginx      │
                         │  :8084       │
                         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ┌─────┴─────┐          ┌──────┴──────┐
              │   Web     │          │    API      │
              │  (Next.js)│          │  (FastAPI)  │
              │   :3000   │          │   :8000     │
              └───────────┘          └──────┬──────┘
                                            │
                              ┌─────────────┼─────────────┐
                              │             │             │
                        ┌─────┴────┐  ┌─────┴────┐  ┌─────┴────┐
                        │ PostgreSQL│  │  Redis   │  │ MinIO/   │
                        │  :5432   │  │  :6379   │  │ Local FS │
                        └──────────┘  └─────┬────┘  └──────────┘
                                            │
                                     ┌──────┴──────┐
                                     │   Celery    │
                                     │   Workers   │
                                     │  (≥1 实例)  │
                                     └─────────────┘
```

### 3.2 核心原则

1. **API 与 Worker 物理分离** — API 只处理 HTTP 请求和认证，不做任何文件处理
2. **Map-Reduce 分治** — 大文档分块处理，合并结果
3. **可靠任务投递** — Celery + Redis，失败自动重试
4. **实时进度推送** — SSE 替代轮询
5. **模块化 Pipeline** — 每个阶段独立、可重试、可跳过

---

## 4. Pipeline 详细设计

### 4.1 数据流

```
上传文件
  │
  ▼
[API] POST /api/uploads/file
  │  → 存储文件到 Storage
  │  → 创建 Paper(status=queued) + SourceFile
  │  → 创建 ProcessingJob(status=queued)
  │  → 发送 Celery 任务 process_paper(paper_id)
  │
  ▼
[Worker] process_paper  ──────────────────────────────────────
  │                                                              │
  │  ┌─────────────────────────────────────────────────────┐    │
  │  │ 阶段 1: 预处理 (Preprocess)                         │    │
  │  │  PDF → 检测文本量 → 不足则 Tesseract OCR            │    │
  │  │  DOCX → python-docx 提取                            │    │
  │  │  图片 → base64 编码                                  │    │
  │  │  输出: list[PageContent]                             │    │
  │  └─────────────────────┬───────────────────────────────┘    │
  │                        │                                     │
  │  ┌─────────────────────▼───────────────────────────────┐    │
  │  │ 阶段 2: 提取 (Extract) — Map-Reduce                 │    │
  │  │  MAP: 并行处理每页/每块                              │    │
  │  │    chunk_1 → extract_chunk() → items_1              │    │
  │  │    chunk_2 → extract_chunk() → items_2              │    │
  │  │    ...                                               │    │
  │  │    chunk_N → extract_chunk() → items_N              │    │
  │  │  REDUCE: 合并所有 items                              │    │
  │  │  输出: list[ExtractedItem]                           │    │
  │  └─────────────────────┬───────────────────────────────┘    │
  │                        │                                     │
  │  ┌─────────────────────▼───────────────────────────────┐    │
  │  │ 阶段 3: 文档生成 (Generate Document) — Map-Reduce   │    │
  │  │  MAP: 分批(10页)生成子文档                           │    │
  │  │    batch_1 → generate_doc() → doc_1                 │    │
  │  │    batch_2 → generate_doc() → doc_2                 │    │
  │  │    ...                                               │    │
  │  │  REDUCE: _merge_documents() 合并                    │    │
  │  │  输出: PaperDocument JSON                            │    │
  │  └─────────────────────┬───────────────────────────────┘    │
  │                        │                                     │
  │  ┌─────────────────────▼───────────────────────────────┐    │
  │  │ 阶段 4: 渲染 (Render)                               │    │
  │  │  PaperDocument → render_paper() → HTML + CSS        │    │
  │  │  (确定性，无 LLM 调用)                               │    │
  │  └─────────────────────┬───────────────────────────────┘    │
  │                        │                                     │
  │  ┌─────────────────────▼───────────────────────────────┐    │
  │  │ 阶段 5: 净化 (Sanitize)                             │    │
  │  │  bleach HTML + tinycss2 CSS + content_hash          │    │
  │  │  (确定性，无 LLM 调用)                               │    │
  │  └─────────────────────┬───────────────────────────────┘    │
  │                        │                                     │
  │  → 创建 PaperDraft(is_valid=True)                          │
  │  → 更新 Paper(status=pending_review)                       │
  │  → 发送 SSE 通知前端                                        │
  ──────────────────────────────────────────────────────────────
```

### 4.2 分块策略（Map-Reduce）

#### 预处理分块
- **单位**：每页独立处理
- **并行度**：ThreadPoolExecutor(8)，OCR 是 CPU 密集
- **容错**：单页 OCR 失败不影响其他页

#### 提取分块（核心改进）
- **单位**：每5页为一个 chunk
- **并行度**：Celery 并发=4，同时处理4个 chunk
- **容错**：单 chunk 失败重试3次，跳过失败 chunk 继续
- **示例**（58页）：
  ```
  chunk_1: pages 1-5   → extract → items_1
  chunk_2: pages 6-10  → extract → items_2
  ...
  chunk_12: pages 56-58 → extract → items_12
  ```

#### 文档生成分块
- **单位**：每10个提取结果为一个 batch
- **并行度**：串行（有依赖：后续 batch 需要前面的上下文）
- **合并**：`_merge_documents()` 重新编号题目

### 4.3 进度追踪

```python
# ProcessingJob 更新进度
job.stage = "preprocessing"     # 阶段
job.current_page = 12           # 当前页
job.total_pages = 58            # 总页数
job.failed_pages = [20]         # 失败页
job.call_summary = {            # 模型调用统计
    "extract_calls": 12,
    "extract_tokens": 45000,
    "generate_calls": 6,
    "generate_tokens": 120000,
}
```

**SSE 推送**：
```
GET /api/jobs/{id}/stream  →  text/event-stream

event: progress
data: {"stage":"extracting","current":12,"total":58,"percent":20}

event: stage_complete
data: {"stage":"preprocessing","duration_ms":45000}

event: complete
data: {"draft_id":42,"question_count":85}

event: error
data: {"stage":"extracting","message":"chunk 3 failed after 3 retries"}
```

---

## 5. 模块划分

### 5.1 Backend 目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI 入口（只管 HTTP）
│   ├── config.py                # 配置（不变）
│   ├── database.py              # DB 连接（不变）
│   ├── schemas.py               # Pydantic 模型（不变）
│   ├── deps.py                  # 依赖注入（不变）
│   │
│   ├── models/                  # ORM 模型（不变）
│   │   └── __init__.py
│   │
│   ├── api/                     # API 路由（简化，移除处理逻辑）
│   │   ├── auth.py
│   │   ├── model_profiles.py
│   │   ├── uploads.py           # 只管上传 + 入队
│   │   ├── papers.py
│   │   ├── jobs.py              # 增加 SSE stream 端点
│   │   ├── drafts.py
│   │   ├── publications.py
│   │   ├── public.py
│   │   └── assets.py
│   │
│   ├── security/                # 安全模块（不变）
│   │   └── __init__.py
│   │
│   ├── storage/                 # 存储抽象（不变）
│   │   └── __init__.py
│   │
│   ├── adapters/                # 模型适配器（增加重试+退避）
│   │   └── __init__.py
│   │
│   └── presentation.py          # HTML/CSS 渲染（不变）
│
├── worker/                      # ★ 独立 Worker 包
│   ├── __init__.py
│   ├── celery_app.py            # Celery 实例配置
│   ├── tasks.py                 # Celery 任务定义
│   ├── pipeline/                # ★ 处理流水线（从 processing.py 拆分）
│   │   ├── __init__.py
│   │   ├── preprocess.py        # 预处理：PDF/DOCX/图片
│   │   ├── extract.py           # 提取：LLM 调用 + Map-Reduce
│   │   ├── generate.py          # 文档生成：分批 + 合并
│   │   ├── render.py            # 渲染：HTML/CSS（调用 presentation.py）
│   │   └── sanitize.py          # 净化：HTML/CSS 清理
│   │
│   └── prompts/                 # Prompt 模板（从 adapters 拆出）
│       ├── __init__.py
│       ├── extraction.py        # 提取 prompt
│       └── document.py          # 文档生成 prompt
│
├── pyproject.toml
└── alembic/
```

### 5.2 模块职责

| 模块 | 文件 | 职责 | 依赖 |
|------|------|------|------|
| **API 层** | `api/*.py` | HTTP 路由、认证、输入验证 | DB, Storage |
| **任务调度** | `celery_app.py` | Celery 配置、任务注册 | Redis |
| **任务定义** | `tasks.py` | Celery 任务入口、错误处理 | pipeline/* |
| **预处理** | `preprocess.py` | 文件解析、OCR | pypdf, pymupdf, pytesseract |
| **提取** | `extract.py` | Map-Reduce LLM 调用 | adapters, prompts |
| **文档生成** | `generate.py` | 分批生成 + 合并 | adapters, prompts |
| **渲染** | `render.py` | HTML/CSS 模板渲染 | presentation.py |
| **净化** | `sanitize.py` | HTML/CSS 安全清理 | bleach, tinycss2 |
| **适配器** | `adapters/__init__.py` | LLM API 调用 + 重试 | httpx |
| **Prompt** | `prompts/*.py` | 提取/生成 prompt 模板 | — |

---

## 6. Celery 任务设计

### 6.1 任务定义

```python
# worker/tasks.py

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_paper(self, paper_id: int):
    """主处理任务 — 编排整个 pipeline。"""
    ...

@celery_app.task(bind=True, max_retries=3)
def extract_chunk(self, paper_id: int, chunk_pages: list[dict]):
    """提取单个 chunk — 可并行。"""
    ...

@celery_app.task(bind=True, max_retries=3)
def generate_document_batch(self, paper_id: int, extracted_batch: list[dict]):
    """文档生成单个 batch — 串行。"""
    ...
```

### 6.2 任务流（Canvas）

```python
# 主任务编排
from celery import chain, chord, group

# 方案 A: 简单链（适合小文档）
workflow = chain(
    preprocess.s(paper_id),
    extract_all.s(paper_id),
    generate_document.s(paper_id),
    render_and_sanitize.s(paper_id),
    finalize.s(paper_id),
)

# 方案 B: Map-Reduce（适合大文档）
def process_paper_large(paper_id):
    """大文档处理：提取阶段并行，文档生成串行。"""
    # 1. 预处理
    preprocessed = preprocess(paper_id)

    # 2. 分块提取（并行）
    chunks = split_into_chunks(preprocessed, chunk_size=5)
    extract_group = group(
        extract_chunk.s(paper_id, chunk) for chunk in chunks
    )
    # chord: 并行提取完成后，调用合并回调
    extract_and_merge = chord(extract_group)(merge_extracted.s(paper_id))

    # 3. 文档生成（串行，等提取完成）
    # 4. 渲染 + 净化
    # 5. 完成
```

### 6.3 重试策略

| 阶段 | 最大重试 | 退避策略 | 失败处理 |
|------|---------|---------|---------|
| 预处理 | 1 | 立即重试 | 标记 failed，终止 |
| 提取 chunk | 3 | 指数退避 60s/120s/240s | 跳过该 chunk，继续 |
| 文档生成 | 2 | 指数退避 120s/240s | 用已成功的 chunk 结果 |
| 渲染 | 0 | 不重试 | 用 fallback 模板 |
| 净化 | 0 | 不重试 | 用原始内容 |

---

## 7. 实时进度（SSE）

### 7.1 API 端点

```python
# api/jobs.py

@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: int):
    """SSE 实时推送任务进度。"""
    async def event_generator():
        while True:
            job = db.get(ProcessingJob, job_id)
            if not job:
                break
            yield f"data: {json.dumps({...})}\n\n"
            if job.status in ("succeeded", "failed"):
                break
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

### 7.2 前端消费

```typescript
// web/src/lib/api.ts
export function streamJobProgress(jobId: number, onEvent: (data: any) => void) {
  const es = new EventSource(`/api/jobs/${jobId}/stream`);
  es.onmessage = (e) => onEvent(JSON.parse(e.data));
  es.onerror = () => es.close();
  return () => es.close();
}
```

---

## 8. 部署拓扑

### 8.1 docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: tpaper
      POSTGRES_USER: tpaper
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tpaper"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://tpaper:${DB_PASSWORD}@postgres:5432/tpaper
      REDIS_URL: redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    environment:
      DATABASE_URL: postgresql+psycopg://tpaper:${DB_PASSWORD}@postgres:5432/tpaper
      REDIS_URL: redis://redis:6379/0
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 1  # 可水平扩展

  web:
    build:
      context: .
      dockerfile: docker/Dockerfile.web
    ports:
      - "3000:3000"
    environment:
      API_INTERNAL_URL: http://api:8000
    depends_on:
      api:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
```

### 8.2 Dockerfile.worker

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev tesseract-ocr \
    tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/ /app/backend/
COPY worker/ /app/worker/
RUN cd /app/backend && pip install --no-cache-dir -e .

WORKDIR /app
CMD ["celery", "-A", "worker.celery_app:celery_app", "worker", \
     "--loglevel=info", "--concurrency=4", "-Q", "tpaper"]
```

---

## 9. 适配器改进

### 9.1 增加重试+退避

```python
# adapters/__init__.py

class OpenAICompatibleAdapter:
    async def chat(self, messages, ..., max_retries=3):
        for attempt in range(max_retries):
            try:
                result = await self._call_api(messages, ...)
                if result.success:
                    return result
                # 可重试的错误
                if self._is_retryable(result.error):
                    wait = min(60 * (2 ** attempt), 300)
                    logger.warning(f"API 调用失败，{wait}s 后重试: {result.error}")
                    await asyncio.sleep(wait)
                    continue
                return result  # 不可重试，直接返回
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = min(60 * (2 ** attempt), 300)
                    await asyncio.sleep(wait)
                    continue
                return ModelCallResult(content="", success=False, error=str(e))
        return ModelCallResult(content="", success=False, error="Max retries exceeded")

    def _is_retryable(self, error: str) -> bool:
        """判断错误是否可重试。"""
        retryable = ["timeout", "529", "503", "429", "rate_limit", "overloaded"]
        return any(r in error.lower() for r in retryable)
```

### 9.2 增加速率限制

```python
# adapters/__init__.py

import asyncio
from collections import deque

class RateLimiter:
    """令牌桶速率限制器。"""
    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.calls = deque()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            while self.calls and self.calls[0] <= now - self.period:
                self.calls.popleft()
            if len(self.calls) >= self.max_calls:
                wait = self.calls[0] + self.period - now
                await asyncio.sleep(wait)
            self.calls.append(time.monotonic())

# 使用
rate_limiter = RateLimiter(max_calls=10, period=60)  # 10次/分钟

async def chat(self, messages, ...):
    await rate_limiter.acquire()
    ...
```

---

## 10. 迁移计划

### Phase 1: 最小可用（1-2天）
1. 将 `processing.py` 拆分为 `worker/pipeline/` 模块
2. 创建 `worker/celery_app.py` + `worker/tasks.py`
3. 更新 `docker-compose.yml` 添加 redis + worker 服务
4. API 中保留 in-process fallback（Redis 不可用时）
5. 验证：上传 PDF → Celery 处理 → 生成草稿

### Phase 2: 大文档支持（1天）
1. 实现 `extract.py` 的 Map-Reduce 分块
2. 实现 `generate.py` 的分批生成
3. 增加适配器重试+退避
4. 验证：上传58页扫描 PDF → 分块处理 → 合并 → 生成草稿

### Phase 3: 实时进度（1天）
1. 添加 SSE stream 端点
2. 前端改用 SSE 替代轮询
3. ProcessingJob 增加详细进度字段
4. 验证：上传文件 → 前端实时显示进度

### Phase 4: 生产加固（可选）
1. 增加 Worker 水平扩展（replicas: 2+）
2. 增加速率限制
3. 增加监控指标（Prometheus）
4. 增加日志聚合

---

## 11. 与当前代码的差异

| 文件 | 当前 | 目标 |
|------|------|------|
| `backend/app/processing.py` | 500+行单体 | **删除**，拆分到 worker/pipeline/* |
| `backend/app/main.py` | 启动处理轮询 | 移除轮询，保留 Celery beat（可选） |
| `backend/app/adapters/__init__.py` | 无重试 | 增加重试+退避+速率限制 |
| `backend/app/api/jobs.py` | 基础 CRUD | 增加 SSE stream 端点 |
| `worker/main.py` | 480行单体 | **重构**为 tasks.py + pipeline/* |
| `docker-compose.yml` | 3 服务 | 4 服务（+redis, +worker） |
| `docker/Dockerfile.worker` | 存在但未使用 | 实际启动 Celery worker |

---

## 12. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| Celery 配置复杂 | 中 | 部署延迟 | 保留 in-process fallback |
| Redis 故障 | 低 | 任务丢失 | 持久化 + 重试 |
| 模型 API 限流 | 高 | 提取变慢 | 速率限制 + 指数退避 |
| 大文档分块丢失上下文 | 中 | 题目不完整 | chunk 重叠 + 合并时去重 |
| Worker 内存溢出 | 低 | 处理失败 | 并发限制 + 超时 |

---

## 13. 验收标准

1. ✅ 58页扫描 PDF 能在10分钟内完成处理（当前：超时失败）
2. ✅ 处理进度实时显示在前端（当前：5秒轮询）
3. ✅ 单页提取失败不影响整体（当前：直接 fallback）
4. ✅ Redis 不可用时仍能处理（保留 fallback）
5. ✅ Worker 可水平扩展（replicas: N）
6. ✅ 所有现有功能不受影响（上传、草稿编辑、发布、公开访问）
