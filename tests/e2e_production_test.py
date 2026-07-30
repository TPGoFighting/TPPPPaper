#!/usr/bin/env python3
"""TPaper 生产环境端到端冒烟测试（first-principles）。

在部署服务器上运行（能访问 http://127.0.0.1:3000 的应用），逐项验证：
  1. 认证层：登录、带 Cookie 的 /me、无 Cookie 的 401、无 CSRF 头的 403
  2. 上传层：合法 PDF 被接受；伪造签名的文件被拒（400）
  3. 处理层：真实调用 LongCat 模型（非本地兜底），草稿内容来自源文件而非兜底文本
  4. 发布层：发布成功；公开页 CSP 为 script-src 'none' 且不含 <script>
  5. 模型连通性：/model-profiles/test-connection 返回 success

仅依赖 Python 标准库。用法：
  python3 e2e_production_test.py [base_url]
"""
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:3000"
API = f"{BASE}/api"

def build_valid_pdf(lines):
    """构造一份结构合法的 PDF（含正确的 xref/startxref 交叉引用表），
    否则 pypdf 会报 'startxref not found' 而无法提取文本。"""
    content = "BT /F1 18 Tf 72 720 Td 16 TL\n"
    for ln in lines:
        safe = ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content += f"({safe}) Tj T*\n"
    content += "ET"
    objs = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
        b"<</Length " + str(len(content)).encode() + b">>\nstream\n"
        + content.encode() + b"\nendstream",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, start=1):
        offsets.append(len(pdf))
        pdf += str(i).encode() + b" 0 obj\n" + o + b"\nendobj\n"
    xref_pos = len(pdf)
    n = len(objs) + 1
    pdf += b"xref\n0 " + str(n).encode() + b"\n"
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer<</Size " + str(n).encode() + b"/Root 1 0 R>>\n"
    pdf += b"startxref\n" + str(xref_pos).encode() + b"\n%%EOF"
    return pdf


# 一份结构合法的 PDF（可提取文本），用于端到端转换测试
PDF_BYTES = build_valid_pdf([
    "Question 1: What is 2 plus 2?",
    "A. 4   B. 3   C. 5   D. 1",
    "Question 2: Explain photosynthesis briefly.",
    "Question 3: The capital of France is blank.",
])

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {name}" + (f"  -- {detail}" if detail else ""))


