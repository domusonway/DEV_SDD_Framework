#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: DEV SDD dashboard tests."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/dev-sdd-dashboard/run.py"
BRIEF_PATH = FRAMEWORK_ROOT / "docs/dev_sdd_dashboard_BRIEF.md"
DOUBLE_CLICK_SCRIPT = FRAMEWORK_ROOT / "tools/dev-sdd-dashboard.sh"
DESKTOP_ENTRY = FRAMEWORK_ROOT / "tools/dev-sdd-dashboard.desktop"


def test_tool_exists_and_syntax_ok():
    assert BRIEF_PATH.exists(), f"dashboard BRIEF 不存在: {BRIEF_PATH}"
    assert TOOL_PATH.exists(), f"dev-sdd-dashboard tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_root_tools_double_click_entrypoints_exist():
    assert DOUBLE_CLICK_SCRIPT.exists(), f"双击脚本不存在: {DOUBLE_CLICK_SCRIPT}"
    assert DESKTOP_ENTRY.exists(), f"desktop 入口不存在: {DESKTOP_ENTRY}"
    assert os.access(DOUBLE_CLICK_SCRIPT, os.X_OK), "双击脚本应具备执行权限"
    script = DOUBLE_CLICK_SCRIPT.read_text(encoding="utf-8")
    desktop = DESKTOP_ENTRY.read_text(encoding="utf-8")
    assert ".claude/tools/dev-sdd-dashboard/run.py" in script
    assert "--html" in script
    assert "xdg-open" in script or "webbrowser" in script
    assert "dashboard-launch.log" in script
    assert "Exec=" in desktop
    assert "dev-sdd-dashboard.sh" in desktop


def test_dashboard_generates_json_html_and_history():
    with tempfile.TemporaryDirectory(prefix="dev_sdd_dashboard_") as tmp:
        html_path = Path(tmp) / "dashboard.html"
        history_path = Path(tmp) / "history.jsonl"
        result = subprocess.run(
            [
                sys.executable,
                str(TOOL_PATH),
                "--task",
                "dashboard health smoke",
                "--html",
                str(html_path),
                "--history",
                str(history_path),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode in (0, 1), result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] in {"ok", "warning", "error"}
        data = payload["data"]
        for key in ["overview", "action_items", "signals", "reports", "history_event"]:
            assert key in data, f"dashboard 缺少字段: {key}"
        assert data["overview"]["framework_status"] in {"ok", "warning", "error"}
        assert html_path.exists(), "--html 应写出静态 Dashboard 页面"
        html = html_path.read_text(encoding="utf-8")
        assert "DEV SDD Dashboard" in html
        assert "Action Required" in html
        assert "Memory System" in html
        assert history_path.exists(), "dashboard 应写入历史 jsonl"


def test_dashboard_interactive_dry_run_lists_actions():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "interactive", "--dry-run", "--json"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode in (0, 1), result.stderr
    data = json.loads(result.stdout)["data"]
    assert data["mode"] == "interactive_dry_run"
    assert "menu" in data
    assert "action_items" in data
    assert data["commands"], "interactive dry-run 应提供可执行命令提示"


if __name__ == "__main__":
    tests = [test_tool_exists_and_syntax_ok, test_root_tools_double_click_entrypoints_exist, test_dashboard_generates_json_html_and_history, test_dashboard_interactive_dry_run_lists_actions]
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
