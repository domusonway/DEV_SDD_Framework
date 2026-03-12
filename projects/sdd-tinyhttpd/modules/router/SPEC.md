# SPEC: router
> 创建日期: 2026-03-03 | 状态: 确认

---

## 模块职责
根据请求路径决定使用哪种处理器。

---

## 接口定义

```python
def route(path: str, htdocs_root: str) -> str:
    """
    根据路径返回处理器类型。

    Returns:
        str: "static" | "cgi" | "not_found"
    """
```

---

## 接口表

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | path | **str** | 请求路径（不含 query string） |
| 输入 | htdocs_root | **str** | 静态文件根目录的绝对路径 |
| 输出 | 返回值 | **str** | "static" / "cgi" / "not_found" |

---

## 路由规则

| 条件 | 返回值 |
|------|--------|
| path 以 /cgi-bin/ 开头 | "cgi" |
| 文件存在于 htdocs_root + path | "static" |
| path == "/" 且 index.html 存在 | "static" |
| 其他 | "not_found" |

---

## 行为规格

```
path="/index.html", 文件存在    → "static"
path="/cgi-bin/color.cgi"       → "cgi"
path="/missing.html", 文件不存在 → "not_found"
path="/"                        → "static"（重定向到 index.html）
```

## 依赖
- 依赖: os.path（stdlib）
- 被依赖: server
