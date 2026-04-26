#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: Layer2/Layer3 model behavior helper tests."""

import json
import subprocess
import sys
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/model-behavior/run.py"


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"model-behavior tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_readiness_reports_case_counts_without_calling_api():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "readiness", "--json"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode in (0, 1), result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] in {"ok", "warning", "error"}
    data = payload["data"]
    assert data["counts"]["total_cases"] > 0, "generated cases 应存在并包含 Layer2/Layer3 用例"
    assert "api_key_present" in data["api"]
    assert data["api"]["provider"] in {"bailian", "anthropic"}
    assert data["api"]["model"], "Layer2/3 行为验证应暴露可配置模型"
    assert data["api"]["live_command"] == "python3 skill-tests/run_all.py --layer 3"


def test_dry_run_lists_layer_cases_without_model_api():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "dry-run", "--skill", "tdd-cycle", "--layer", "3", "--max-cases", "3", "--json"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["mode"] == "dry_run_no_api"
    assert data["selected_count"] >= 1
    assert 1 <= len(data["sample_cases"]) <= 3
    assert all("criterion" in case for case in data["sample_cases"])


if __name__ == "__main__":
    tests = [test_tool_exists_and_syntax_ok, test_readiness_reports_case_counts_without_calling_api, test_dry_run_lists_layer_cases_without_model_api]
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
