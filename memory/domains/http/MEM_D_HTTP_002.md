---
id: MEM_D_HTTP_002
domain: http
title: 响应头必须用 \r\n 分隔，头部结束用 \r\n\r\n
created: 2026-03-03
---

## 规则
HTTP/1.x 协议规定行结束符为 `\r\n`（CRLF），不是 `\n`（LF）。
头部与 body 之间必须有空行，即连续两个 `\r\n`。

## 反例 → 后果
```python
# ❌ 只用 \n
response = "HTTP/1.1 200 OK\nContent-Type: text/html\n\n<html>"
```
→ 现代浏览器通常能容忍，但 curl `--strict` 报错，E2E 测试失败。

## 正例
```python
# ✅ CRLF
headers = [
    "HTTP/1.1 200 OK",
    "Content-Type: text/html; charset=utf-8",
    f"Content-Length: {len(body)}",
    "",   # 空行，产生 \r\n\r\n
    ""
]
response = "\r\n".join(headers).encode() + body
```
