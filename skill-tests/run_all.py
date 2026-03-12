#!/usr/bin/env python3
"""
DEV SDD Framework Skill Tests Runner
用法: python3 skill-tests/run_all.py [skill_name]
"""
import subprocess
import sys
import os
import json
from pathlib import Path
from datetime import datetime

CASES_DIR = Path(__file__).parent / "cases"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

TEST_FILES = [
    "test_complexity_assess.py",
    "test_tdd_cycle.py",
    "test_diagnose_bug.py",
    "test_memory_update.py",
    "test_validate_output.py",
    "test_hook_network_guard.py",
    "test_hook_post_green.py",
    "test_hook_stuck_detector.py",
]


def run_test(test_file: str) -> dict:
    path = CASES_DIR / test_file
    if not path.exists():
        return {"name": test_file, "status": "MISSING", "output": "文件不存在"}

    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True, text=True, timeout=30
    )
    status = "PASS" if result.returncode == 0 else "FAIL"
    return {
        "name": test_file,
        "status": status,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main():
    filter_name = sys.argv[1] if len(sys.argv) > 1 else None
    tests = [t for t in TEST_FILES if filter_name is None or filter_name in t]

    print("=" * 50)
    print("DEV SDD Framework Skill Tests")
    print("=" * 50)

    results = []
    for test_file in tests:
        try:
            r = run_test(test_file)
        except subprocess.TimeoutExpired:
            r = {"name": test_file, "status": "TIMEOUT", "output": "超时（>30s）"}

        icon = {"PASS": "✅", "FAIL": "❌", "MISSING": "⚠️", "TIMEOUT": "⏱️"}.get(r["status"], "?")
        name = r["name"].replace(".py", "").replace("test_", "")
        print(f"{icon} {name:<30} {r['status']}")
        if r["status"] == "FAIL":
            stderr = r.get("stderr", "")
            if stderr:
                print(f"   └─ {stderr.strip()[:120]}")
        results.append(r)

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)
    print("=" * 50)
    print(f"结果: {passed}/{total} 通过")

    # 保存报告
    report = {
        "timestamp": datetime.now().isoformat(),
        "passed": passed,
        "total": total,
        "results": results,
    }
    report_path = REPORTS_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"报告已保存: {report_path}")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