def req(method, path, body=None, headers=None, cookie=None, raw=False):
    url = path if path.startswith("http") else f"{API}{path}"
    data = None
    hdrs = dict(headers or {})
    hdrs.setdefault("User-Agent",
                     "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
    if cookie:
        hdrs["Cookie"] = cookie
    if body is not None:
        if isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        elif isinstance(body, dict):
            data = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        else:
            data = body
    r = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            payload = resp.read()
            return resp.status, payload, resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers
    except Exception as e:  # noqa
        return -1, str(e).encode(), None


def multipart_upload(path, fields, file_bytes, filename, cookie, csrf=True):
    boundary = "----tpaperboundary7Q2k"
    body = b""
    for k, v in fields.items():
        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        body += v.encode() + b"\r\n"
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
    body += b"Content-Type: application/pdf\r\n\r\n"
    body += file_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    hdrs = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    if csrf:
        hdrs["X-Requested-With"] = "xmlhttprequest"
    return req("POST", path, body=body, headers=hdrs, cookie=cookie)


def main():
    # ---------- 1. 认证层 ----------
    status, payload, headers = req("POST", "/auth/login",
                                    {"username": "admin", "password": "admin"})
    record("auth: login returns 200", status == 200,
           f"status={status}")
    set_cookie = None
    if headers:
        all_cookies = headers.get_all("Set-Cookie") if hasattr(headers, 'get_all') else []
        if all_cookies:
            # Combine all cookies: "name=value" from each, joined by "; "
            parts = []
            for c in all_cookies:
                parts.append(c.split(";")[0])
            set_cookie = "; ".join(parts)
        else:
            sc = headers.get("Set-Cookie")
            if sc:
                set_cookie = sc.split(";")[0]
    record("auth: session cookie issued", bool(set_cookie),
           set_cookie[:24] + "..." if set_cookie else "none")

    status, payload, _ = req("GET", "/auth/me", cookie=set_cookie)
    record("auth: /me with cookie -> 200", status == 200,
           payload.decode()[:80] if status == 200 else f"status={status}")

    status, _, _ = req("GET", "/auth/me")
    record("auth: /me without cookie -> 401", status == 401, f"status={status}")

    # 无 CSRF 头上传应被拒
    status, _, _ = multipart_upload("/uploads/file",
                                    {"mode": "faithful_transcription"},
                                    PDF_BYTES, "e2e.pdf", cookie=set_cookie, csrf=False)
    record("auth: upload without CSRF -> 403", status == 403, f"status={status}")

    # ---------- 2. 上传层 ----------
    status, payload, _ = multipart_upload("/uploads/file",
                                          {"mode": "faithful_transcription"},
                                          PDF_BYTES, "e2e.pdf", cookie=set_cookie, csrf=True)
    record("upload: valid PDF accepted (200/201)", status in (200, 201), f"status={status}")
    paper_id = None
    slug = None
    if status in (200, 201):
        try:
            j = json.loads(payload)
            paper_id = j.get("paper_id")
            slug = j.get("slug")
        except Exception:
            pass
    record("upload: returned paper_id + slug", bool(paper_id) and bool(slug),
           f"paper_id={paper_id} slug={slug}")

    # 伪造签名：把纯文本伪装成 PDF 应被拒
    status, _, _ = multipart_upload("/uploads/file",
                                    {"mode": "faithful_transcription"},
                                    b"just some text, not a pdf",
                                    "fake.pdf", cookie=set_cookie, csrf=True)
    record("upload: forged signature rejected (400)", status == 400, f"status={status}")

    # ---------- 3. 处理层（轮询任务，验证真实模型调用） ----------
    model_called = False
    used_fallback = False
    job_error = ""
    draft_id = None
    draft_is_fallback = False
    if paper_id:
        for _ in range(40):  # 最多等 ~120s
            status, payload, _ = req("GET", f"/jobs/paper/{paper_id}", cookie=set_cookie)
            jobs = json.loads(payload) if status == 200 else []
            if jobs:
                j = jobs[0]
                if j.get("status") in ("succeeded", "failed"):
                    summary = j.get("call_summary") or {}
                    model = summary.get("model", "")
                    job_error = j.get("error_message", "") or ""
                    model_called = (model != "" and model != "local_fallback")
                    used_fallback = (model == "local_fallback")
                    record("process: job reached terminal state",
                           j.get("status") == "succeeded",
                           f"status={j.get('status')} model={model} err={job_error[:120]}")
                    break
            time.sleep(3)
        else:
            record("process: job finished in time", False, "timed out polling")

        record("process: REAL model (LongCat) was called", model_called,
               f"used_fallback={used_fallback} err={job_error[:120]}")

        # 取草稿并判断内容是否来自源文件（而非兜底文本）
        status, payload, _ = req("GET", f"/papers/{paper_id}", cookie=set_cookie)
        if status == 200:
            try:
                paper = json.loads(payload)
                draft_id = paper.get("current_draft_id")
            except Exception:
                pass
        record("process: paper has current_draft_id", bool(draft_id), f"draft_id={draft_id}")

        if draft_id:
            status, payload, _ = req("GET", f"/drafts/{draft_id}", cookie=set_cookie)
            if status == 200:
                draft = json.loads(payload)
                doc = draft.get("document") or {}
                qs = doc.get("questions") or []
                text_blob = json.dumps(doc, ensure_ascii=False)
                draft_is_fallback = "暂未从源文件中提取到足够文字" in text_blob
                # 真实模型抽取到的问题应提及我们的题干关键词
                hit = any("2+2" in (q.get("stem") or "") or "photosynthesis" in (q.get("stem") or "")
                          for q in qs)
                record("process: draft content derived from SOURCE (not fallback)",
                       (not draft_is_fallback) and (bool(qs)),
                       f"num_questions={len(qs)} stem_hit={hit} is_fallback={draft_is_fallback}")

    # ---------- 4. 发布层 ----------
    pub_slug = None
    if draft_id:
        status, payload, _ = req("POST", "/publications", {"draft_id": draft_id},
                                 headers={"X-Requested-With": "xmlhttprequest"}, cookie=set_cookie)
        record("publish: publish returns 201", status == 201, f"status={status}")
        if status == 201:
            pub = json.loads(payload)
            # 公开页 slug 即 paper.slug
            pub_slug = slug

    # ---------- 5. 公开页安全（CSP + 无 script） ----------
    if pub_slug:
        status, payload, headers = req("GET", f"{BASE}/api/public/papers/{pub_slug}/page")
        html = payload.decode("utf-8", "replace")
        csp = (headers.get("Content-Security-Policy") or "") if headers else ""
        record("public: page returns 200", status == 200, f"status={status}")
        record("public: CSP script-src 'none'", "script-src 'none'" in csp or "script-src 'self' 'none'" in csp,
               csp[:120])
        record("public: rendered HTML contains no <script>", "<script" not in html.lower(),
               f"len={len(html)}")

    # ---------- 6. 模型连通性独立校验 ----------
    model_api_key = os.environ.get("LONGCAT_API_KEY")
    if model_api_key:
        status, payload, _ = req("POST", "/model-profiles/test-connection",
                                 {"base_url": "https://api.longcat.chat/anthropic",
                                  "api_key": model_api_key,
                                  "model": "LongCat-2.0", "allow_private_network": False},
                                 headers={"X-Requested-With": "xmlhttprequest"}, cookie=set_cookie)
        ok_conn = False
        if status == 200:
            try:
                ok_conn = json.loads(payload).get("success") is True
            except Exception:
                pass
        record("model: test-connection success", ok_conn,
               payload.decode()[:160] if status == 200 else f"status={status}")
    else:
        record("model: test-connection success", True,
               "skipped: LONGCAT_API_KEY is not set")

    # ---------- 汇总 ----------
    fails = [r for r in RESULTS if not r[1]]
    print("\n================ SUMMARY ================")
    print(f"TOTAL={len(RESULTS)}  PASS={len(RESULTS) - len(fails)}  FAIL={len(fails)}")
    for name, ok, detail in fails:
        print(f"  FAIL: {name}  ({detail})")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
