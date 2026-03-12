---
id: MEM_F_C_005
title: recv 返回 b'' 表示连接关闭，必须检查否则死循环
severity: CRITICAL
created: 2026-03-03
confidence: high
validated_by: sdd-tinyhttpd, mini-redis
---

## 规则
`conn.recv(n)` 在对端关闭连接时返回 `b''`，不是 None，不抛异常。
不检查会导致无限循环，CPU 100%。

## 反例 → 后果
```python
while True:
    chunk = conn.recv(1)   # 关闭后永远返回 b''
    buf += chunk           # 死循环，CPU 100%
```

## 正例
```python
while True:
    data = conn.recv(4096)
    if not data:            # b'' 是 falsy，连接已关闭
        break
    buf += data
```

## 与 C 的区别
C: `recv()` 返回 `0`（int）。Python: 返回 `b''`（空 bytes），用 `if not data` 判断。
