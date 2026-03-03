# Bug 报告 / CT 扫描
# ID: BUG-<YYYYMMDD>-<SEQ>
# 状态: 🔴 待诊断

## 1. 症状（必填）
**发生了什么**: 
**期望行为**: 
**实际行为**: 
**影响**: [ ] 程序崩溃 [ ] 结果错误 [ ] 性能异常 [ ] 偶发

## 2. 环境快照（必填）
```bash
conda activate pcl-1.12 && python -c "
import sys, platform, numpy as np
print('Python:', sys.version[:20])
print('Platform:', platform.platform()[:40])
print('NumPy:', np.__version__)
"
```
输出:
```
(粘贴在此)
```

## 3. 完整 Traceback（必填，若有）
```
(粘贴完整错误栈)
```

## 4. 触发输入
```python
input_characteristics = {
    "file": "",
    "point_count": 0,
    "special": "",
}
# 最小复现代码（可选但强烈推荐）:
```

## 5. 时间信息
- 首次出现: 
- 复现率: [ ] 必现 [ ] 高概率 [ ] 偶现
- 上次正常版本: 

---
_诊断结果由 @diagnostician 填写_
**TRIAGE**: [→ TRIAGE_<id>.md]()
**FIX**: [→ FIX_<id>.md]()
**回归测试**: [→ tests/regression/test_BUG_<id>.py]()
