---
name: tdd-cycle
description: |
  TDD（测试驱动开发）完整循环技能。当需要实现新功能模块、进行测试驱动开发、
  编写实现代码、运行测试时自动调用。
  包含 RED（写测试）→ GREEN（实现）→ REFACTOR（重构）→ VALIDATE（校验）完整流程。
  Use PROACTIVELY when implementing any module in modules/ directory.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# TDD 开发循环

## 前置条件
1. 模块 `SPEC.md` 已存在且通过 Planner 审核
2. `tests/fixtures/reference_<module>_output.pkl` 已由 Tester 生成
3. 运行环境：参考 `projects/<your_project>/CONTEXT.md §2`（项目指定的环境）

## 循环步骤

### STEP 1 — RED：写测试（预期失败）
```python
# modules/<module>/tests/test_<module>.py
import pytest, pickle
import numpy as np
from pathlib import Path

FIXTURES = Path("tests/fixtures")

def test_<function>_output_matches_reference():
    with open(FIXTURES / "reference_<module>_output.pkl", "rb") as f:
        ref = pickle.load(f)
    with open(FIXTURES / "reference_<module>_input.pkl", "rb") as f:
        inputs = pickle.load(f)
    from modules.<module>.<impl> import <function>
    result = <function>(**inputs)
    if isinstance(ref, np.ndarray):
        np.testing.assert_allclose(result, ref, rtol=1e-5)
    else:
        assert result == ref
```
```bash
# 用项目环境运行（环境名从 CONTEXT.md §2 获取）
<project_env_cmd> python -m pytest modules/<module>/tests/ -v
# 预期: FAILED ✓
```

### STEP 2 — GREEN：实现（自主编写，不复制参考代码）
```bash
<project_env_cmd> python -m pytest modules/<module>/tests/ -v
# 预期: PASSED ✓
```

### STEP 3 — REFACTOR：重构后重新运行

### STEP 4 — VALIDATE
```bash
<project_env_cmd> python tests/validators/validate_<module>.py
# 预期: ✅ 校验通过
```

## 失败处理规则
| 失败类型 | 禁止 | 正确 |
|---------|------|------|
| 测试失败 | ~~改测试断言~~ | 改实现代码 |
| 校验不通过 | ~~降低 rtol~~ | 分析差异，改实现 |
| 环境报错 | ~~跳过测试~~ | 修复环境，记录到 memory |
