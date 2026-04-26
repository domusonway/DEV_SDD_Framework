#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: executable context-probe helper tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/context-probe/run.py"
SKILL_PATH = FRAMEWORK_ROOT / ".claude/skills/context-probe/SKILL.md"
START_WORK = FRAMEWORK_ROOT / ".claude/tools/start-work/run.py"


def make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="context_probe_project_", dir=str(FRAMEWORK_ROOT / "projects")))
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("# test\n工作模式: L\n", encoding="utf-8")
    (root / "memory" / "INDEX.md").write_text("# memory\n", encoding="utf-8")
    (root / "docs" / "plan.json").write_text(
        json.dumps({"project": root.name, "batches": [{"name": "B1", "modules": [{"id": "T-001", "name": "m", "state": "pending"}]}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"context-probe helper 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_tool_classifies_tdd_and_type_memory():
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "测试失败 TypeError bytes str 断言", "--json"],
        capture_output=True,
        text=True,
        cwd=str(FRAMEWORK_ROOT),
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)["data"]
    assert "TDD 问题" in data["matched_dimensions"]
    assert "类型安全" in data["matched_dimensions"]
    assert "MEM_F_C_003" in data["auto_load"] or "MEM_F_C_002" in data["auto_load"]


def test_tool_records_loaded_memory_usage():
    project = make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(TOOL_PATH), "测试失败 TypeError", "--project", project.name, "--record-loaded", "--json"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["data"]["recorded_events"], "应记录 loaded 事件"
        usage_path = project / "memory" / "memory_usage.jsonl"
        assert usage_path.exists(), "应写入 memory_usage.jsonl"
        assert "loaded" in usage_path.read_text(encoding="utf-8")
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_start_work_includes_context_probe_for_task_text():
    project = make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(START_WORK), project.name, "--json", "--task", "测试失败 TypeError"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)["data"]
        matched = data.get("context_probe", {}).get("matched_dimensions") or []
        assert "TDD 问题" in matched
        assert "类型安全" in matched
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_skill_references_executable_helper_and_memory_usage():
    content = SKILL_PATH.read_text(encoding="utf-8")
    assert ".claude/tools/context-probe/run.py" in content
    assert "--record-loaded" in content
    assert "memory_usage.jsonl" in content


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_tool_classifies_tdd_and_type_memory,
        test_tool_records_loaded_memory_usage,
        test_start_work_includes_context_probe_for_task_text,
        test_skill_references_executable_helper_and_memory_usage,
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
