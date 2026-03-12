# SPEC: response
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
构建符合 HTTP/1.0 规范的响应 bytes。

---

## 接口定义

```python
def build_response(
    status_code: int,
    body: bytes,
    content_type: str = "text/html; charset=utf-8",
    extra_headers: dict = None,
) -> bytes:
    """
    构建完整的 HTTP/1.0 响应。

    Returns:
        bytes: 完整 HTTP 响应，含状态行 + 头部 + 空行 + body
    """
```

---

## 接口表

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | status_code | **int** | HTTP 状态码：200/404/500 等 |
| 输入 | body | **bytes** | 响应体 |
| 输入 | content_type | **str** | Content-Type 值，默认 text/html |
| 输入 | extra_headers | **dict[str,str]** | 额外响应头，可选 |
| 输出 | 返回值 | **bytes** | 完整 HTTP 响应（重要：必须是 bytes）|

---

## 行为规格

### 200 OK
```
输入: status_code=200, body=b"<h1>Hello</h1>"
输出: b"HTTP/1.0 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 14\r\n\r\n<h1>Hello</h1>"
```

### 404
```
输入: status_code=404, body=b"Not Found"
输出含: b"HTTP/1.0 404 Not Found\r\n..."
```

### Content-Length 精确
Content-Length 值 == len(body)，中文按 UTF-8 字节数计（MEM_D_HTTP_003）

### CRLF 分隔
所有头部行用 \r\n 分隔，头部结束用 \r\n\r\n（MEM_D_HTTP_002）

---

## 依赖关系
- 依赖: 无
- 被依赖: static_handler, cgi_handler
