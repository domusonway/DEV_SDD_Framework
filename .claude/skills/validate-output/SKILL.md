---
name: validate-output
description: |
  输出校验技能。将重构实现的输出与参考项目输出精确比对。
  当需要运行校验器、生成 reference fixtures、比对输出一致性时自动调用。
  Use when verifying module output matches reference, or creating validators.
allowed-tools: Read, Write, Bash, Glob
context: fork
---

# 输出校验技能

## 校验架构
```
参考项目 → generate_reference.py → tests/fixtures/reference_<m>_output.pkl
实现代码 → 运行实现 → 实际输出
validate_<m>.py → 比对（rtol=1e-5）→ ✅ 通过 / ❌ 失败（含差异分析）
```

## 生成 Fixtures
```bash
<project_env_cmd> \
  python tests/fixtures/generate_reference.py --module <module>
```

## 创建校验器（复制模板并填写）
```bash
cp tests/validators/validate_TEMPLATE.py tests/validators/validate_<module>.py
# 修改：MODULE_NAME, IMPL_MODULE, IMPL_FUNCTION
```

## 校验器自测（必须先自测！）
```bash
# 用参考输出自测：应该 PASS（若 FAIL 说明校验器本身有 bug）
<project_env_cmd> python tests/validators/validate_<module>.py
```

## 运行全量校验
```bash
<project_env_cmd> python tests/run_all_validators.py
```

## 容差标准（不可降低）
- `rtol=1e-5`（相对误差）
- `atol=1e-7`（绝对误差）
- 失败时只能修改实现，不能降低阈值
