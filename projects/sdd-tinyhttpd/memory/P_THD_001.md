---
id: P_THD_001
project: sdd-tinyhttpd
title: socket.sendall() 收到 str 而非 bytes → TypeError
severity: BUG_FIX
created: 2026-03-03
promoted_to_framework: MEM_F_C_002（SPEC dtype 要求）
---

## 症状
```
TypeError: a bytes-like object is required, not 'str'
  File "modules/server/server.py", line 42, in handle_request
    conn.sendall(response)
```

## 根因
`response` 模块的 `build_response()` 返回 `str`，而 `socket.sendall()` 只接受 `bytes`。
SPEC 未明确返回类型（只写了"返回响应内容"），导致实现者返回了 str。

## 修复
```python
# ❌ 修复前
def build_response(status, headers, body):
    return f"HTTP/1.0 {status}\r\n..." + body

# ✅ 修复后
def build_response(status: int, headers: dict, body: bytes) -> bytes:
    header_str = f"HTTP/1.0 {status} OK\r\n..."
    return header_str.encode("utf-8") + body
```

## 预防
SPEC 接口表必须明确 dtype：`| 返回值 | bytes | HTTP 完整响应 |`
→ 已提升为框架 MEM_F_C_002
