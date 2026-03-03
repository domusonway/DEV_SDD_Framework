---
id: MEM_F_C_003
title: 禁止修改测试用例或降低校验阈值来通过测试
tags:
  domain: general
  task_type: tdd_impl, debugging, validation
  severity: CRITICAL
created: 2026-02-27
expires: never
confidence: high
---

## 经验
测试/校验失败时，唯一允许的修改是**实现代码**。禁止改断言、降 rtol、skip 测试。

## 反例 → 后果
改测试来通过 = 技术债最危险形式 → 集成阶段以更难诊断的形式爆发。

## 唯一例外
测试本身有 bug（fixture 生成逻辑错误）时允许修改，但必须：
1. HUMAN_NOTES.md 记录原因
2. 重新生成 fixture（不只改断言值）
