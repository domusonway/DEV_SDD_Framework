# SPEC: request_parser
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
从 socket 连接中读取 HTTP 请求数据，解析为结构化字典。

---

## 接口定义

```python
def parse_request(conn: socket.socket) -> dict:
    """
    从 socket 读取并解析 HTTP/1.0 请求。

    Args:
        conn: 已建立的客户端 socket 连接

    Returns:
        包含请求信息的字典（见接口表）

    Raises:
        ValueError: 请求格式不合法（无法解析请求行）
        ConnectionError: 连接在读取过程中关闭
    """
```

---

## 接口表

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | conn | socket.socket | 已建立的客户端连接 |
| 输出 | method | **str** | HTTP 方法：GET / POST |
| 输出 | path | **str** | 请求路径，不含 query string |
| 输出 | query_string | **str** | query string（无则为空字符串） |
| 输出 | version | **str** | HTTP 版本：HTTP/1.0 或 HTTP/1.1 |
| 输出 | headers | **dict[str, str]** | 请求头，key 小写 |
| 输出 | body | **bytes** | 请求体（GET 为 b''） |

---

## 行为规格

### 正常路径（GET）
```
输入 socket 数据: b"GET /index.html HTTP/1.0\r\nHost: localhost\r\n\r\n"
输出: {
    "method": "GET",
    "path": "/index.html",
    "query_string": "",
    "version": "HTTP/1.0",
    "headers": {"host": "localhost"},
    "body": b""
}
```

### 带 query string 的 GET
```
输入: b"GET /search?q=hello&page=1 HTTP/1.0\r\n\r\n"
输出 path: "/search"
输出 query_string: "q=hello&page=1"
```

### 空连接（b''）
```
recv 立即返回 b'' → 抛出 ConnectionError
```

---

## 依赖关系
- 依赖: 无（stdlib socket）
- 被依赖: server 模块

---

## 验收标准
- [ ] GET 请求解析正确
- [ ] query string 分离正确
- [ ] 请求头 key 统一小写
- [ ] b'' 连接关闭正确处理（MEM_F_C_005）
