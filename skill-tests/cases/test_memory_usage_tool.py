#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: memory usage/effectiveness tracker tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/memory-usage/run.py"
MEMORY_UPDATE = FRAMEWORK_ROOT / ".claude/skills/memory-update/SKILL.md"


def make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="memory_usage_project_", dir=str(FRAMEWORK_ROOT / "projects")))
    (root / "memory").mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("# test\n工作模式: L\n", encoding="utf-8")
    return root


def run_tool(*args: str):
    return subprocess.run([sys.executable, str(TOOL_PATH), *args], capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT))


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"memory-usage tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_record_and_summary_json():
    project = make_project()
    try:
        result = run_tool(
            "record",
            "MEM_F_C_003",
            "--project",
            project.name,
            "--source",
            "framework",
            "--task",
            "fix test failure",
            "--outcome",
            "helped",
            "--note",
            "prevented assertion edits",
            "--json",
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["data"]["event"]["outcome"] == "helped"

        summary = run_tool("summary", "--project", project.name, "--json")
        assert summary.returncode == 0, summary.stderr
        data = json.loads(summary.stdout)["data"]
        assert data["total"] == 1
        assert data["by_outcome"]["helped"] == 1
        assert data["by_memory"]["MEM_F_C_003"]["helped"] == 1
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_prune_and_deprecate_flow():
    project = make_project()
    try:
        for outcome in ["misled", "stale"]:
            result = run_tool(
                "record",
                "MEM_BAD_001",
                "--project",
                project.name,
                "--source",
                "project",
                "--outcome",
                outcome,
                "--json",
            )
            assert result.returncode == 0, result.stderr

        prune = run_tool("prune", "--project", project.name, "--json")
        assert prune.returncode == 0, prune.stderr
        recommendations = json.loads(prune.stdout)["data"]["recommendations"]
        bad = [item for item in recommendations if item["memory_id"] == "MEM_BAD_001"][0]
        assert bad["action"] == "deprecate"

        deprecated = run_tool(
            "deprecate",
            "MEM_BAD_001",
            "--project",
            project.name,
            "--reason",
            "misled twice",
            "--json",
        )
        assert deprecated.returncode == 0, deprecated.stderr
        assert (project / "memory" / "memory_deprecations.jsonl").exists()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_memory_update_skill_references_effectiveness_tracking():
    content = MEMORY_UPDATE.read_text(encoding="utf-8")
    assert ".claude/tools/memory-usage/run.py" in content
    assert "helped" in content and "misled" in content and "stale" in content
    assert "prune" in content and "deprecate" in content


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_record_and_summary_json,
        test_prune_and_deprecate_flow,
        test_memory_update_skill_references_effectiveness_tracking,
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
