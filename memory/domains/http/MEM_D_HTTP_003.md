---
id: MEM_D_HTTP_003
domain: http
title: Content-Length 必须与 body 字节数精确匹配
created: 2026-03-03
---

## 规则
`Content-Length` 头的值必须等于 body 的**字节数**（不是字符数）。
中文/多字节字符 `len(str)` ≠ `len(bytes)`，必须用 `len(body_bytes)`。

## 反例 → 后果
```python
body = "<h1>你好</h1>"
# ❌ 字符数
headers["Content-Length"] = len(body)        # 10（字符）
# ✅ 字节数
body_bytes = body.encode("utf-8")
headers["Content-Length"] = len(body_bytes)  # 16（字节）
```
→ Content-Length 不匹配 → 浏览器截断响应或等待超时。

## 检查
```python
assert len(body_bytes) == int(response_headers["Content-Length"])
```
