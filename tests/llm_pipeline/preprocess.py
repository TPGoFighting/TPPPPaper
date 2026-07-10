"""第 1 层：文本预处理层。

策略（两层兜底）：
  Tier 1a: PDF 内嵌文本层（fitz 直接提取，最快）
  Tier 1b: 若无文本层 → Tesseract OCR（扫描件）
  Tier 1c: 若 OCR 仍失败 → 大模型视觉识别（需 supports_vision 的模型）

注意：当前 LongCat-2.0 不支持视觉，Tier 1c 在本部署中不可用；
      代码保留该分支，配置视觉模型后自动启用。
"""
import base64
import io
import logging

logger = logging.getLogger("tier1.preprocess")


def preprocess_pdf(content: bytes) -> dict:
    """返回 {'pages': [...], 'page_count': int, 'engine': str}。"""
    pages = _extract_text_layer(content)
    engine = "text_layer"

    # Tier 1b: OCR 兜底
    need_ocr = [p for p in pages if len(p.get("text", "").strip()) < 30]
    if need_ocr:
        logger.info(f"Tier 1b: 对 {len(need_ocr)} 个低文本页做 OCR")
        ocr_pages = _ocr_pages(content, need_ocr)
        # 只有 OCR 实际渲染并写回页面时才标记为 ocr；低文本页原本残留的
        # 少量文本不能说明 OCR 已成功，避免依赖缺失时产生误导性日志。
        if any(p.get("image_b64") for p in ocr_pages):
            engine = "ocr"
        still_empty = [p for p in ocr_pages if not p.get("text", "").strip()]
        if still_empty:
            # Tier 1c: 视觉兜底（需视觉模型，当前部署跳过）
            logger.warning(f"Tier 1c: {len(still_empty)} 页 OCR 仍为空，需视觉模型（当前不可用）")

    return {"pages": pages, "page_count": len(pages), "engine": engine}


def _extract_text_layer(content: bytes) -> list[dict]:
    try:
        import fitz

        doc = fitz.open(stream=content, filetype="pdf")
        out = []
        for i, page in enumerate(doc):
            out.append({
                "page": i + 1,
                "text": page.get_text() or "",
                "image_b64": None,
            })
        doc.close()
        return out
    except Exception as e:
        logger.warning(f"文本层提取失败: {e}")
        return [{"page": 1, "text": "", "image_b64": None}]


def _ocr_pages(content: bytes, pages: list[dict]) -> list[dict]:
    try:
        import fitz
        import pytesseract
        from PIL import Image

        doc = fitz.open(stream=content, filetype="pdf")
        mat = fitz.Matrix(2, 2)
        for p in pages:
            idx = p["page"] - 1
            if idx < 0 or idx >= len(doc):
                continue
            pix = doc[idx].get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = img.convert("L").point(lambda v: 0 if v < 140 else 255)
            text = pytesseract.image_to_string(img, lang="chi_sim+eng", config="--psm 6")
            p["text"] = text.strip()
            p["image_b64"] = base64.b64encode(pix.tobytes("png")).decode()
        doc.close()
    except Exception as e:
        logger.error(f"OCR 失败: {e}")
    return pages


def _ocr_via_vision(content: bytes, pages: list[dict], vision_fn) -> list[dict]:
    """Tier 1c: 用视觉模型识别（vision_fn(image_b64, mime) -> str）。"""
    import fitz

    doc = fitz.open(stream=content, filetype="pdf")
    mat = fitz.Matrix(2, 2)
    for p in pages:
        idx = p["page"] - 1
        if idx < 0 or idx >= len(doc):
            continue
        pix = doc[idx].get_pixmap(matrix=mat)
        b64 = base64.b64encode(pix.tobytes("png")).decode()
        try:
            p["text"] = vision_fn(b64, "image/png")
        except Exception as e:
            logger.error(f"视觉识别失败 p{p['page']}: {e}")
    doc.close()
    return pages
