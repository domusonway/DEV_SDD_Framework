#!/usr/bin/env python3
from __future__ import annotations

"""
skill-tests/cases/test_plan_tracker_completion_guard.py
Layer 1: plan-tracker 完成态保护测试

用途:
  验证 plan-tracker 在标记完成或 validate 前，会调用 check_impl.py 阻止空实现混入完成态。
"""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TRACKER = FRAMEWORK_ROOT / ".claude/tools/plan-tracker/tracker.py"


def run_tracker(workspace_root: Path, *args: str):
    return subprocess.run(
        [sys.executable, str(TRACKER), *args],
        capture_output=True,
        text=True,
        cwd=str(workspace_root),
    )


def make_workspace(module_body: str) -> tuple[Path, Path]:
    workspace_root = Path(tempfile.mkdtemp(prefix="plan_tracker_guard_"))
    project_name = "demo_project"
    project_root = workspace_root / "projects" / project_name
    module_dir = project_root / "modules" / "backend" / "demo"
    docs_dir = project_root / "docs"

    module_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    (workspace_root / "CLAUDE.md").write_text(
        f"PROJECT: {project_name}\nPROJECT_PATH: projects/{project_name}\n",
        encoding="utf-8",
    )
    (module_dir / "demo.py").write_text(module_body, encoding="utf-8")
    (docs_dir / "plan.json").write_text(
        json.dumps(
            {
                "project": "demo_project",
                "batches": [
                    {
                        "name": "Batch 1",
                        "modules": [
                            {
                                "id": "T-001",
                                "name": "demo",
                                "path": "modules/backend/demo",
                                "state": "pending",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return workspace_root, project_root


def make_parallel_workspace() -> tuple[Path, Path]:
    workspace_root = Path(tempfile.mkdtemp(prefix="plan_tracker_parallel_"))
    project_name = "demo_project"
    project_root = workspace_root / "projects" / project_name
    docs_dir = project_root / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    (workspace_root / "CLAUDE.md").write_text(
        f"PROJECT: {project_name}\nPROJECT_PATH: projects/{project_name}\n",
        encoding="utf-8",
    )
    (docs_dir / "plan.json").write_text(
        json.dumps(
            {
                "project": "demo_project",
                "batches": [
                    {
                        "name": "Batch 1",
                        "modules": [
                            {"id": "T-001", "name": "shared", "state": "completed"},
                            {
                                "id": "T-002",
                                "name": "lane_a",
                                "state": "pending",
                                "deps": ["shared"],
                                "writes": ["contracts/runtime.json"],
                            },
                            {
                                "id": "T-003",
                                "name": "lane_b",
                                "state": "pending",
                                "deps": ["shared"],
                                "writes": ["contracts/runtime.json"],
                            },
                            {
                                "id": "T-004",
                                "name": "merge",
                                "state": "pending",
                                "deps": ["lane_a", "lane_b"],
                            },
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return workspace_root, project_root


def test_complete_rejects_stub_module():
    workspace_root, project_root = make_workspace(
        "def run_demo(value: int) -> int:\n    pass\n"
    )
    try:
        result = run_tracker(workspace_root, "--json", "complete", "demo")
        assert result.returncode == 1, f"stub 模块应拒绝完成: {result.stdout}\n{result.stderr}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "error"
        assert "未通过实现完整性检查" in payload["message"]

        plan = json.loads((project_root / "docs" / "plan.json").read_text(encoding="utf-8"))
        assert plan["batches"][0]["modules"][0]["state"] == "pending", "失败时不应修改计划状态"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_complete_accepts_real_module_and_updates_plan():
    workspace_root, project_root = make_workspace(
        "def run_demo(value: int) -> int:\n    return value + 1\n"
    )
    try:
        result = run_tracker(workspace_root, "--json", "complete", "demo")
        assert result.returncode == 0, f"完整实现应允许完成: {result.stdout}\n{result.stderr}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "ok"

        plan = json.loads((project_root / "docs" / "plan.json").read_text(encoding="utf-8"))
        module = plan["batches"][0]["modules"][0]
        assert module["state"] == "completed"
        assert module.get("completed_at"), "完成后应写入 completed_at"
        assert (project_root / "docs" / "PLAN.md").exists(), "完成后应重建 PLAN.md"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_validate_rejects_completed_stub_module():
    workspace_root, project_root = make_workspace(
        "def run_demo(value: int) -> int:\n    pass\n"
    )
    try:
        plan = json.loads((project_root / "docs" / "plan.json").read_text(encoding="utf-8"))
        plan["batches"][0]["modules"][0]["state"] = "completed"
        (project_root / "docs" / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")

        result = run_tracker(workspace_root, "--json", "validate")
        assert result.returncode == 1, f"validate 应拒绝 completed stub: {result.stdout}\n{result.stderr}"
        payload = json.loads(result.stdout)
        assert payload["status"] == "error"
        invalid_modules = payload["data"].get("invalid_modules", [])
        assert invalid_modules and invalid_modules[0]["module"] == "demo"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_parallel_next_conflicts_and_critical_path_commands():
    workspace_root, project_root = make_parallel_workspace()
    try:
        next_result = run_tracker(workspace_root, "next", "--parallel", "--json")
        assert next_result.returncode == 0, next_result.stderr
        next_payload = json.loads(next_result.stdout)
        ready_names = {task["name"] for task in next_payload["data"]["ready_tasks"]}
        assert ready_names == {"lane_a", "lane_b"}, f"ready task pool 错误: {ready_names}"

        conflicts_result = run_tracker(workspace_root, "conflicts", "--json")
        assert conflicts_result.returncode == 0, conflicts_result.stderr
        conflicts_payload = json.loads(conflicts_result.stdout)
        assert conflicts_payload["status"] == "warning", "共享写入冲突应返回 warning"
        assert conflicts_payload["data"]["conflict_count"] == 1

        path_result = run_tracker(workspace_root, "critical-path", "--json")
        assert path_result.returncode == 0, path_result.stderr
        path_payload = json.loads(path_result.stdout)
        assert path_payload["data"]["max_depth"] == 3, "merge 应处于 critical depth 3"
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_lock_and_release_parallel_module():
    workspace_root, project_root = make_parallel_workspace()
    try:
        lock_result = run_tracker(workspace_root, "lock", "lane_a", "--owner", "agent-a", "--json")
        assert lock_result.returncode == 0, lock_result.stderr
        lock_payload = json.loads(lock_result.stdout)
        assert lock_payload["data"]["lock"]["owner"] == "agent-a"

        plan = json.loads((project_root / "docs" / "plan.json").read_text(encoding="utf-8"))
        lane_a = [m for b in plan["batches"] for m in b["modules"] if m["name"] == "lane_a"][0]
        assert lane_a["lock"]["owner"] == "agent-a"

        conflict_lock = run_tracker(workspace_root, "lock", "lane_a", "--owner", "agent-b", "--json")
        assert conflict_lock.returncode == 1, "其他 owner 不应覆盖已有锁"

        release_result = run_tracker(workspace_root, "release", "lane_a", "--owner", "agent-a", "--json")
        assert release_result.returncode == 0, release_result.stderr
        plan = json.loads((project_root / "docs" / "plan.json").read_text(encoding="utf-8"))
        lane_a = [m for b in plan["batches"] for m in b["modules"] if m["name"] == "lane_a"][0]
        assert "lock" not in lane_a
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_complete_rejects_stub_module,
        test_complete_accepts_real_module_and_updates_plan,
        test_validate_rejects_completed_stub_module,
        test_parallel_next_conflicts_and_critical_path_commands,
        test_lock_and_release_parallel_module,
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
