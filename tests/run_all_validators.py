"""tests/run_all_validators.py — 运行所有模块校验器"""
import subprocess, sys
from pathlib import Path
from datetime import datetime

validators = sorted(Path(__file__).parent.glob("validators/validate_[!T]*.py"))
if not validators:
    print("⚠️  无校验器（跳过 TEMPLATE）")
    sys.exit(0)

results = {}
for v in validators:
    m = v.stem.replace("validate_","")
    r = subprocess.run([sys.executable, str(v)], capture_output=True, text=True,
                       cwd=Path(__file__).parent.parent)
    results[m] = r.returncode == 0
    print(f"{'✅' if results[m] else '❌'} {m}")

passed = sum(results.values())
print(f"\n{'='*40}\n总计: {passed}/{len(results)} 通过 [{datetime.now():%Y-%m-%d %H:%M}]")
sys.exit(0 if passed == len(results) else 1)
