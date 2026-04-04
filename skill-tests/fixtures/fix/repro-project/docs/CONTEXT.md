# repro-project · 项目背景与架构

---

## 项目目标
验证 FIX 在可复现缺陷下，先读取项目上下文与记忆，再给出最小修复和全面修复两个层级的行动建议。

---

## 背景
当前项目的校准链路会把不完整的相机参数继续传给激光曲面拟合和下游模块，导致回归影响难以定位。

---

## 技术栈
- 语言: Python 3.11
- 测试框架: pytest
- 主要依赖: stdlib only

---

## 模块划分

### calibration
- 职责：加载并验证相机参数与激光曲面拟合输入
- 输入：标定文件、相机参数
- 输出：可供下游使用的 `CalibrationResult`
- 依赖：无

### stripe_matching
- 职责：基于标定结果做双目匹配
- 输入：`CalibrationResult`、左右条纹集合
- 输出：匹配后的条纹对
- 依赖：calibration

### reconstruction_3d
- 职责：从匹配结果恢复点云
- 输入：匹配条纹对、`CalibrationResult`
- 输出：点云数据
- 依赖：calibration, stripe_matching

---

## 验收标准
- 不完整的相机参数必须在 `calibration` 边界被拒绝
- `stripe_matching` 与 `reconstruction_3d` 不应接收到无效 `CalibrationResult`
- FIX 输出必须在 triage 后给出两层修复建议
