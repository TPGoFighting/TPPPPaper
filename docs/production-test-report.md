# TPaper 生产环境端到端测试报告（PRODUCTION E2E TEST REPORT）

- **部署地址**：https://tpaper.tpgofighting.top
- **后端 API**：https://tpaper.tpgofighting.top/api
- **测试时间**：2026-07-09 17:24 CST（测试机直连服务器 `http://127.0.0.1:3000` 与应用内网通信）
- **测试方法**：第一性原理分层验证——把系统拆成「认证 / 上传校验 / 模型处理 / 发布 / 公开页安全 / 模型连通性」六层，逐层独立验证，并直接调用模型适配器隔离“模型层”以定位根因。
- **测试脚本**：`tests/e2e_production_test.py`（仅依赖 Python 标准库，可在服务器上 `python3 e2e_production_test.py http://127.0.0.1:3000` 复现）

## 一、测试结果总览

| 指标 | 结果 |
|------|------|
| 总检查项 | 17 |
| 通过 | 15 |
| 失败 | 2 |
| 模型真实调用 | 是（LongCat-2.0，HTTP 200，非本地兜底） |

> 失败项均为 **SPEC 合规性偏差（CSP / 脚本）**，非功能崩溃；另发现 1 个会导致 DOCX 上传 500 的真实 schema bug，已修复。

## 二、分层验证明细（第一性原理）

### 1. 认证层 ✅
- 登录 `POST /api/auth/login` → 200，签发 `Secure; HttpOnly; SameSite=Lax` 会话 Cookie。
- 携带 Cookie 访问 `/api/auth/me` → 200。
- 不携带 Cookie → 401（正确拒绝）。
- 状态修改接口缺少 `X-Requested-With` 头 → 403（CSRF 防护生效）。

### 2. 上传校验层 ✅
- 合法 PDF（结构合法、含 xref）→ 200，返回 `paper_id` + `slug`。
- 伪造签名文件（纯文本谎称 PDF）→ 400（文件签名校验生效，防类型伪造）。
- 上传接口缺 CSRF 头 → 403。

### 3. 模型处理层 ✅（修复 schema bug 后）
- 任务达到终态 `succeeded`，`call_summary.model = "LongCat-2.0"`（**真实调用模型，非本地兜底**）。
- 合法 DOCX 输入 → 抽取出 3 道真实题目（single_choice / subjective / fill_blank），题干命中源文件内容。
- 模型连通性独立校验 `POST /api/model-profiles/test-connection` → `success: true`。

### 4. 发布层 ✅
- `POST /api/publications` → 201，生成不可变发布版本；公开页 `GET /api/public/papers/{slug}/page` → 200。

### 5. 公开页安全层 ⚠️（见 F3 / F4）
- CSP 未设置 `script-src 'none'`（SPEC 明确要求）。
- 渲染 HTML 内含平台注入的 `<script>`。

## 三、发现的问题（已沉淀）

---

### 🔴 F1【严重 / 已修复】上传 .docx 返回 HTTP 500（数据库列宽度不足）

- **现象**：上传任意 `.docx` 文件时，API 返回 500；PDF / 图片上传正常。
- **根因**：`source_files` 表的 `mime_type` / `detected_type` 列在**数据库实际为 `VARCHAR(50)`**，但模型定义 `mime_type` 已是 `VARCHAR(100)`（说明曾改过模型但未同步库表）。`.docx` 的真实 MIME 为
  `application/vnd.openxmlformats-officedocument.wordprocessingml.document`（**73 字符**），超过 50 字符 →
  `psycopg.errors.StringDataRightTruncation: value too long for type character varying(50)`。
  PDF（`application/pdf`，15 字符）与图片（≤10 字符）不触发，故此前未被发现。
- **证据**：
  - `backend/app/api/uploads.py:98` 写入 `mime_type=detected`。
  - 数据库列定义（迁移缺失）：`information_schema` 显示 `mime_type`/`detected_type` = `character varying(50)`。
  - 模型定义：`backend/app/models/__init__.py:145` `mime_type = String(100)`；`:150` `detected_type = String(50)`。
- **修复**：
  1. `ALTER TABLE source_files ALTER COLUMN mime_type TYPE VARCHAR(128); ALTER COLUMN detected_type TYPE VARCHAR(128);`（已在生产库执行）。
  2. 同步模型：`backend/app/models/__init__.py` 将 `mime_type`/`detected_type` 改为 `String(128)`。
  3. 回归验证：重新上传 DOCX → 200，成功抽取 3 题。
- **状态**：✅ 已修复并验证。

---

### 🟡 F2【中等 / 已记录，未改】损坏/非法 PDF 静默产出空试卷

