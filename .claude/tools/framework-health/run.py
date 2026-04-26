#!/usr/bin/env python3
from __future__ import annotations

"""Aggregate DEV_SDD framework health signals into one JSON-friendly report."""

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)


def _run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode != 0:
        return {
            "status": "error",
            "message": (result.stderr or result.stdout or "command failed").strip(),
            "data": None,
            "returncode": result.returncode,
        }
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "command did not return JSON",
            "data": {"stdout": result.stdout[:500], "stderr": result.stderr[:500]},
            "returncode": result.returncode,
        }


def _python_tool(*parts: str) -> list[str]:
    return [sys.executable, str(ROOT.joinpath(*parts))]


def collect_health(project: str | None, task: str = "") -> dict[str, Any]:
    project_args = [project] if project else []
    start_cmd = _python_tool(".claude", "tools", "start-work", "run.py") + project_args + ["--json"]
    if task:
        start_cmd += ["--task", task]

    signals = {
        "start_work": _run_json(start_cmd),
        "candidate_schema": _run_json(_python_tool(".claude", "tools", "skill-tracker", "tracker.py") + ["validate-schema", "--json"]),
        "candidate_review": _run_json(_python_tool(".claude", "tools", "skill-tracker", "tracker.py") + ["review-summary", "--json"]),
        "parallel_next": _run_json(_python_tool(".claude", "tools", "plan-tracker", "tracker.py") + ["next", "--parallel", "--json"]),
        "parallel_conflicts": _run_json(_python_tool(".claude", "tools", "plan-tracker", "tracker.py") + ["conflicts", "--json"]),
        "memory_prune": _run_json(_python_tool(".claude", "tools", "memory-usage", "run.py") + ["prune", "--json"] + (["--project", project] if project else [])),
        "memory_conflicts": _run_json(_python_tool(".claude", "tools", "memory-conflicts", "run.py") + ["--json"] + (["--project", project] if project else [])),
        "model_behavior": _run_json(_python_tool(".claude", "tools", "model-behavior", "run.py") + ["readiness", "--json"]),
    }

    issues = []
    schema_status = signals["candidate_schema"].get("status")
    if schema_status != "ok":
        issues.append({"level": "high", "source": "candidate_schema", "message": signals["candidate_schema"].get("message")})

    review_data = signals["candidate_review"].get("data") or {}
    review_items = review_data.get("items") or []
    actionable_count = sum(1 for item in review_items if item.get("recommendation") not in (None, "none"))
    if actionable_count:
        issues.append({"level": "medium", "source": "candidate_review", "message": f"{actionable_count} candidates require review"})

    conflict_data = signals["parallel_conflicts"].get("data") or {}
    conflict_count = int(conflict_data.get("conflict_count") or 0)
    if conflict_count:
        issues.append({"level": "high", "source": "parallel_conflicts", "message": f"{conflict_count} write conflicts detected"})

    prune_data = signals["memory_prune"].get("data") or {}
    deprecate_count = int(prune_data.get("deprecate_count") or 0)
    review_count = int(prune_data.get("review_count") or 0)
    if deprecate_count or review_count:
        issues.append({"level": "medium", "source": "memory_prune", "message": f"{deprecate_count} deprecate, {review_count} review recommendations"})

    memory_conflicts_data = signals["memory_conflicts"].get("data") or {}
    memory_conflict_count = int(memory_conflicts_data.get("conflict_count") or 0)
    if memory_conflict_count:
        issues.append({"level": "high", "source": "memory_conflicts", "message": f"{memory_conflict_count} memory conflicts require arbitration"})

    model_behavior_data = signals["model_behavior"].get("data") or {}
    model_behavior_issues = model_behavior_data.get("issues") or []
    high_model_issues = [issue for issue in model_behavior_issues if issue.get("level") == "high"]
    if high_model_issues:
        issues.append({"level": "high", "source": "model_behavior", "message": f"{len(high_model_issues)} blocking Layer2/Layer3 validation issues"})

    start_data = signals["start_work"].get("data") or {}
    if start_data.get("session", {}).get("stale_session_ignored"):
        issues.append({"level": "low", "source": "session", "message": "stale in-progress session ignored because plan is complete"})

    status = "ok"
    if any(issue["level"] == "high" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"

    return {
        "project": project or start_data.get("project"),
        "status": status,
        "issues": issues,
        "signals": signals,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD framework health dashboard")
    parser.add_argument("--project", default=None, help="project name/path, defaults to active project")
    parser.add_argument("--task", default="", help="task text for start-work context/prompt policy classification")
    parser.add_argument("--json", action="store_true", help="emit JSON envelope")
    args = parser.parse_args()

    data = collect_health(args.project, task=args.task)
    payload = {"status": data["status"], "message": f"framework health: {data['status']}", "data": data}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
        for issue in data["issues"]:
            print(f"- [{issue['level']}] {issue['source']}: {issue['message']}")
    return 1 if data["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
