---
module: <MODULE_NAME>
version: 0.1.0
status: draft
---

# 模块规格（SPEC.md）

> ⚠️ 实现前必须先读 projects/<proj>/CONTEXT.md

## 1. 职责（一句话）
_(单一职责原则)_

## 2. 接口定义

```python
def <function_name>(<params>) -> <ReturnType>:
    """
    Args:
        param: Type — 说明
    Returns:
        Type[dtype] shape(N,M) — 说明
    Raises:
        ValueError: 触发条件
    """
```

### 输入规格
| 参数 | 类型 | dtype | 形状 | 说明 |
|------|------|-------|------|------|

### 输出规格
| 返回 | 类型 | **dtype** | 形状 | 说明 |
|------|------|-----------|------|------|
_(dtype 必须明确，float32 vs float64 是静默偏差最常见来源)_

## 3. 行为约束
- 输入验证：
- 边界条件：
- 数值精度：

## 4. 参考项目对应（位置，不复制）
| 功能 | 参考位置 | 备注 |
|------|---------|------|

## 5. 测试要点
- 正常用例：
- 边界用例：
- 异常用例：
- 校验基准：`tests/fixtures/reference_<module>_output.pkl`

## 6. 依赖
- 依赖模块：
- 被依赖于：
- 第三方库：
