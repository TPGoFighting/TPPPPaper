"""编排脚本：串联 第1层(预处理) → 第2层(理解) → 第3层(渲染) → 第5层(发布)。

用法：
  python run.py <pdf_path> [--mode lecture_to_quiz|faithful_transcription]

第4层（可视化编辑器）为前端能力，本脚本仅产出静态 HTML 供其加载。
"""
import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from preprocess import preprocess_pdf
from understand import understand
from render import render, publish

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("run")


def run(pdf_path: str, mode: str, out_path: str) -> dict:
    with open(pdf_path, "rb") as f:
        content = f.read()

    # 第 1 层
    pre = preprocess_pdf(content)
    logger.info(f"预处理完成：引擎={pre['engine']}, 页数={pre['page_count']}")

    # 第 2 层
    doc = understand(pre["pages"], mode=mode)
    logger.info(f"理解完成：{len(doc.get('questions', []))} 题")

    # 第 3 层
    html_str = render(doc)

    # 第 5 层（发布托管雏形）
    publish(html_str, out_path)
    logger.info(f"已发布到：{out_path}")
    return doc


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf", help="PDF 路径")
    ap.add_argument("--mode", default="lecture_to_quiz")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "output.html"))
    args = ap.parse_args()
    run(args.pdf, args.mode, args.out)
