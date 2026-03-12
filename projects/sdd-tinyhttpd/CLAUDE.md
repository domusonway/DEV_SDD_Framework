# sdd-tinyhttpd · 项目上下文入口
> 创建日期: 2026-03-03 | 复杂度: 8/10 | 工作模式: H（完整）
> 参考: tinyhttpd（C 语言 HTTP 服务器教学项目），Python 重构版本

---

## 项目简介
用 Python 重新实现 tinyhttpd，一个支持静态文件和 CGI 的极简 HTTP/1.0 服务器。
目标：理解 HTTP 服务器工作原理，练习 SDD + TDD 流程，验证框架 H 模式。

---

## 技术栈
- 语言: Python 3.10+
- 测试框架: pytest
- 网络: socket（stdlib）
- 并发: threading（每请求一线程）
- CGI: subprocess.Popen

---

## 项目特有约束
1. 使用 HTTP/1.0 协议（每次请求后关闭连接）
2. 响应必须是 bytes（含头部），不是 str
3. CGI 脚本放在 htdocs/cgi-bin/，需要执行权限
4. 静态文件根目录：htdocs/
5. 端口：8080（可通过环境变量 PORT 覆盖）

---

## 模块列表

| 模块 | 路径 | SPEC | 状态 |
|------|------|------|------|
| request_parser | modules/request_parser/ | [SPEC](modules/request_parser/SPEC.md) | 🔴 待实现 |
| response | modules/response/ | [SPEC](modules/response/SPEC.md) | 🔴 待实现 |
| router | modules/router/ | [SPEC](modules/router/SPEC.md) | 🔴 待实现 |
| static_handler | modules/static_handler/ | [SPEC](modules/static_handler/SPEC.md) | 🔴 待实现 |
| cgi_handler | modules/cgi_handler/ | [SPEC](modules/cgi_handler/SPEC.md) | 🔴 待实现 |
| server | modules/server/ | [SPEC](modules/server/SPEC.md) | 🔴 待实现 |

---

## 按需加载地图（项目级）

| 场景 | 路径 |
|------|------|
| 项目背景 | `docs/CONTEXT.md` |
| 实现计划 | `docs/PLAN.md` |
| 当前进度 | `docs/TODO.md` |
| 项目记忆 | `memory/INDEX.md` |
| HTTP 协议 | `../../memory/domains/http/INDEX.md` |

---

## 验收标准
- [ ] curl http://localhost:8080/ 返回 index.html 内容
- [ ] curl http://localhost:8080/notfound 返回 404
- [ ] curl http://localhost:8080/cgi-bin/color.cgi 返回 CGI 输出
- [ ] ab -n 100 -c 10 无错误（并发基础稳定性）
