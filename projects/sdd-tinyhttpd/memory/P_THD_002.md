---
id: P_THD_002
project: sdd-tinyhttpd
title: recv 循环未检查 b''，客户端关闭后死循环 CPU 100%
severity: BUG_FIX
created: 2026-03-03
promoted_to_framework: MEM_F_C_005（recv b'' 检查）
---

## 症状
客户端关闭连接后，服务器线程 CPU 占用跳至 100%，持续不降。
`top` 显示 python3 进程单核跑满。

## 根因
```python
# ❌ 问题代码
def read_request(conn):
    buf = b""
    while True:
        chunk = conn.recv(1)   # 客户端关闭后永远返回 b''
        buf += chunk           # 无限追加空 bytes，死循环
```

`conn.recv()` 在对端关闭时返回 `b''`（空 bytes），不抛异常，不返回 None。
未检查 `if not data` 导致无限循环。

## 修复
```python
# ✅ 修复后
def read_request(conn):
    buf = b""
    while True:
        data = conn.recv(4096)
        if not data:   # b'' = 对端已关闭
            break
        buf += data
        if b"\r\n\r\n" in buf:   # HTTP 头部结束
            break
    return buf
```

## 预防
所有 recv 循环必须包含 `if not data: break`。
→ 已提升为框架 MEM_F_C_005
