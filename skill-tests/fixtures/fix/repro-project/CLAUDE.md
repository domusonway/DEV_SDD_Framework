# repro-project · 项目指引

> 版本: v1.0 | 工作模式: M 标准

---

## 项目简介

用于验证 `DEV_SDD:FIX` 在结构化项目上下文中先做 triage，再提供修复选项。

---

## 项目特有约束

1. `CalibrationResult` 必须在进入下游匹配前完成完整性校验。
2. 激光模型必须保持二次曲面，不能用兜底平面系数掩盖错误输入。
3. 校准异常必须在 `calibration` 边界抛出，不能拖到 `stripe_matching` 或 `reconstruction_3d`。

---

## 模块列表

| 模块 | 路径 | 说明 | 依赖 |
|------|------|------|------|
| calibration | `sls/calibration.py` | 负责加载与验证标定参数 | 无 |
| stripe_matching | `sls/stripe_matching.py` | 使用校准结果做双目匹配 | calibration |
| reconstruction_3d | `sls/reconstruction_3d.py` | 基于匹配结果重建点云 | calibration, stripe_matching |
