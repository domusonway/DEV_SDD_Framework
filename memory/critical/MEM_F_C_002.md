---
id: MEM_F_C_002
title: SPEC 接口输出规格必须明确 dtype（bytes/str/int）
severity: CRITICAL
created: 2026-03-03
confidence: high
validated_by: sdd-tinyhttpd, sdd-chatserver, file-indexer
---

## 规则
SPEC 输出表中，所有返回值必须明确类型。HTTP 响应场景必须明确是 `bytes` 还是 `str`。

## 反例 → 后果
```
# ❌ 模糊 SPEC
| 返回 | 响应内容 |
```
→ 实现返回 str → `socket.sendall(str)` → TypeError 在 E2E 才爆

## 正例
```
# ✅ 精确 SPEC
| 返回     | 类型  | 说明                     |
|----------|-------|--------------------------|
| response | bytes | HTTP 响应，含头+body     |
| status   | int   | HTTP 状态码 200/404/500  |
```
