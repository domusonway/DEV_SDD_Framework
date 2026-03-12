---
id: MEM_F_I_002
title: socketpair 比真实 socket 更适合单元测试
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd
---

## 规则
单元测试网络模块时，优先使用 `socket.socketpair()` 代替 MockSocket。
socketpair 是真实 socket，不需要 bind/listen/accept，双端可直接读写。

## 为什么不用 Mock
MockSocket 要手动模拟 `recv`、`sendall` 等行为，容易掩盖隐式契约（见 MEM_F_I_003）。

## 正例
```python
def test_handle_request():
    server_sock, client_sock = socket.socketpair()
    client_sock.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")
    handle_request(server_sock)   # 真实 socket，真实 IO
    resp = client_sock.recv(4096)
    assert b"200 OK" in resp
    server_sock.close()
    client_sock.close()
```
