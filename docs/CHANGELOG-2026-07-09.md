# 更新日志 - 2026-07-09

> **在线体验**: https://tpaper.tpgofighting.top
> **管理员账号**: admin / rkiOqvL2WR7Uwlw0

---

## 今日修改汇总

### 📦 已推送的 Commits

| Commit | 说明 |
|--------|------|
| `044cf97` | fix: 添加 SQLAlchemy cascade 关系，修复 Paper 删除时级联问题 |
| `338ffe2` | fix: 修复前后端集成问题 (2026-07-09) |
| `dc7f866` | fix: send Celery tasks to 'tpaper' queue instead of default 'celery' queue |
| `f9eea9e` | refactor: architecture redesign - Celery worker + modular pipeline + SSE |

---

## 详细修改记录

### 1. 架构重设计 (`f9eea9e`)

#### 新增文件
- `worker/celery_app.py` - Celery 实例配置
- `worker/tasks.py` - Celery 任务定义
- `worker/pipeline/preprocess.py` - 预处理模块（PDF/图片/OCR）
- `worker/pipeline/extract.py` - LLM 提取模块
- `worker/pipeline/generate.py` - 文档生成模块
- `worker/pipeline/render.py` - HTML/CSS 渲染模块
- `worker/pipeline/sanitize.py` - 内容清理模块
- `backend/app/api/jobs.py` - SSE 流式端点

#### 修改文件
- `docker-compose.yml` - 添加 worker 服务
- `docker/Dockerfile.api` - 复制 worker/ 包
- `docker/Dockerfile.worker` - 新增 worker 镜像
- `backend/app/main.py` - 移除进程内轮询
- `backend/app/queue.py` - Celery send_task 集成

#### 核心功能
- **模块化流水线**: 预处理 → 提取 → 生成 → 渲染 → 清理
- **SSE 实时进度**: `GET /api/jobs/{job_id}/stream`
- **分块生成**: 每 10 题一块，最后合并重新编号

---

### 2. Celery 队列修复 (`dc7f866`)

#### 问题
Worker 启动后空闲，任务发送到默认 `celery` 队列而非 `tpaper`。

#### 修复
```python
# backend/app/queue.py
result = send_task(
    "worker.tasks.process_paper",
    args=[paper_id, source_file_id],
    queue="tpaper"  # 显式指定队列
)
```

---

### 3. 前后端集成问题修复 (`338ffe2`)

#### P0-1: 登出按钮无效
**文件**: `web/src/components/Navbar.tsx`

**问题**: 登出只是链接跳转，未调用 API 清除 session。

**修复**:
```tsx
const handleLogout = async () => {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "include",
  });
  window.location.href = "/login";
};
```

---

#### P0-2: 删除试卷报 Internal Server Error
**文件**: `backend/app/api/papers.py`

**问题**: 删除 Paper 时未级联删除 Asset 和 SourceFile。

**修复**:
```python
# 删除相关资源
db.query(Asset).filter(Asset.paper_id == paper.id).delete()
db.query(SourceFile).filter(SourceFile.paper_id == paper.id).delete()
db.delete(paper)
db.commit()
```

---

#### P1-1: 移除死代码（localStorage token）
**文件**: `web/src/lib/api.ts`

**问题**: 前端有从 localStorage 读取 token 并添加到请求头的代码，但认证已改为 httpOnly cookie。

**修复**: 删除 `getToken()` 和 `Authorization: Bearer` 头。

---

#### P1-2: 公开页面直接调用 fetch
**文件**: `web/src/app/p/[slug]/page.tsx`

**问题**: 公开页面直接使用 `fetch()`，未走统一的 `api` 客户端。

**修复**: 改用 `api.get()` 并设置 `auth: false`。

---

#### P1-3: 添加全局错误边界
**文件**: `web/src/components/ErrorBoundary.tsx`, `web/src/app/layout.tsx`

**问题**: 未捕获异常导致白屏。

**修复**: 添加 `ErrorBoundary` 组件包裹根布局。

---

#### P2-4: API 客户端重试逻辑
**文件**: `web/src/lib/api.ts`

**问题**: 网络波动或服务重启时无重试机制。

**修复**:
```typescript
async request<T>(endpoint: string, options: RequestInit = {}, retries = 2): Promise<T> {
  // 5xx 错误重试
  if (res.status >= 500 && retries > 0) {
    await new Promise(r => setTimeout(r, 1000));
    return this.request<T>(endpoint, options, retries - 1);
  }
}
```

---

### 4. SQLAlchemy Cascade 修复 (`044cf97`)

**文件**: `backend/app/models/__init__.py`

**问题**: 删除 Paper 时，相关的 Asset、SourceFile、PaperDraft 等不自动删除。

**修复**:
```python
class Paper(TimestampMixin, Base):
    source_file: Mapped["SourceFile | None"] = relationship(
        foreign_keys=[source_file_id], cascade="all, delete-orphan"
    )
    drafts: Mapped[list["PaperDraft"]] = relationship(
        back_populates="paper", foreign_keys="PaperDraft.paper_id", cascade="all, delete-orphan"
    )
    publications: Mapped[list["PublicationVersion"]] = relationship(
        back_populates="paper", foreign_keys="PublicationVersion.paper_id", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["ProcessingJob"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    assets: Mapped[list["Asset"]] = relationship(
        foreign_keys="Asset.paper_id", cascade="all, delete-orphan"
    )
```

同时为 `Asset` 模型添加了 `paper` 反向引用：
```python
class Asset(TimestampMixin, Base):
    paper: Mapped["Paper | None"] = relationship(back_populates="assets", foreign_keys=[paper_id])
```

---

## 部署信息

### 服务器
- **IP**: 43.142.121.230
- **部署目录**: `/opt/tpaper/`
- **SSH**: `ssh -i ~/.ssh/tpbili.pem root@43.142.121.230`

### 环境变量
- **数据库**: PostgreSQL (postgres/postgres@127.0.0.1:5432/tpaper)
- **Redis**: Redis (redis://127.0.0.1:6379/0)
- **模型**: LongCat-2.0 (ak_2u634A1cq02E3t15Xw4iM39A7hX1Q)

### Docker 命令
```bash
# 重启服务
cd /opt/tpaper && docker compose restart api web worker

# 查看日志
docker compose logs -f worker --tail=100

# 重建
docker compose up -d --build api web worker
```

---

## 测试验证

### 公开页面测试
- 登录: ✅
- 上传 PDF: ✅
- 创建试卷: ✅
- 编辑题目: ✅
- 删除试卷: ✅
- 公开链接: ✅

### Celery Worker 测试
- 任务发送: ✅
- 队列路由: ✅
- 进度更新: ✅
- SSE 流: ✅
