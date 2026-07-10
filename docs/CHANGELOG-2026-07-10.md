# Changelog - 2026-07-10

## 核心功能优化

### 新增优化计划文档

**文件**: `docs/OPTIMIZATION-PLAN.md`

详细记录了核心功能优化的完整计划，包括：
- 当前问题分析
- 优化目标架构
- 具体实现计划
- 实施步骤
- 预期效果
- 风险与注意事项

---

### 预处理层升级 (PyMuPDF + 多模态LLM)

**文件**: `worker/pipeline/preprocess_v2.py`

**升级点**:
1. **PyMuPDF 替代 pypdf**: 提升文本提取质量，保留表格结构
2. **多模态LLM直接读图**: 替代 Tesseract OCR，提升准确率
3. **保留结构信息**: 表格、标题、列表层级

**主要功能**:
- `preprocess_pdf_v2()`: PDF 预处理，PyMuPDF 提取文本+表格
- `preprocess_docx_v2()`: DOCX 预处理，python-docx 提取结构化内容
- `preprocess_image_v2()`: 图片预处理，直接进入多模态识别
- `split_by_content_boundaries()`: 按内容边界分块
- `split_with_overlap()`: 带滑动窗口的分块
- `is_question_end()`: 检测题目结束标记

---

### 提取层优化 (按内容边界分块 + 滑动窗口)

**问题**: 原实现按页独立处理，导致跨页题目被切断

**解决方案**:
1. **按内容边界分块**: 不按页分块，按题目/段落边界分块
2. **滑动窗口重叠**: 每块带前后上下文，保留跨页题目完整性

**实现**:
```python
def split_by_content_boundaries(pages):
    """按内容边界分块，保留跨页题目的完整性"""
    # 检测题目结束标记（题号、答案、解析等）
    # 合并跨页内容到同一块

def split_with_overlap(pages, window_size=200):
    """带滑动窗口的分块，保留跨页上下文"""
    # 前置窗口：前一块的末尾
    # 后置窗口：后一块的开头
```

---

### 提取+生成合并为单阶段

**问题**: 原实现提取和生成分开调用，成本高、延迟大

**解决方案**: 合并为单阶段，减少 API 调用次数

**文件**: `worker/pipeline/extract_v2.py`

**主要功能**:
- `extract_and_generate()`: 单阶段提取+生成（纯文本）
- `extract_and_generate_with_vision()`: 单阶段提取+生成（支持多模态）

**Prompt 设计**:
```
你是试卷结构化助手。请从原始内容中直接提取并生成结构化的试卷文档。

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
```

---

### 任务处理优化

**文件**: `worker/tasks_v2.py`

**升级点**:
1. 使用预处理 v2（PyMuPDF + 多模态LLM）
2. 合并提取+生成为单阶段
3. 按内容边界分块 + 滑动窗口
4. 优化超时和错误处理

**主要功能**:
- `process_paper_v2()`: 优化后的 Celery 任务
- `_preprocess_async()`: 异步预处理
- `_generate_local_fallback()`: 本地生成 HTML（兜底方案）

---

### 配置更新

**文件**: `worker/pyproject.toml`

**依赖变更**:
- 移除: `pypdf`, `pytesseract`
- 保留: `pymupdf`, `python-docx`, `Pillow`

**文件**: `docker/Dockerfile.worker`

**系统依赖变更**:
- 移除: `tesseract-ocr`, `tesseract-ocr-chi-sim`, `tesseract-ocr-chi-tra`
- 保留: `build-essential`, `libpq-dev`, `curl`

**文件**: `worker/celery_app.py`

**配置更新**:
- 新增任务模块: `worker.tasks_v2`
- 新增任务路由: `worker.tasks_v2.process_paper_v2`

---

### 后端处理流程更新

**文件**: `backend/app/processing.py`

**新增 v2 处理函数**:
- `_preprocess_pdf_v2()`: PDF 预处理 v2
- `_split_by_content_boundaries()`: 按内容边界分块
- `_split_with_overlap()`: 带滑动窗口的分块
- `_extract_and_generate_single_stage()`: 单阶段提取+生成
- `process_paper_v2()`: 优化后的完整处理流程

**文件**: `backend/app/queue.py`

**任务队列更新**:
- 优先使用 v2 任务
- 降级到 v1 任务（兼容性）

---

## 测试验证

### 待测试项目

1. **PyMuPDF 文本提取质量**: 对比 pypdf 的提取效果
2. **多模态LLM识别**: 扫描件 PDF 的识别准确率
3. **跨页题目完整性**: 验证滑动窗口是否保留上下文
4. **单阶段提取+生成**: 验证 API 调用次数和成本
5. **超时优化**: 验证处理时间是否缩短

### 测试命令

```bash
# 进入 worker 目录
cd worker

# 运行测试脚本
python -m pytest tests/test_v2_pipeline.py -v

# 或者手动测试
python -c "
from pipeline.preprocess_v2 import preprocess_pdf_v2
from pipeline.extract_v2 import extract_and_generate

# 测试预处理
with open('test.pdf', 'rb') as f:
    content = f.read()
    result = preprocess_pdf_v2(content)
    print(f'预处理完成: {result[\"page_count\"]} 页')
"
```

---

## 预期效果

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 文本提取质量 | 低（pypdf） | 高（PyMuPDF + 多模态LLM） |
| 跨页题目完整性 | 被切断 | 完整保留 |
| API 调用次数 | 58次（提取）+ N次（生成） | 1-3次（合并） |
| Token 成本 | 高 | 降低60-80% |
| 用户等待时间 | 长（900秒） | 短（预期120-180秒） |
| OCR 准确率 | 低（Tesseract） | 高（多模态LLM） |

---

## 后续步骤

1. **部署测试**: 将代码部署到服务器进行测试
2. **性能测试**: 对比优化前后的处理时间
3. **成本测试**: 验证 API 调用成本是否降低
4. **兼容性测试**: 确保 v1 和 v2 流程可以并存
5. **文档更新**: 更新 README 和 API 文档
