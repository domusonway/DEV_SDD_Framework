# SPEC: {{MODULE_NAME}}
> 创建日期: {{DATE}} | 状态: 草稿

---

## 模块职责
[一句话描述这个模块做什么]

---

## 接口定义

```python
def function_name(
    param1: Type1,
    param2: Type2,
) -> ReturnType:
    """
    [功能描述]
    
    Args:
        param1: 说明
        param2: 说明
    
    Returns:
        说明（明确 bytes/str/int/dict）
    
    Raises:
        ValueError: 何时抛出
    """
```

---

## 接口表（必须明确 dtype）

| 方向 | 名称 | 类型 | 说明 |
|------|------|------|------|
| 输入 | param1 | **str** | |
| 输出 | 返回值 | **bytes** | 明确写 bytes 或 str，不能含糊 |
| 异常 | ValueError | Exception | 何时触发 |

---

## 行为规格

### 正常路径
```
输入: 
输出: 
```

### 边界情况
```
情况: 空输入
预期: 
```

### 错误路径
```
错误: 非法格式
预期: 抛出 ValueError
```

---

## 依赖关系
- 依赖: （无 / 模块名）
- 被依赖: （无 / 模块名）

---

## 验收标准
- [ ] 正常路径测试通过
- [ ] 边界情况测试通过
- [ ] 错误路径测试通过
- [ ] 返回类型与此 SPEC 精确一致
