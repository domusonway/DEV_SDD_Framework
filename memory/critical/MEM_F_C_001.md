---
id: MEM_F_C_001
title: 校验器必须先用参考输出自测（应 PASS）再交付
severity: CRITICAL
created: 2026-03-03
confidence: high
validated_by: sdd-tinyhttpd, mini-redis, sdd-chatserver
---

## 规则
校验器创建后，**必须先用参考输出对自身运行一次**，确认应 PASS，再交给 Implementer 使用。

## 反例 → 后果
未自测直接交付 → 校验器比对逻辑有 bug → 实现正确但误报失败 → 浪费多轮调试

## 正例
```bash
# 校验器自测
python3 tests/validators/validate_response.py tests/fixtures/response_200.txt
# 预期: ✅ PASS
```

## 检查清单
- [ ] 有参考输出文件（fixtures/）
- [ ] 用参考输出跑校验器，确认 PASS
- [ ] 用已知错误输出跑，确认 FAIL
