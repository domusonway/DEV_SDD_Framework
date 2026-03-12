---
id: MEM_D_HTTP_001
domain: http
title: HTTP/1.0 每次请求后关闭连接；1.1 默认 Keep-Alive
created: 2026-03-03
---

## 规则
- HTTP/1.0：每次请求响应后**服务器主动关闭连接**
- HTTP/1.1：默认 Keep-Alive，`Connection: close` 才关闭

## 实现要点
```python
def should_keep_alive(request: dict) -> bool:
    version = request.get("version", "HTTP/1.0")
    connection = request.get("headers", {}).get("Connection", "").lower()
    if version == "HTTP/1.0":
        return connection == "keep-alive"
    else:  # HTTP/1.1
        return connection != "close"
```

## 常见错误
服务器实现 HTTP/1.1 但每次都关闭连接 → curl/浏览器不报错，但性能差，ab 压测连接数暴增。
