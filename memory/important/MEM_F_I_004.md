---
id: MEM_F_I_004
title: C int fd → Python socket 对象，size 参数省略
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd（从 tinyhttpd C 重构）
---

## 规则
将 C 代码迁移到 Python 时，函数签名中的 `int fd`（文件描述符）替换为 `socket.socket` 对象。
`send()`/`recv()` 调用中的 `size` 参数通常省略（Python 默认合理值），但 `recv(n)` 的 n 需保留。

## 对照
```c
// C
void handle_request(int cfd) {
    char buf[1024];
    recv(cfd, buf, sizeof(buf), 0);
    send(cfd, response, strlen(response), 0);
}
```

```python
# Python
def handle_request(conn: socket.socket) -> None:
    data = conn.recv(4096)
    conn.sendall(response)   # sendall 保证全部发送
```

## 注意
- C `send()` 返回发送字节数，可能不完整；Python 用 `sendall()` 代替
- C 手动管理 fd；Python socket 对象有 `close()` 方法，推荐用 `with` 语句
