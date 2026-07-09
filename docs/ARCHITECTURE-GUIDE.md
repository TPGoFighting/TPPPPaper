# 核心功能实现详解

> **在线体验**: https://tpaper.tpgofighting.top
> **管理员账号**: admin / rkiOqvL2WR7Uwlw0

---

## 目录

1. [认证系统](#1-认证系统)
2. [文件上传](#2-文件上传)
3. [Celery 异步处理](#3-celery-异步处理)
4. [AI 模型适配器](#4-ai-模型适配器)
5. [文档生成流水线](#5-文档生成流水线)
6. [SSE 实时进度](#6-sse-实时进度)
7. [前端路由](#7-前端路由)

---

## 1. 认证系统

### 架构
```
用户登录 → FastAPI 验证 → itsdangerous 签名 → httpOnly cookie → Session 中间件验证
```

### 实现细节

#### Session 管理 (`backend/app/deps.py`)
```python
# Session 签名器
session_signer = URLSafeTimedSerializer(settings.secret_key)

# 创建 session
def create_session_token(user_id: str) -> str:
    return session_signer.dumps({"user_id": user_id})

# 验证 session
def get_current_user(request: Request) -> dict | None:
    token = request.cookies.get("tpaper_session")
    if not token:
        return None
    try:
        data = session_signer.loads(token, max_age=43200)  # 12小时
        return {"user_id": data["user_id"]}
    except:
        return None
```

#### 登录 API (`backend/app/api/auth.py`)
```python
@router.post("/login")
async def login(request: Request, response: Response, db: Session = Depends(get_db)):
    body = await request.json()
    username = body.get("username", "")
    password = body.get("password", "")
    
    # 验证密码 (bcrypt)
    if not verify_password(password, settings.admin_password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # 创建 session token
    token = create_session_token(username)
    
    # 设置 httpOnly cookie
    response.set_cookie(
        "tpaper_session",
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=43200  # 12小时
    )
    return {"ok": True, "user": username}
```

#### CSRF 防护
```python
# 要求 X-Requested-With 头
def require_csrf(request: Request):
    if not request.headers.get("X-Requested-With"):
        raise HTTPException(status_code=403, detail="CSRF check failed")
```

---

## 2. 文件上传

### 架构
```
前端上传 → Nginx (50MB 限制) → FastAPI 验证 → 存储到本地文件系统 → 数据库记录
```

### 实现细节

#### 上传端点 (`backend/app/api/uploads.py`)
```python
@router.post("/init")
async def init_upload(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    filename = body.get("filename", "")
    mime_type = body.get("mime_type", "")
    size_bytes = body.get("size_bytes", 0)
    
    # 验证文件类型
    if not is_allowed_file(filename, mime_type):
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # 验证文件大小 (50MB)
    if size_bytes > settings.upload_max_size_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large")
    
    # 生成存储路径
    storage_key = generate_storage_key(filename)
    
    # 创建 SourceFile 记录
    source_file = SourceFile(
        storage_key=storage_key,
        original_filename=filename,
        mime_type=mime_type,
        size_bytes=size_bytes,
        sha256="",  # 上传后计算
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(source_file)
    db.commit()
    
    return {"upload_id": source_file.id, "storage_key": storage_key}
```

#### 文件类型验证
```python
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
ALLOWED_MIMES = {"application/pdf", "image/png", "image/jpeg"}

def is_allowed_file(filename: str, mime_type: str) -> bool:
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS and mime_type in ALLOWED_MIMES
```

---

## 3. Celery 异步处理

### 架构
```
API 调用 send_task() → Redis 队列 (tpaper) → Worker 进程 → 更新数据库进度
```

### 实现细节

#### Celery 配置 (`worker/celery_app.py`)
```python
from celery import Celery

app = Celery("tpaper")
app.config_from_object({
    "broker_url": "redis://redis:6379/0",
    "result_backend": "redis://redis:6379/0",
    "task_serializer": "json",
    "task_soft_time_limit": 600,   # 10分钟软限制
    "task_time_limit": 900,         # 15分钟硬限制
    "worker_max_memory_per_child": 512000,  # 512MB
    "worker_max_tasks_per_child": 100,
    "task_routes": {
        "worker.tasks.process_paper": {"queue": "tpaper"}
    }
})

# 启动 worker
# celery -A worker.celery_app worker -Q tpaper -c 4
```

#### 任务定义 (`worker/tasks.py`)
```python
@app.task(bind=True, name="worker.tasks.process_paper")
def process_paper(self, paper_id: int, source_file_id: int):
    """处理试卷的主任务"""
    # 获取数据库会话
    db = next(get_db())
    
    try:
        # 1. 更新状态为 running
        job = db.query(ProcessingJob).filter(ProcessingJob.paper_id == paper_id).first()
        job.status = "running"
        db.commit()
        
        # 2. 预处理 (PDF → 图片)
        images = preprocess(source_file)
        
        # 3. 并行 OCR
        ocr_results = parallel_ocr(images)
        
        # 4. 并行 LLM 提取
        extracted = parallel_extract(ocr_results)
        
        # 5. 生成文档
        document = generate_document(extracted)
        
        # 6. 渲染 HTML/CSS
        html, css = render(document)
        
        # 7. 清理
        clean_html, clean_css = sanitize(html, css)
        
        # 8. 保存结果
        draft = PaperDraft(
            paper_id=paper_id,
            document=document,
            presentation_html=clean_html,
            theme_css=clean_css
        )
        db.add(draft)
        
        # 9. 更新 Paper 状态
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        paper.status = "pending_review"
        paper.current_draft_id = draft.id
        
        # 10. 更新 Job 状态
        job.status = "succeeded"
        job.stage = "done"
        db.commit()
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
```

#### API 触发任务 (`backend/app/queue.py`)
```python
from celery import send_task

def dispatch_paper_processing(paper_id: int, source_file_id: int):
    """发送处理任务到 Celery"""
    result = send_task(
        "worker.tasks.process_paper",
        args=[paper_id, source_file_id],
        queue="tpaper"
    )
    return result.id
```

---

## 4. AI 模型适配器

### 架构
```
统一接口 → 协议检测 → 适配器选择 → HTTP 请求 → 重试/限流
```

### 实现细节

#### 适配器接口 (`backend/app/adapters/__init__.py`)
```python
class RateLimiter:
    """令牌桶限流器"""
    def __init__(self, max_tokens: int, refill_interval: float):
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.refill_interval = refill_interval
        self.last_refill = time.time()
    
    def acquire(self):
        self._refill()
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

class ModelAdapter:
    def __init__(self, profile: ModelProfile):
        self.profile = profile
        self.rate_limiter = RateLimiter(10, 60)  # 10 tokens/min
    
    def chat(self, messages: list, model: str = None) -> str:
        """统一调用接口"""
        # 限流检查
        if not self.rate_limiter.acquire():
            raise RateLimitError("Rate limit exceeded")
        
        # 重试逻辑
        for attempt in range(self.profile.max_retries):
            try:
                return self._call_api(messages, model)
            except (TimeoutError, RateLimitError) as e:
                if attempt < self.profile.max_retries - 1:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    raise
```

#### Anthropic 协议支持
```python
def _to_anthropic_messages(self, messages: list) -> list:
    """转换为 Anthropic 消息格式"""
    result = []
    for msg in messages:
        if msg["role"] == "system":
            result.append({"role": "user", "content": msg["content"]})
        else:
            content = []
            for part in msg["content"]:
                if isinstance(part, dict):
                    if part["type"] == "text":
                        content.append({"type": "text", "text": part["text"]})
                    elif part["type"] == "image":
                        content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": part["media_type"],
                                "data": part["data"]
                            }
                        })
                else:
                    content.append({"type": "text", "text": str(part)})
            result.append({"role": msg["role"], "content": content})
    return result
```

---

## 5. 文档生成流水线

### 架构
```
提取结果 → 分块 (每10题) → 并行生成 → 合并 → 重新编号
```

### 实现细节

#### 分块生成 (`worker/pipeline/generate.py`)
```python
def generate_document(extracted: list) -> dict:
    """分块生成文档"""
    CHUNK_SIZE = 10
    
    chunks = [extracted[i:i+CHUNK_SIZE] for i in range(0, len(extracted), CHUNK_SIZE)]
    
    documents = []
    for chunk in chunks:
        doc = _generate_chunk(chunk)
        documents.append(doc)
    
    # 合并文档
    return _merge_documents(documents)

def _merge_documents(documents: list) -> dict:
    """合并多个文档并重新编号"""
    all_questions = []
    for doc in documents:
        all_questions.extend(doc.get("questions", []))
    
    # 重新编号
    for i, q in enumerate(all_questions, 1):
        q["number"] = i
    
    return {
        "title": documents[0].get("title", "") if documents else "",
        "questions": all_questions,
        "metadata": documents[0].get("metadata", {}) if documents else {}
    }
```

---

## 6. SSE 实时进度

### 架构
```
前端 EventSource → FastAPI StreamingResponse → 数据库轮询 → 事件推送
```

### 实现细节

#### SSE 端点 (`backend/app/api/jobs.py`)
```python
@router.get("/{job_id}/stream")
async def stream_job_progress(
    job_id: int,
    db: Session = Depends(get_db),
    _user: dict = Depends(require_auth)
):
    """SSE 实时进度流"""
    async def event_generator():
        last_stage = None
        last_progress = -1
        
        while True:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if not job:
                yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
                break
            
            # 计算进度
            progress = _calculate_progress(job)
            stage = job.stage
            
            # 只在变化时推送
            if stage != last_stage or progress != last_progress:
                data = {
                    "job_id": job.id,
                    "status": job.status,
                    "stage": stage,
                    "progress": progress,
                    "current_page": job.current_page,
                    "total_pages": job.total_pages
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_stage = stage
                last_progress = progress
            
            # 完成或失败时结束
            if job.status in ("succeeded", "failed"):
                break
            
            await asyncio.sleep(1)  # 每秒轮询一次
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

---

## 7. 前端路由

### 架构
```
Next.js App Router → 页面组件 → API 客户端 → 后端 API
```

### 路由表

| 路径 | 组件 | 说明 |
|------|------|------|
| `/` | `app/page.tsx` | 首页 |
| `/login` | `app/login/page.tsx` | 登录页 |
| `/admin` | `app/admin/layout.tsx` | 管理后台布局 |
| `/admin/papers` | `app/admin/papers/page.tsx` | 试卷列表 |
| `/admin/papers/new` | `app/admin/papers/new/page.tsx` | 创建试卷 |
| `/admin/papers/[id]` | `app/admin/papers/[id]/page.tsx` | 试卷编辑 |
| `/p/[slug]` | `app/p/[slug]/page.tsx` | 公开页面 |

### API 客户端 (`web/src/lib/api.ts`)
```typescript
class ApiClient {
  private baseUrl: string;
  
  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const config: RequestInit = {
      credentials: "include",  // 携带 cookie
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "XMLHttpRequest",  // CSRF
        ...options.headers,
      },
      ...options,
    };
    
    const res = await fetch(url, config);
    
    // 5xx 重试
    if (res.status >= 500 && retries > 0) {
      await new Promise(r => setTimeout(r, 1000));
      return this.request<T>(endpoint, options, retries - 1);
    }
    
    if (!res.ok) {
      throw new ApiError(res.status, data.detail || "Request failed");
    }
    
    return data as T;
  }
  
  get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: "GET" });
  }
  
  post<T>(endpoint: string, body?: any, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }
}

export const api = new ApiClient();
```
