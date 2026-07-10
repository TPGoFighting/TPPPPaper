# TPaper 核心功能优化计划

> **日期**: 2026-07-10
> **状态**: 进行中

---

## 一、当前问题分析

### 1. 预处理层问题

| 问题 | 影响 |
|------|------|
| pypdf 文本提取质量差 | 中文试卷提取不完整，表格丢失 |
| 扫描件依赖 Tesseract OCR | OCR 准确率低，中文识别差 |
| 按页独立处理 | 跨页题目被切断 |

### 2. 提取层问题

| 问题 | 影响 |
|------|------|
| 按页独立调用 LLM | 第3页看不到第4页，跨页题目丢失上下文 |
| 提取+生成两阶段 | API 调用次数翻倍，成本高，延迟大 |
| 58页文档需调用58次 | Token 成本高，用户等待时间长 |

### 3. 生成层问题

| 问题 | 影响 |
|------|------|
| 分批生成+合并 | 合并后题目编号可能错乱 |
| JSON Schema 复杂 | LLM 输出不稳定，解析失败率高 |

---

## 二、优化目标架构

```
原始文件
    ↓
[文件类型识别]
    ↓
┌─────────────────────────────────────────┐
│ 预处理层（升级）                         │
│ • 文本型PDF → PyMuPDF / pdfplumber      │
│ • 扫描件PDF → 多模态LLM 直接读图（推荐）  │
│   或 PaddleOCR+PP-Structure（降本方案）  │
│ • Word → python-docx / mammoth          │
│ • 输出：带结构的Markdown/JSON（保留标题、  │
│   表格、列表层级，不只是纯文本）          │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 提取层（优化）                           │
│ • 不按页分块，按内容边界分块（题目/段落）  │
│ • 或保留滑动窗口重叠（每块带前后上下文）   │
│ • 小模型/规则提取候选题目边界              │
│ • 提取+生成合并为单阶段                   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ 渲染层（保留）                           │
│ • 受控组件，禁止<script>                  │
│ • 平台运行时接管交互逻辑                  │
└─────────────────────────────────────────┘
```

---

## 三、具体实现计划

### 阶段1：预处理层升级（优先级：高）

#### 1.1 替换 pypdf → PyMuPDF

**目标**: 提升文本提取质量，保留表格结构

**实现**:
```python
# worker/pipeline/preprocess.py
import fitz  # PyMuPDF

def preprocess_pdf(content: bytes) -> dict:
    doc = fitz.open(stream=content, filetype="pdf")
    pages = []
    for i, page in enumerate(doc):
        # 提取文本（保留布局）
        text = page.get_text("text")
        # 提取表格（如果有）
        tables = page.find_tables()
        # 提取图片（如果有）
        images = page.get_images()
        
        pages.append({
            "page": i + 1,
            "text": text,
            "tables": tables,
            "image_count": len(images),
            "needs_multimodal": len(text.strip()) < 50
        })
    return {"pages": pages, "page_count": len(pages)}
```

#### 1.2 扫描件处理：多模态LLM直接读图

**目标**: 替代 Tesseract OCR，提升准确率

**实现**:
```python
# 对于扫描件，直接将图片发送给多模态LLM
async def extract_with_vision(adapter, image_b64, page_number):
    prompt = f"""
    请提取第 {page_number} 页的所有内容，包括：
    1. 题目（题干、选项）
    2. 答案
    3. 解析
    4. 表格数据
    5. 章节标题
    
    输出格式为 JSON：
    {{
        "page": {page_number},
        "items": [
            {{"type": "question", "content": "题干内容"}},
            {{"type": "option", "content": "A. 选项内容"}},
            ...
        ],
        "confidence": 0.95
    }}
    """
    return await adapter.chat_with_image(prompt, image_b64, "image/png")
```

#### 1.3 备选方案：PaddleOCR + PP-Structure

**目标**: 降本方案，不依赖多模态LLM

**依赖**:
```bash
pip install paddlepaddle paddleocr ppstructure
```

**实现**:
```python
from paddleocr import PPStructure

engine = PPStructure(show_log=False, lang='ch')

def preprocess_with_paddle(content: bytes):
    # 将 PDF 转为图片
    images = pdf_to_images(content)
    results = []
    for img in images:
        result = engine(img)
        # PP-Structure 输出结构化结果
        # 包含表格、标题、文本区域
        results.append(parse_structure(result))
    return results
```

---

### 阶段2：提取层优化（优先级：高）

#### 2.1 按内容边界分块

**目标**: 保留跨页题目的完整性

**实现**:
```python
def split_by_content_boundaries(pages: list[dict]) -> list[dict]:
    """按内容边界分块，而不是按页分块"""
    chunks = []
    current_chunk = {"pages": [], "text": ""}
    
    for page in pages:
        text = page["text"]
        
        # 检测内容边界（题目结束标记）
        if is_question_end(text):
            current_chunk["pages"].append(page)
            chunks.append(current_chunk)
            current_chunk = {"pages": [], "text": ""}
        else:
            current_chunk["pages"].append(page)
            current_chunk["text"] += text + "\n"
    
    # 处理最后一个块
    if current_chunk["pages"]:
        chunks.append(current_chunk)
    
    return chunks

def is_question_end(text: str) -> bool:
    """检测题目结束标记"""
    # 常见结束标记：下一题题号、答案区域、解析区域
    patterns = [
        r'^\d+\.',  # 题号
        r'^[一二三四五六七八九十]+、',  # 中文题号
        r'答案[：:]',
        r'解析[：:]',
    ]
    return any(re.search(p, text.strip()) for p in patterns)
```

#### 2.2 滑动窗口重叠

**目标**: 保留跨页题目的上下文

