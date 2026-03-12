# SPEC: {{MODULE_NAME}}
> 最后更新: {{DATE}} | 状态: 草稿/确认/实现中/完成

---

## 模块职责
{{ONE_LINE_DESCRIPTION}}

---

## 接口定义

### 函数/类签名
```python
def {{FUNCTION_NAME}}(
    {{PARAM_1}}: {{TYPE_1}},
    {{PARAM_2}}: {{TYPE_2}},
) -> {{RETURN_TYPE}}:
    """
    {{DOCSTRING}}
    
    Args:
        {{PARAM_1}}: {{PARAM_1_DESC}}
        {{PARAM_2}}: {{PARAM_2_DESC}}
    
    Returns:
        {{RETURN_DESC}}
    
    Raises:
        {{EXCEPTION_1}}: {{WHEN}}
    """
```

---

## 接口表（精确 dtype，不可含糊）

| 参数/返回 | 名称 | 类型 | 说明 |
|---------|------|------|------|
| 输入 | {{PARAM_1}} | {{TYPE}} | {{DESC}} |
| 输出 | 返回值 | **{{EXACT_TYPE}}** | {{DESC}} |
| 异常 | {{EXCEPTION}} | Exception | {{WHEN}} |

---

## 行为规格

### 正常路径
```
输入: {{EXAMPLE_INPUT}}
输出: {{EXAMPLE_OUTPUT}}
```

### 边界情况
```
情况1: {{EDGE_CASE_1}}
预期: {{EXPECTED_1}}

情况2: {{EDGE_CASE_2}}
预期: {{EXPECTED_2}}
```

### 错误路径
```
错误1: {{ERROR_CASE_1}}
预期: 抛出 {{EXCEPTION_TYPE}}，消息含 "{{MESSAGE_FRAGMENT}}"
```

---

## 依赖
- 依赖模块: {{DEPENDENCIES}}
- 被依赖: {{DEPENDENTS}}

---

## 验收标准
- [ ] {{ACCEPTANCE_1}}
- [ ] {{ACCEPTANCE_2}}
