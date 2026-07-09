# TPaper 文档索引

> **最后更新**: 2026-07-09
> **在线体验**: https://tpaper.tpgofighting.top
> **管理员账号**: admin / rkiOqvL2WR7Uwlw0

---

## 快速导航

| 文档 | 说明 |
|------|------|
| [CHANGELOG-2026-07-09.md](./CHANGELOG-2026-07-09.md) | 今日所有修改记录 |
| [ARCHITECTURE-GUIDE.md](./ARCHITECTURE-GUIDE.md) | 核心功能实现详解 |
| [FILE-REFERENCE.md](./FILE-REFERENCE.md) | 每个文件的作用说明 |

---

## 项目概述

TPaper 是一个 AI 驱动的试卷转换系统，支持将 PDF/图片格式的试卷转换为可编辑的 HTML 格式。

### 核心功能
- 📄 PDF/图片试卷上传
- 🤖 AI 识别题目（支持 OpenAI/Claude/通义千问）
- ✏️ 在线编辑题目和答案
- 🌐 生成可分享的链接

### 技术栈
- **后端**: FastAPI + SQLAlchemy + Celery + Redis
- **前端**: Next.js + React + TypeScript
- **部署**: Docker Compose (5 服务)

---

## 目录结构

```
TPPPPaper/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/               # API 路由
│   │   ├── adapters/          # AI 模型适配器
│   │   ├── models/            # 数据模型
│   │   └── ...
│   └── ...
├── web/                        # Next.js 前端
│   └── src/
│       ├── app/               # 页面
│       ├── components/        # 组件
│       └── lib/               # 工具库
├── worker/                     # Celery Worker
│   └── pipeline/              # 处理流水线
├── docs/                       # 文档目录
│   ├── INDEX.md               # 本文件
│   ├── CHANGELOG-2026-07-09.md
│   ├── ARCHITECTURE-GUIDE.md
│   └── FILE-REFERENCE.md
└── docker/                     # Docker 配置
```

---

## 服务架构

```
用户请求 → Cloudflare Tunnel → Nginx (8084) → Web (3000) → API (8000) → PostgreSQL
                              ↓
                           Redis (队列) → Worker (Celery) → 模型 API
```

### 服务列表
| 服务 | 端口 | 说明 |
|------|------|------|
| postgres | 5432 | 数据库 |
| redis | 6379 | 消息队列 |
| api | 8000 | FastAPI 后端 |
| worker | - | Celery Worker |
| web | 3000 | Next.js 前端 |
| nginx | 8084 | 反向代理 |