**实现**:
```python
def split_with_overlap(pages: list[dict], window_size: int = 500) -> list[dict]:
    """带滑动窗口的分块"""
    chunks = []
    all_text = "\n".join([p["text"] for p in pages])
    
    # 按题目边界分块
    question_boundaries = find_question_boundaries(all_text)
    
    for i, boundary in enumerate(question_boundaries):
        start = max(0, boundary["start"] - window_size)  # 前置窗口
        end = min(len(all_text), boundary["end"] + window_size)  # 后置窗口
        
        chunk_text = all_text[start:end]
        chunks.append({
            "text": chunk_text,
            "start_page": boundary["start_page"],
            "end_page": boundary["end_page"],
            "question_count": boundary["question_count"]
        })
    
    return chunks
```

#### 2.3 小模型提取候选边界

**目标**: 用规则/小模型预处理，减少大模型调用

**实现**:
```python
def detect_question_boundaries(text: str) -> list[dict]:
    """用规则检测题目边界"""
    boundaries = []
    
    # 正则匹配题号
    patterns = [
        (r'(\d+)[.、．]\s*', 'number'),  # 1. 2. 3.
        (r'([一二三四五六七八九十]+)[、．]\s*', 'chinese_number'),
        (r'(第\d+题)', 'question_marker'),
    ]
    
    for pattern, type in patterns:
        for match in re.finditer(pattern, text):
            boundaries.append({
                "position": match.start(),
                "type": type,
                "content": match.group()
            })
    
    return sorted(boundaries, key=lambda x: x["position"])
```

---

### 阶段3：合并提取+生成（优先级：中）

#### 3.1 单阶段调用

**目标**: 减少 API 调用次数，降低成本和延迟

**实现**:
```python
async def extract_and_generate(adapter, preprocessed, mode):
    """合并提取+生成为单阶段"""
    
    system = """你是试卷结构化助手。请从原始内容中直接提取并生成结构化的试卷文档。

输出 JSON 必须符合以下 Schema：
{
  "title": "试卷标题",
  "questions": [
    {
      "number": 1,
      "type": "single_choice | multi_choice | true_false | fill_blank | subjective",
      "stem": "题干文本",
      "options": [{"key": "A", "text": "选项内容"}],
      "correct_keys": ["A"],
      "reference_answer": "参考答案",
      "explanation": "解析",
      "knowledge_points": ["知识点"]
    }
  ]
}

注意：
1. 必须忠实原文，不得补充或修改答案
2. 跨页题目要完整提取，不要切断
3. 保留表格、列表等结构"""
    
    # 将所有页面内容合并
    all_text = "\n\n".join([f"第{p['page']}页:\n{p['text']}" for p in preprocessed["pages"]])
    
    # 单次调用完成提取+生成
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": all_text}
    ]
    
    result = await adapter.chat(messages, response_format_json=True)
    return json.loads(result.content)
```

#### 3.2 大文档分批策略

**目标**: 保持单阶段调用，但支持大文档

**实现**:
```python
async def process_large_document(adapter, preprocessed, mode, max_pages_per_batch=20):
    """大文档分批处理"""
    pages = preprocessed["pages"]
    
    if len(pages) <= max_pages_per_batch:
        return await extract_and_generate(adapter, preprocessed, mode)
    
    # 按内容边界分批
    chunks = split_by_content_boundaries(pages)
    
    results = []
    for chunk in chunks:
        result = await extract_and_generate(adapter, chunk, mode)
        results.append(result)
    
    # 合并结果
    return merge_results(results)
```

---

## 四、实施步骤

### Step 1: 升级预处理层（1-2天）
- [ ] 替换 pypdf → PyMuPDF
- [ ] 实现多模态LLM直接读图
- [ ] 添加 PaddleOCR 作为备选方案
- [ ] 测试文本提取质量

### Step 2: 优化提取层（1-2天）
- [ ] 实现按内容边界分块
- [ ] 添加滑动窗口重叠
- [ ] 实现小模型/规则边界检测
- [ ] 测试跨页题目完整性

### Step 3: 合并提取+生成（1天）
- [ ] 实现单阶段调用
- [ ] 优化大文档分批策略
- [ ] 测试 API 调用次数和成本

### Step 4: 测试验证（1天）
- [ ] 用现代管理科学试卷测试
- [ ] 对比优化前后效果
- [ ] 性能测试（延迟、成本）

---

## 五、预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 文本提取质量 | 低（pypdf） | 高（PyMuPDF + 多模态LLM） |
| 跨页题目完整性 | 被切断 | 完整保留 |
| API 调用次数 | 58次（提取）+ N次（生成） | 1-3次（合并） |
| Token 成本 | 高 | 降低60-80% |
| 用户等待时间 | 长（900秒） | 短（预期120-180秒） |
| OCR 准确率 | 低（Tesseract） | 高（多模态LLM） |

---

## 六、风险与注意事项

1. **多模态LLM 成本**: 虽然调用次数减少，但每次调用的 token 数量可能增加
2. **PyMuPDF 依赖**: 需要安装 `fitz` 库
3. **PaddleOCR 部署**: 需要 GPU 支持才能发挥最佳性能
4. **向后兼容**: 需要保留旧的处理方式作为兜底

---

## 七、参考资源

- [PyMuPDF 文档](https://pymupdf.readthedocs.io/)
- [PaddleOCR 文档](https://paddleocr.readthedocs.io/)
- [PP-Structure 文档](https://paddleocr.readthedocs.io/en/latest/ppstructure/overview.html)
- [marker PDF 解析](https://github.com/VikParuchuri/marker)
- [unstructured 文档解析](https://github.com/Unstructured-IO/unstructured)
