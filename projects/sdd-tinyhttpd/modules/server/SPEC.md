# SPEC: server
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
HTTP 服务器主循环：监听端口，Accept 连接，分发请求给处理器。

---

## 接口定义

```python
class HTTPServer:
    def __init__(self, host: str = "0.0.0.0", port: int = 8080,
                 htdocs_root: str = "htdocs"):
        ...

    def start(self) -> None:
        """启动服务器，阻塞运行"""

    def stop(self) -> None:
        """优雅关闭服务器"""
```

---

## 行为规格

### 启动
- 创建 TCP socket，设置 SO_REUSEADDR
- bind + listen(10)
- 每个连接启动新线程（threading.Thread）处理

### 请求处理流程（每线程）
```
1. parse_request(conn) → request
2. route(request["path"], htdocs_root) → handler_type
3. if handler_type == "static": handle_static(...)
   if handler_type == "cgi":    handle_cgi(...)
   if handler_type == "not_found": build_response(404, ...)
4. conn.sendall(response_bytes)
5. conn.close()
```

### 异常处理
- recv 异常：`except (socket.timeout, ConnectionResetError, OSError)` → 关闭连接（MEM_F_C_004）
- 未预期异常：记录日志，返回 500，关闭连接

### 关闭
- 停止 Accept 新连接
- 等待当前处理线程完成（超时 5 秒）
- 关闭 server socket

---

## 接口表

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| host | **str** | "0.0.0.0" | 监听地址 |
| port | **int** | 8080 | 监听端口 |
| htdocs_root | **str** | "htdocs" | 静态文件根目录 |

---

## 依赖
- 依赖: request_parser, response, router, static_handler, cgi_handler
- 依赖: socket, threading（stdlib）
