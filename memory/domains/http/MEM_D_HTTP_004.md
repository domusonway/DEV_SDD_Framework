---
id: MEM_D_HTTP_004
domain: http
title: CGI 环境变量：QUERY_STRING/REQUEST_METHOD/CONTENT_LENGTH 必须设置
created: 2026-03-03
---

## 规则
执行 CGI 脚本前，必须在 subprocess 的 `env` 字典中设置以下环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| REQUEST_METHOD | HTTP 方法 | GET / POST |
| QUERY_STRING | URL 查询字符串 | name=alice&age=20 |
| CONTENT_LENGTH | POST body 长度 | 15 |
| CONTENT_TYPE | POST body 类型 | application/x-www-form-urlencoded |
| SERVER_NAME | 服务器主机名 | localhost |
| SERVER_PORT | 端口 | 8080 |

## 正例
```python
import os, subprocess

env = os.environ.copy()   # 继承系统环境（PATH 等）
env.update({
    "REQUEST_METHOD": request["method"],
    "QUERY_STRING": request.get("query_string", ""),
    "CONTENT_LENGTH": str(len(post_body)),
    "CONTENT_TYPE": request["headers"].get("Content-Type", ""),
    "SERVER_NAME": "localhost",
    "SERVER_PORT": str(port),
})
proc = subprocess.Popen([cgi_path], env=env, stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, _ = proc.communicate(input=post_body, timeout=10)
```
