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
=== DEV SDD Framework Skill Tests ===
test_complexity_assess  ✅ PASS
test_tdd_cycle          ✅ PASS
test_diagnose_bug       ✅ PASS
test_memory_update      ✅ PASS
test_validate_output    ✅ PASS
test_hook_network_guard ✅ PASS
test_hook_post_green    ✅ PASS
test_hook_stuck_detector✅ PASS

8/8 通过
```

## 失败时
- 检查 skill-tests/reports/ 下的详情报告
- 查看对应的 SKILL.md 是否需要更新
