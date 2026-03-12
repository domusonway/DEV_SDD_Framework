# HTTP 领域记忆 · 索引
> 加载时机：任何涉及 HTTP 协议实现的任务

---

## 快速规则表（标题即规则）

| ID | 规则 | 文件 |
|----|------|------|
| MEM_D_HTTP_001 | HTTP/1.0 每次请求后关闭连接；1.1 默认 Keep-Alive | [→](MEM_D_HTTP_001.md) |
| MEM_D_HTTP_002 | 响应头必须用 \r\n 分隔，头部结束用 \r\n\r\n | [→](MEM_D_HTTP_002.md) |
| MEM_D_HTTP_003 | Content-Length 必须与 body 字节数精确匹配 | [→](MEM_D_HTTP_003.md) |
| MEM_D_HTTP_004 | CGI 环境变量：QUERY_STRING/REQUEST_METHOD/CONTENT_LENGTH 必须设置 | [→](MEM_D_HTTP_004.md) |

---

## 加载建议

```
静态文件服务    → MEM_D_HTTP_001, MEM_D_HTTP_002, MEM_D_HTTP_003
CGI 实现        → MEM_D_HTTP_004（+ 以上三条）
请求解析        → MEM_D_HTTP_002
压力测试 / 并发 → MEM_D_HTTP_001（连接管理策略影响并发数）
```
