"""最小 Anthropic 兼容 LLM 客户端（仅用标准库，便于独立测试）。

对应第 1~2 层的基础调用能力。
"""
import json
import logging
import os
import re
import time
import urllib.request
from typing import Optional

API_URL = "https://api.longcat.chat/anthropic/v1/messages"
API_KEY = os.environ.get("LONGCAT_API_KEY")
MODEL = "LongCat-2.0"

logger = logging.getLogger("tier2.client")


def chat(
    messages: list,
    *,
    max_tokens: int = 32000,
    temperature: float = 0.2,
    system: Optional[str] = None,
) -> str:
    """调用 LongCat（Anthropic 兼容接口），返回文本内容。

    messages: [{"role": "user"|"assistant", "content": str}, ...]
    """
    if not API_KEY:
        raise RuntimeError("请设置 LONGCAT_API_KEY 环境变量后再调用 LongCat")
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    if system:
        payload["system"] = system

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": API_KEY,
            "Authorization": f"Bearer {API_KEY}",
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    started = time.monotonic()
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    text = ""
    for block in data.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            text += block.get("text", "")
    logger.info(
        "LLM completed in %.1fs; %d chars; stop_reason=%s; usage=%s",
        time.monotonic() - started,
        len(text),
        data.get("stop_reason"),
        data.get("usage"),
    )
    return text


def chat_json(
    messages: list,
    *,
    max_tokens: int = 32000,
    temperature: float = 0.2,
    system: Optional[str] = None,
) -> dict:
    """调用 chat 并稳定解析出 JSON 对象（容错：去 markdown、截首尾）。"""
    if system is None:
        system = "你必须只返回一个合法 JSON 对象，不要输出 Markdown 或解释文字。"
    else:
        system = system + "\n\n你必须只返回一个合法 JSON 对象，不要输出 Markdown 或解释文字。"
    raw = chat(messages, max_tokens=max_tokens, temperature=temperature, system=system)
    return _extract_json(raw)


def _repair_json_escapes(raw: str) -> str:
    """补齐模型在 LaTeX 命令中漏写的 JSON 反斜杠。

    宽松 JSON 解析会把 LaTeX 的 \\frac 误作 JSON 的 \\f（换页符），因此必须先修复。
    """
    # \\frac / \\bar / \\times 等看似以合法 JSON 转义开头，实际是 LaTeX 命令。
    repaired = re.sub(r"\\([bfrt])(?=[A-Za-z])", r"\\\\\1", raw)
    # 不是四位十六进制数的 \\u 是 LaTeX 命令而非 JSON Unicode 转义。
    repaired = re.sub(r"\\u(?![0-9a-fA-F]{4})", r"\\\\u", repaired)
    # 其余非 JSON 转义，例如 \\cap、\\sum。
    return re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", repaired)


def _extract_json(raw: str) -> dict:
    raw = raw.strip()
    # json.loads 会把 \\frac 中的 \\f 当作换页符而不报错，因此必须先修复。
    raw = _repair_json_escapes(raw)
    # 去掉 ```json ... ``` 围栏
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0:
        raise ValueError("LLM 返回中没有 JSON 对象")
    if end <= start:
        raise ValueError(
            "LLM JSON 输出疑似被截断；请缩短单题解答或降低题目数量后重试"
        )
    raw = raw[start : end + 1]
    try:
        return json.loads(raw)
    except json.JSONDecodeError as standard_error:
        repaired = raw
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            # 兜底处理尾逗号、单引号等非标准 JSON；公式已在上一步保护。
            try:
                import demjson3
                parsed = demjson3.decode(repaired, strict=False)
            except (ImportError, ValueError, TypeError):
                raise standard_error
            if not isinstance(parsed, dict):
                raise ValueError("LLM 返回的 JSON 根节点不是对象")
            return parsed


if __name__ == "__main__":
    out = chat([{"role": "user", "content": "用一句话介绍 TCP"}])
    print("TEST:", out[:120])
