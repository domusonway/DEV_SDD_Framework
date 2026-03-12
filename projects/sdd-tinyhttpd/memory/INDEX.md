# sdd-tinyhttpd · 项目记忆索引
> 创建日期: 2026-03-03

---

## 3行摘要（切换到本项目时必读，5秒知道特有约束）
1. 所有响应必须是 **bytes**，含头部+body，`socket.sendall()` 只接受 bytes
2. recv 后必须检查 `if not data: break`，b'' = 对端关闭，不检查 CPU 100%
3. CGI 用 `subprocess.Popen`，必须设置 REQUEST_METHOD/QUERY_STRING 等环境变量

---

## Bug 经验表

| ID | 症状 | 根因 | 预防 | 详情 |
|----|------|------|------|------|
| P_THD_001 | sendall(str) → TypeError | response 模块返回 str 而非 bytes | SPEC 明确 dtype | [→](P_THD_001.md) |
| P_THD_002 | recv 死循环 CPU 100% | 未检查 b'' 连接关闭信号 | if not data: break | [→](P_THD_002.md) |

---

## 设计决策表

| 决策 | 选择 | 原因 | 日期 |
|------|------|------|------|
| 并发模型 | threading（每请求一线程） | 简单，教学目的，无需高并发 | 2026-03-03 |
| HTTP 版本 | HTTP/1.0 | 对应原始 tinyhttpd，每次请求关闭连接 | 2026-03-03 |
| CGI 执行 | subprocess.Popen | C fork+execl → Python 多线程安全替代 | 2026-03-03 |

---

## 记忆文件
- [P_THD_001.md](P_THD_001.md) — sendall 收到 str 而非 bytes
- [P_THD_002.md](P_THD_002.md) — recv b'' 未检查死循环

---

## 统计
```
Bug记忆: 2条
设计决策: 3条
创建: 2026-03-03
上次更新: 2026-03-03
```
