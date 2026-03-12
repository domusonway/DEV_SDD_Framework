---
id: MEM_F_I_003
title: MockSocket 会掩盖隐式契约 Bug，E2E 才能发现
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd
---

## 规则
MockSocket 只验证你已知的行为，无法发现模块间隐式契约（如 bytes/str 边界、连接关闭信号）。
关键集成点必须有 E2E 测试，不能只靠 Mock。

## 典型案例
response 模块返回 str，server 模块用 `sendall()` 发送。
MockSocket 的 sendall 接受 str/bytes 都不报错，但真实 socket.sendall(str) 抛 TypeError。
→ 单元全绿，E2E 报错。

## 建议测试层级
| 层级 | 工具 | 覆盖范围 |
|------|------|---------|
| 单元 | socketpair | 单模块逻辑 |
| 集成 | 真实 TCP loopback | 模块间契约 |
| E2E | HTTP 客户端 | 完整请求/响应链路 |