- **现象**：上传一份**缺少 `xref`/`startxref` 交叉引用表**的非法 PDF 时，处理流水线不会报错，而是产出一个 `questions: []` 的空 `PaperDocument`（标题为空）。
- **根因**：`preprocess_pdf()`（`backend/app/processing.py:36`）用 `pypdf` 解析失败时抛 `startxref not found`，被 `except` 捕获并把该页标记为 `needs_multimodal=True` 但**不携带 `image_b64`**；进入 `stage1_extract` 后文本为空，模型拿不到内容，最终 `stage2` 生成空文档。应用没有对“源文件完全无法解析”给出明确错误/警告，而是静默降级为空试卷。
- **说明**：本项同时暴露一个**测试资产问题**——首版端到端测试用的 PDF 是我手工拼写的、缺少 xref 的非法 PDF，本身无法被解析（已在第一性原理排查中定位并修正测试脚本，改用运行时正确计算偏移量的合法 PDF）。
- **建议修复**：当所有页 `needs_multimodal` 且无图像、且提取文本为空时，应在草稿中标记 `needs_review=True` 并附带“源文件解析失败，请人工补充”的明确提示，而非空文档。
- **状态**：🟡 已记录；测试脚本已改为生成结构合法 PDF。

---

### 🟠 F3【安全 / SPEC 偏差，已记录】公开页 CSP 未设置 `script-src 'none'`

- **现象**：公开复习页响应头为
  `default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; script-src 'unsafe-inline'; object-src 'none'; base-uri 'none'`。
- **根因**：`backend/app/api/public.py:78` 显式写死 `script-src 'unsafe-inline'`。而 SPEC（README “安全要点” 与第 9/19 节）明确要求公开页 **`script-src 'none'`**。这是与规范的偏离（代码注释称“允许交互式试卷必要的脚本”）。
- **影响**：公开页允许同源内联脚本执行，削弱了“公开页零脚本”的纵深防御（与 F4 同源）。
- **建议修复**：若坚持 SPEC 的 `script-src 'none'`，需移除公开页内的运行时脚本（见 F4），答题/判分改由独立宿主页或原生表单实现；或至少在 CSP 中收紧为 `script-src 'none'` 并接受公开页无交互脚本。
- **状态**：🟠 已记录；**未改动**（避免破坏现有答题交互，待架构决策）。

---

### 🟠 F4【SPEC 偏差，已记录】公开页 HTML 内含平台注入的 `<script>`

- **现象**：`GET /api/public/papers/{slug}/page` 返回的 HTML 中包含 `<script>`（如 `IntersectionObserver` 运行时，用于答题进度/可见性跟踪）。
- **根因**：编译后的试卷 HTML 由 `backend/app/presentation.py:583` 的渲染器**主动注入内联 `<script>`**（平台运行时，用于交互答题）。适配器与净化器 (`backend/app/security/__init__.py:185`) 只禁止**模型生成**的 `<script>`，不禁止**平台自身**注入的脚本。CSP（F3）用 `script-src 'unsafe-inline'` 放行了它。
- **与 SPEC 的冲突**：SPEC 要求公开页“`script-src 'none'`”且“禁止生成 JavaScript”，意图是公开页为纯静态内容、答题由平台运行时实现。当前实现把运行时脚本直接写进公开页 HTML，与规范意图冲突。
- **建议修复**：将交互运行时从“写进每份试卷 HTML”改为由外层宿主页（如 Next.js 公开路由 `/p/[slug]`）统一提供，试卷 HTML 仅保留受控静态结构；届时可安全设置 `script-src 'none'`。
- **状态**：🟠 已记录；**未改动**（与 F3 配套，需架构决策）。

## 四、结论

1. 核心链路（认证 → 上传 → 大模型转换 → 草稿 → 发布 → 公开访问）在生产环境**端到端打通**，LongCat-2.0 模型真实参与转换并产出结构化题目。
2. 发现并修复了一个会导致 **.docx 上传 500** 的真实数据库 schema bug（已回归验证通过）。
3. 暴露两个与 SPEC 一致的公开页安全/合规偏差（CSP `script-src 'none'` 缺失、公开页含平台脚本），已沉淀待架构决策。
4. 测试脚本 `tests/e2e_production_test.py` 已固化为可复现的回归测试（使用结构合法的 PDF）。

## 五、复现命令

```bash
# 在部署服务器上
cd /opt/tpaper
python3 e2e_production_test.py http://127.0.0.1:3000
# 期望输出：TOTAL=17 PASS=15 FAIL=2（仅 F3/F4 两项 SPEC 合规偏差）
```
