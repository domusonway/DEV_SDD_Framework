# /project:validate — 运行框架 skill 验证测试

## 用法
```
/project:validate [skill-name]
```
无参数时运行全部测试。

## 执行步骤
```bash
# 全部
python3 skill-tests/run_all.py

# 单个
python3 skill-tests/cases/test_<skill-name>.py
```

## 预期输出
```
  ✅ complexity_assess     PASS
  ✅ tdd_cycle             PASS
  ✅ ...（逐项列出全部 Layer 1 测试文件）
  ✅ workflow_drift_guards PASS

  总结: 30/30 通过  ✅

  报告: skill-tests/reports/report_L1_<时间戳>.json
```
> Layer 1 用例数量随框架演进变化，以实际 `总结: N/N 通过` 行为准（当前 30）。

## 失败时
- 检查 skill-tests/reports/ 下的详情报告
- 查看对应的 SKILL.md 是否需要更新
