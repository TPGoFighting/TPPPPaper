# 文件作用说明

> **在线体验**: https://tpaper.tpgofighting.top
> **管理员账号**: admin / rkiOqvL2WR7Uwlw0

---

## 目录

1. [后端 (backend/)](#1-后端-backend)
2. [前端 (web/)](#2-前端-web)
3. [Worker (worker/)](#3-worker-worker)
4. [Docker (docker/)](#4-docker-docker)
5. [文档 (docs/)](#5-文档-docs)

---

## 1. 后端 (backend/)

### 核心配置

| 文件 | 作用 |
|------|------|
| `backend/app/__init__.py` | 应用包初始化 |
| `backend/app/main.py` | FastAPI 入口，注册路由、中间件、生命周期 |
| `backend/app/config.py` | 配置管理（环境变量读取） |
| `backend/app/database.py` | 数据库连接（SQLAlchemy） |
| `backend/app/deps.py` | 依赖注入（认证、CSRF、数据库会话） |
| `backend/app/queue.py` | 任务队列（Celery send_task） |

### API 路由

| 文件 | 作用 |
|------|------|
| `backend/app/api/auth.py` | 认证 API（登录/登出/会话） |
| `backend/app/api/papers.py` | 试卷 CRUD API |
| `backend/app/api/uploads.py` | 文件上传 API |
| `backend/app/api/jobs.py` | 任务 API（状态查询、SSE 流） |
| `backend/app/api/publications.py` | 发布 API（公开链接与版本控制） |
| `backend/app/api/model_profiles.py` | 模型配置 API 与一键诊断 |
| `backend/app/api/assets.py` | 资源 API（图片与私有卷访问） |
| `backend/app/api/drafts.py` | 草稿 API 与 AI 局部修题 |
| `backend/app/api/public.py` | 公开复习读取 API |
| `backend/app/api/metrics.py` | 监控仪表盘指标 API |

### 数据模型

| 文件 | 作用 |
|------|------|
| `backend/app/models/__init__.py` | SQLAlchemy 模型定义（Paper, SourceFile, ProcessingJob 等） |

### AI 适配器

| 文件 | 作用 |
|------|------|
| `backend/app/adapters/__init__.py` | 模型适配器（支持 OpenAI/Claude/通义千问）、限流、重试 |

### 处理模块

| 文件 | 作用 |
|------|------|
| `backend/app/processing.py` | 进程内处理（Redis 不可用时的备选） |

---

## 2. 前端 (web/)

### 页面

| 文件 | 作用 |
|------|------|
| `web/src/app/layout.tsx` | 根布局（ErrorBoundary） |
| `web/src/app/page.tsx` | 首页 |
| `web/src/app/login/page.tsx` | 登录页 |
| `web/src/app/admin/layout.tsx` | 管理后台布局（认证守卫） |
| `web/src/app/admin/page.tsx` | 工作台试卷列表页 |
| `web/src/app/admin/upload/page.tsx` | 上传试卷资料页 |
| `web/src/app/admin/settings/page.tsx` | 模型配置设置页 |
| `web/src/app/admin/papers/[id]/page.tsx` | 试卷编辑审核页 |
| `web/src/app/p/[slug]/page.tsx` | 公开复习页面（无需登录） |

### 组件与功能模块

| 文件 | 作用 |
|------|------|
| `web/src/components/Navbar.tsx` | 导航栏（无障碍抽屉、登出逻辑） |
| `web/src/components/ErrorBoundary.tsx` | 全局错误边界与自愈重试 |
| `web/src/components/BrandMark.tsx` | 顶栏 Logo 品牌优化组件 |
| `web/src/components/StatusBadge.tsx` | 状态标签组件 |
| `web/src/features/admin-dashboard/components.tsx` | 工作台仪表盘与试卷卡片核心组件 |

### 工具库

| 文件 | 作用 |
|------|------|
| `web/src/lib/api.ts` | API 客户端（超时重试、CSRF、Cookie、错误解构） |

### 样式

| 文件 | 作用 |
|------|------|
| `web/src/app/globals.css` | 全局样式 |
| `tailwind.config.js` | Tailwind CSS 配置 |

### 配置

| 文件 | 作用 |
|------|------|
| `web/next.config.mjs` | Next.js 配置（API 代理） |
| `web/package.json` | 依赖管理 |

---

## 3. Worker (worker/)

### 核心

| 文件 | 作用 |
|------|------|
| `worker/celery_app.py` | Celery 实例配置 |
| `worker/tasks.py` | 主 Celery 任务定义（process_paper Pipeline） |
| `worker/tasks_simple.py` | 快速路径 Celery 任务定义（process_paper_simple） |

### 流水线

| 文件 | 作用 |
|------|------|
| `worker/pipeline/__init__.py` | Pipeline 包初始化 |
| `worker/pipeline/preprocess.py` | 预处理（PDF/图片/OCR） |
| `worker/pipeline/extract.py` | LLM 提取（并行） |
| `worker/pipeline/generate.py` | 文档生成（分块） |
| `worker/pipeline/render.py` | HTML/CSS 渲染 |
| `worker/pipeline/sanitize.py` | 内容清理 |

---

## 4. Docker (docker/)

| 文件 | 作用 |
|------|------|
| `docker/Dockerfile.api` | API 镜像（复制 worker/ 包） |
| `docker/Dockerfile.web` | Web 镜像（Next.js 构建） |
| `docker/Dockerfile.worker` | Worker 镜像（Celery + tesseract） |

---

## 5. 文档 (docs/)

| 文件 | 作用 |
|------|------|
| `docs/INDEX.md` | 文档索引（本文件） |
| `docs/CHANGELOG-2026-07-09.md` | 今日修改记录 |
| `docs/ARCHITECTURE-GUIDE.md` | 核心功能实现详解 |
| `docs/FILE-REFERENCE.md` | 每个文件的作用说明 |

---

## 6. 测试 (tests/)

| 文件 | 作用 |
|------|------|
| `tests/e2e_production_test.py` | 生产环境端到端测试 |

---

## 7. 根目录配置

| 文件 | 作用 |
|------|------|
| `.env` | 环境变量（不提交到 git） |
| `docker-compose.yml` | Docker 服务编排（5 服务） |
| `requirements.txt` | Python 依赖 |
| `package.json` | Node.js 依赖 |
