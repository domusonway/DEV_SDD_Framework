---
id: MEM_F_I_007
title: 共享状态用 RLock，不用 Lock（防同线程递归死锁）
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd server 模块
---

## 规则
多线程服务器中，保护共享状态（连接计数、路由表等）用 `threading.RLock()`，不用 `threading.Lock()`。

## 原因
同一线程可能在持锁时调用另一个也需要该锁的函数（递归加锁）。
`Lock` 会死锁，`RLock`（可重入锁）允许同线程多次 acquire。

## 正例
```python
class Server:
    def __init__(self):
        self._lock = threading.RLock()   # ✅ 可重入
        self._conn_count = 0

    def _increment(self):
        with self._lock:
            self._conn_count += 1

    def handle_new_connection(self, conn):
        with self._lock:            # 已持锁
            self._increment()       # 再次 acquire → RLock 不死锁
```
