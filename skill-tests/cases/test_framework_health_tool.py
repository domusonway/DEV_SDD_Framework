#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: framework-health dashboard tests."""

import json
import subprocess
import sys
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/framework-health/run.py"


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"framework-health tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_health_json_contains_core_signals():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--json", "--task", "请审查经验沉淀和多模块并行规划"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode in (0, 1), result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] in ("ok", "warning", "error")
    data = payload["data"]
    for signal in [
        "start_work",
        "candidate_schema",
        "candidate_review",
        "parallel_next",
        "parallel_conflicts",
        "memory_prune",
        "memory_conflicts",
        "model_behavior",
    ]:
        assert signal in data["signals"], f"health 缺少信号: {signal}"
    start_data = data["signals"]["start_work"].get("data") or {}
    assert "prompt_policy" in start_data, "start-work 信号应包含 prompt_policy"
    assert "context_probe" in start_data, "start-work 信号应包含 context_probe"


def test_health_counts_only_actionable_candidate_review_items():
    result = subprocess.run([sys.executable, str(TOOL_PATH), "--json"], capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT))
    assert result.returncode in (0, 1), result.stderr
    data = json.loads(result.stdout)["data"]
    review_items = data["signals"]["candidate_review"]["data"]["items"]
    actionable = [item for item in review_items if item.get("recommendation") not in (None, "none")]
    sources = {issue["source"] for issue in data.get("issues", [])}
    assert ("candidate_review" in sources) == bool(actionable), "只有可操作候选才应产生 review issue"


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_health_json_contains_core_signals,
        test_health_counts_only_actionable_candidate_review_items,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ❌ {test.__name__} [ERROR]: {exc}")
            failed += 1
    sys.exit(failed)
