# Memory 写入指南（HOW_TO_WRITE.md）

## 决策树
```
经验值得记录
  → 换个完全不同的项目还有用？
      是 → framework/ 或 domains/<d>/
      否 → projects/<proj>/
  → 涉及特定技术领域？
      是 → domains/<domain>/
      否 → framework/
  → 违反直接导致错误且不分任务类型？
      是 → critical/（CRITICAL，永不过期）
      否 → important/ 或 tips/
```

## 文件命名
- 框架: `MEM_F_<S>_<NNN>.md`（S=C/I/T）
- 领域: `MEM_D_<DOM>_<NNN>.md`
- 项目: `MEM_P_<PROJ>_<NNN>.md`

## 必要字段
```yaml
---
id: MEM_X_X_NNN
title: <15字内>
tags:
  domain: general|point_cloud|python_numpy
  task_type: spec_writing|tdd_impl|debugging|diagnosis
  severity: CRITICAL|IMPORTANT|TIPS
created: YYYY-MM-DD
expires: never|YYYY-MM-DD
confidence: high|medium|low
---
```

## 写入后必须更新 INDEX.md
