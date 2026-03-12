---
id: MEM_F_I_005
title: C fork+execl → Python subprocess.Popen（多线程安全）
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd CGI 模块
---

## 规则
C 的 `fork()`+`execl()` 在 Python 多线程环境下不安全（fork 后子进程继承锁状态）。
用 `subprocess.Popen` 代替，它在内部处理 fork 安全问题。

## 对照
```c
// C
if (fork() == 0) {
    execl(cgi_path, cgi_path, NULL);
    exit(1);
}
```

```python
# Python
proc = subprocess.Popen(
    [cgi_path],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=env
)
stdout, _ = proc.communicate(timeout=10)
```

## 注意
- 设置 `timeout` 防止 CGI 脚本挂死
- 传递 `env` 字典设置 CGI 环境变量（QUERY_STRING, REQUEST_METHOD 等）
- 捕获 `subprocess.TimeoutExpired` 并 `proc.kill()`
