# SPEC: static_handler
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
读取静态文件并构建 HTTP 响应。

---

## 接口定义

```python
def handle_static(path: str, htdocs_root: str) -> bytes:
    """
    读取静态文件，返回 HTTP 响应 bytes。

    Returns:
        bytes: HTTP 200 响应（文件存在）或 HTTP 404 响应
    """
```

---

## 接口表

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | path | **str** | 请求路径 |
| 输入 | htdocs_root | **str** | 静态文件根目录 |
| 输出 | 返回值 | **bytes** | 完整 HTTP 响应 |

---

## 行为规格

### 文件存在
```
输出: HTTP/1.0 200 OK + 正确 Content-Type + 文件内容（bytes）
```

### 文件不存在
```
输出: HTTP/1.0 404 Not Found + body="404 Not Found"
```

### Content-Type 推断
| 扩展名 | Content-Type |
|--------|-------------|
| .html  | text/html; charset=utf-8 |
| .css   | text/css |
| .js    | application/javascript |
| .png   | image/png |
| .jpg   | image/jpeg |
| 其他   | application/octet-stream |

---

## 依赖
- 依赖: response 模块
- 被依赖: server
