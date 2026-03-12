---
id: MEM_F_I_006
title: RED 阶段先确认测试 FAIL，直接 PASS = 测试写错了
severity: IMPORTANT
created: 2026-03-03
validated_by: sdd-tinyhttpd, mini-redis
---

## 规则
TDD RED 阶段：写完测试后，**先运行一次确认 FAIL**，再写实现。
如果测试在无实现时就 PASS，说明测试逻辑有误（永真、路径错误、import 错误等）。

## 反例
```python
def test_parse_request():
    result = parse_request(b"GET / HTTP/1.1\r\n\r\n")
    assert result is not None   # ❌ 即使实现返回 None 也 PASS（not None 是 True？不对）
```

## 正例
```python
def test_parse_request():
    result = parse_request(b"GET / HTTP/1.1\r\n\r\n")
    assert result["method"] == "GET"   # 无实现 → KeyError → FAIL ✅
    assert result["path"] == "/"
```

## 诊断
运行测试得到 PASS → 检查：
1. assert 条件是否永真
2. 模块是否已有旧实现（应先删除或 raise NotImplementedError）
3. import 是否指向了错误模块
