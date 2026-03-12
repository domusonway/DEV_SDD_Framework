---
id: MEM_F_I_001
title: 集成测试客户端也须捕获 ConnectionResetError
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd
---

## 规则
集成测试中的 HTTP 客户端在收到响应后，服务器可能已关闭连接。
客户端的 `recv()` 需捕获 `ConnectionResetError`，否则测试本身报错，干扰失败分析。

## 反例
```python
# ❌ 测试客户端无保护
conn.sendall(req)
resp = conn.recv(4096)   # 服务器已关闭 → ConnectionResetError 在测试层爆
assert b"200 OK" in resp
```

## 正例
```python
conn.sendall(req)
try:
    resp = conn.recv(4096)
except ConnectionResetError:
    resp = b""   # 服务器关闭，部分响应已收到
assert b"200 OK" in resp
```
