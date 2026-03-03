---
id: MEM_F_C_002
title: SPEC 输出规格必须明确数值类型精度（如 float32 vs float64）
tags:
  domain: general
  lang_stack: general
  task_type: spec_writing
  severity: CRITICAL
created: 2026-02-27
expires: never
confidence: high
---

## 经验
SPEC 输出表中，凡涉及数值数组，必须明确精度类型（如 float32 / float64 / int32）。
写 `np.ndarray` 不够，必须写 `np.ndarray[float32]`。

## 为什么是 CRITICAL
精度类型错误是最常见的"静默偏差"来源：代码能跑、没有报错，但输出在下游接口处
发生隐式转换，导致精度丢失或接口拒绝。不同项目的底层接口（C扩展、硬件SDK等）
对精度要求不同，必须在 SPEC 阶段明确。

## 反例 → 后果
SPEC 只写 `np.ndarray` → 实现用 float64 → 下游接口要求 float32 → 静默截断或报错。

## 正例
```markdown
| 返回    | 类型        | **dtype**  | 形状   | 说明       |
|---------|-------------|------------|--------|------------|
| result  | np.ndarray  | **float32**| (N, 3) | 处理后数据 |
```

## 验证方式（与项目无关的通用方法）
```python
import pickle
with open("tests/fixtures/reference_<module>_output.pkl", "rb") as f:
    d = pickle.load(f)
print(d.dtype)  # 记录此值到 SPEC 的 dtype 列
```
