# 前后端分离 & 数据层分析 — 2026-07-09

## 一、前后端分离现状

### 1.1 架构概览

```
浏览器 → Nginx(:8084) → Web容器(:3000 Next.js) → API容器(:8000 FastAPI) → PostgreSQL
```

- **前端**：Next.js 14 App Router，部署在 `tpaper-web-1` 容器
- **后端**：FastAPI，部署在 `tpaper-api-1` 容器
- **通信方式**：Next.js rewrite 代理 `/api/*` 到 FastAPI

### 1.2 API 调用方式

前端使用自定义 fetch 封装（`web/src/lib/api.ts`），通过 `NEXT_PUBLIC_API_URL` 环境变量配置 API 地址，默认 `/api`。

**认证机制**：后端使用 httpOnly cookie（`tpaper_session`），前端通过 `credentials: 'include'` 自动携带。

### 1.3 发现的问题

#### 问题 1：登录后 token 存储逻辑不完整（高）

`web/src/app/login/page.tsx:26` 调用 `api.post('/auth/login', ...)` 后，**没有任何代码将 token 写入 localStorage**。

`web/src/lib/api.ts:117-119` 中 `getToken()` 从 `localStorage.getItem('tpaper_token')` 读取 token，但从未写入。

**实际效果**：由于后端使用 httpOnly cookie 认证，`credentials: 'include'` 使 cookie 自动携带，登录功能实际上**可以正常工作**。但 Bearer token 路径是死代码，增加了混淆。

#### 问题 2：退出登录未清除会话（中）

`web/src/components/Navbar.tsx:142-143` 退出按钮只是一个 `<Link href="/login">`：
- 没有调用 `POST /api/auth/logout`
- 没有清除 cookie
- 没有清除 localStorage

**后果**：用户点击"退出登录"后，session cookie 仍然有效，刷新页面后仍处于登录状态。

#### 问题 3：公开页面绕过 API 客户端（低）

`web/src/app/p/[slug]/page.tsx` 使用原生 `fetch('/api/public/papers/...')` 而非封装的 `api` 客户端：
- 硬编码 `/api` 路径，忽略 `NEXT_PUBLIC_API_URL` 环境变量
- 错误处理不一致

#### 问题 4：无全局错误处理（低）

每个页面独立处理错误，无全局 error boundary、toast 通知或重试逻辑。5秒轮询间隔会静默吞掉错误。

---

## 二、数据层分离分析

### 2.1 当前数据访问模式

**直接 SQLAlchemy 查询，无 Repository/Service 层。**

所有 API handler 直接接收 `DBSession` 并内联执行查询：

```python
# backend/app/api/papers.py
@router.get("")
async def list_papers(
    db: DBSession,
    _: AdminUser,
    status: str | None = None,
    q: str | None = None,
):
    query = db.query(Paper)
    if status:
        query = query.filter(Paper.status == status)
    if q:
        query = query.filter(Paper.title.ilike(f"%{q}%"))
    return query.order_by(Paper.updated_at.desc()).all()
```

### 2.2 数据层问题

#### 问题 1：无 Repository/Service 抽象（中）

- 每个 handler 都包含业务逻辑和数据访问逻辑
- 无法复用查询逻辑（如"查找用户的 papers"）
- 单元测试困难（需要 mock 数据库）

#### 问题 2：手动级联删除（中）

`backend/app/api/papers.py:67-71` 中 `DELETE /api/papers/{id}` 手动删除关联记录：

```python
db.query(PaperDraft).filter(PaperDraft.paper_id == paper_id).delete()
db.query(ProcessingJob).filter(ProcessingJob.paper_id == paper_id).delete()
db.query(PublicationVersion).filter(PublicationVersion.paper_id == paper_id).delete()
db.delete(paper)
db.commit()
```

SQLAlchemy 模型未定义 `cascade="all, delete-orphan"`，依赖手动删除，容易遗漏。

#### 问题 3：无分页（低）

`GET /api/papers` 返回全部记录（`.all()`），无 `limit/offset` 或游标分页。数据量增长后会性能退化。

#### 问题 4：Slug 生成存在竞态条件（低）

```python
while db.query(Paper).filter(Paper.slug == slug).first():
    slug = f"{base_slug}-{suffix}"
    suffix += 1
```

并发请求可能生成相同 slug，依赖数据库唯一约束兜底。

---

## 三、公网测试结果

通过 `https://tpaper.tpgofighting.top` 测试：

| 操作 | 结果 |
|------|------|
| 登录 `POST /api/auth/login` | ✅ 成功，cookie 正确设置 |
| 认证检查 `GET /api/auth/me` | ✅ 返回用户信息 |
| 论文列表 `GET /api/papers` | ✅ 返回 5 篇论文 |
| 论文详情 `GET /api/papers/6` | ✅ pending_review |
| 草稿详情 `GET /api/drafts/10` | ✅ 12 题 |
| 创建论文 `POST /api/papers` | ✅ 返回新论文 |
| 上传文件 `POST /api/uploads/file` | ✅ 文件上传成功 |
| 删除论文 `DELETE /api/papers/{id}` | ⚠️ 部分返回 Internal Server Error |

**结论**：API 本身工作正常，但前端与后端的集成存在上述问题。

---

## 四、修复建议

### 优先级 P0（必须修复）

1. **退出登录**：调用 `POST /api/auth/logout` 并清除 cookie
2. **删除论文 Internal Error**：检查 cascade 删除逻辑

### 优先级 P1（建议修复）

3. **统一认证机制**：移除 localStorage token 逻辑，仅依赖 httpOnly cookie
4. **公开页面使用 API 客户端**：统一错误处理
5. **添加全局 Error Boundary**：防止页面白屏

### 优先级 P2（架构优化）

6. **引入 Repository 层**：分离数据访问逻辑
7. **使用 SQLAlchemy cascade**：替代手动删除
8. **添加分页**：`GET /api/papers?page=1&size=20`
9. **添加全局错误处理和重试**：提升用户体验
