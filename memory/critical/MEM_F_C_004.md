---
id: MEM_F_C_004
title: socket recv 循环必须精确捕获三类异常，禁用 except Exception
severity: CRITICAL
created: 2026-03-03
confidence: high
validated_by: sdd-tinyhttpd 2×2 对照实验（加载组全部预防，未加载组全部未命中）
---

## 规则
TCP 服务器 recv 循环必须使用：
```python
except (socket.timeout, ConnectionResetError, OSError):
    pass
```
**禁止** `except Exception` 吞掉 socket 错误。

## 原因
服务器 close() 后对端继续 recv() 收到 ECONNRESET，Python 抛出 ConnectionResetError。
`except Exception` 虽能捕获，但掩盖正常关闭和真实错误的语义区别，高并发下静默吞掉真实异常。

## 反例
```python
except Exception:   # ❌ 掩盖语义，高并发 Bug 静默
    pass
```

## 正例
```python
try:
    data = conn.recv(4096)
except (socket.timeout, ConnectionResetError, OSError):
    break   # 正常：连接重置 / 超时 / socket 关闭
except Exception:
    logger.error("unexpected recv error", exc_info=True)
    break
```
