#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: Review Cockpit aggregation/UI tests."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/review-cockpit/run.py"


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"review-cockpit tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_review_cockpit_generates_json_and_static_html():
    with tempfile.TemporaryDirectory(prefix="review_cockpit_") as tmp:
        html_path = Path(tmp) / "cockpit.html"
        result = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--task", "review memory candidate behavior", "--html", str(html_path), "--json"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode in (0, 1), result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] in {"ok", "warning", "error"}
        signals = payload["data"]["signals"]
        for key in ["framework_health", "candidate_review", "memory_conflicts", "model_behavior"]:
            assert key in signals, f"cockpit 缺少信号: {key}"
        assert html_path.exists(), "--html 应写出静态 Review Cockpit 页面"
        html = html_path.read_text(encoding="utf-8")
        assert "DEV SDD Review Cockpit" in html
        assert "Memory Conflicts" in html
        assert "Model Behavior" in html


if __name__ == "__main__":
    tests = [test_tool_exists_and_syntax_ok, test_review_cockpit_generates_json_and_static_html]
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
