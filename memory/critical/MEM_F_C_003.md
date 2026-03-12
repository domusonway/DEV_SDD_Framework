---
id: MEM_F_C_003
title: 测试失败只改实现，禁止修改断言或 skip
severity: CRITICAL
created: 2026-03-03
confidence: high
validated_by: sdd-tinyhttpd, mini-redis, sdd-taskqueue
---

## 规则
测试/校验失败时，唯一允许的修改是**实现代码**。断言是规格的表达，不是障碍。

## 绝对禁止
```python
# ❌ 改断言值
assert result == b"HTTP/1.1 200 OK"   →   assert result == b"HTTP/1.0 200 OK"

# ❌ skip 测试
@pytest.mark.skip("暂时跳过")

# ❌ 注释断言
# assert response.status_code == 404
```

## 唯一例外
测试本身确认有 bug 时允许修改，但必须：
1. 在项目 memory 或 TODO.md 中记录原因和时间
2. 重新从 RED 开始走完整 TDD 流程
