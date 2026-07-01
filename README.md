# TPaper

AI 试卷转换工具 — 将 PDF、DOCX、图片等试卷/复习资料转换为可在线访问的交互式复习网页。

基于 [SPEC.md](./SPEC.md) 实现。单管理员、自托管、Docker Compose 部署。

## 项目结构

```
TPPPPaper/
├── backend/          # FastAPI 后端（API + 数据模型 + 安全 + 存储适配器）
│   ├── app/
│   │   ├── api/      # 路由：auth / model-profiles / uploads / papers / jobs / drafts / publications / public / assets
│   │   ├── models/   # SQLAlchemy ORM：7 个核心数据模型
│   │   ├── schemas.py        # Pydantic Schema + PaperDocument 校验器
│   │   ├── security/         # 密码哈希 / API Key 信封加密 / SSRF 防护 / HTML-CSS 净化
│   │   ├── storage/          # 存储抽象 + 本地私有卷实现
│   │   ├── adapters/         # OpenAI-compatible 模型适配器
│   │   └── main.py           # FastAPI 入口
│   ├── alembic/      # 数据库迁移
│   └── pyproject.toml
├── worker/           # 异步任务 Worker（文档预处理 + 两阶段模型处理 + 网页生成 + 净化）
├── web/              # Next.js 14 前端（管理后台 + 公开复习页）
├── docker/           # Dockerfile（api / worker / web）
├── docker-compose.yml
├── SPEC.md           # 产品需求与系统设计
└── tpaper-app/       # 前端原型（React + Vite，设计参考）
```

## 快速开始

### Docker Compose 部署（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env，设置 MASTER_SECRET、SESSION_SECRET、ADMIN_PASSWORD_HASH

# 2. 生成管理员密码哈希
docker compose run --rm api python -c \
  "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('your-password'))"
# 将输出填入 .env 的 ADMIN_PASSWORD_HASH

# 3. 启动
docker compose up -d

# 4. 检查健康状态
docker compose ps
```

访问地址：
- 前端：http://localhost:3000
- API 文档：http://localhost:8000/api/docs
- 公开复习页：http://localhost:3000/p/{slug}

### 本地开发

**后端：**
```bash
cd backend
pip install -e .
# 配置 PostgreSQL 与 Redis，设置 .env
alembic revision --autogenerate -m "init"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Worker：**
```bash
cd worker
pip install -e .
python main.py
```

**前端：**
```bash
cd web
npm install
npm run dev
```

开发环境默认管理员：`admin` / `admin`（仅 `ENV=dev` 时生效）。

## 架构概览

| 组件 | 技术 | 职责 |
|------|------|------|
| web | Next.js 14 + TypeScript + Tailwind | 管理后台、公开复习页 |
| api | FastAPI + SQLAlchemy + Alembic | 鉴权、CRUD、发布编译、公开读取 |
| worker | Python asyncio + Redis 队列 | 文档预处理、模型调用、HTML/CSS 净化 |
| postgres | PostgreSQL 16 | 业务数据持久化 |
| redis | Redis 7 | 任务队列、锁 |

## 核心数据流

```
上传 → 预处理(PDF/DOCX/图片) → 两阶段模型提取 → PaperDocument 校验
     → 生成受控 HTML/CSS → 净化 → 草稿 → 管理员审核 → 发布(不可变版本)
     → 访客通过 /p/{slug} 答题
```

## 安全要点

- API Key 信封加密（部署级主密钥）
- SSRF 防护（阻止回环、内网、云元数据地址）
- HTML/CSS 净化（禁止 script、事件属性、iframe、远程导入）
- 严格 CSP（公开页 `script-src 'none'`）
- 源文件七天后自动清理，无公开路由
- CSRF 防护（状态修改接口需自定义头）
- 文件签名校验（防伪造类型）

## 验收标准

详见 [SPEC.md 第 19 节](./SPEC.md#19-mvp-验收标准)。

## 许可

© 2025 TPaper. All rights reserved.
