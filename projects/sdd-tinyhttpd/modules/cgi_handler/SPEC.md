# SPEC: cgi_handler
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
执行 CGI 脚本，返回脚本输出封装的 HTTP 响应。

---

## 接口定义

```python
def handle_cgi(path: str, request: dict, htdocs_root: str) -> bytes:
    """
    执行 CGI 脚本，返回 HTTP 响应 bytes。

    Returns:
        bytes: HTTP 200（成功）或 HTTP 500（脚本失败）
    """
```

---

## 接口表

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | path | **str** | CGI 脚本路径（含 /cgi-bin/） |
| 输入 | request | **dict** | parse_request 返回的字典 |
| 输入 | htdocs_root | **str** | htdocs 根目录 |
| 输出 | 返回值 | **bytes** | 完整 HTTP 响应 |

---

## 行为规格

### 正常执行
```
执行 htdocs_root + path 对应的脚本
设置 CGI 环境变量（MEM_D_HTTP_004）
返回: HTTP/1.0 200 OK + 脚本 stdout
```

### 脚本不存在
```
返回: HTTP/1.0 404 Not Found
```

### 脚本执行失败（returncode != 0）
```
返回: HTTP/1.0 500 Internal Server Error
```

### 超时（>10秒）
```
kill 脚本进程
返回: HTTP/1.0 500 Internal Server Error，body 含 "timeout"
```

---

## 依赖
- 依赖: response 模块，subprocess，os
- 被依赖: server
