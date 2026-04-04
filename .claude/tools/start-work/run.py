#!/usr/bin/env python3
"""
start-work/run.py

用途:
  /DEV_SDD:start-work 的执行辅助 CLI。
  统一探测项目上下文、Session 续接状态、计划进度和下一步动作。

用法:
  python3 .claude/tools/start-work/run.py [project-name] [--json]

示例:
  python3 .claude/tools/start-work/run.py
  python3 .claude/tools/start-work/run.py structured-light-stereo
  python3 .claude/tools/start-work/run.py --json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)


STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"

MANAGED_BEGIN = "<!-- DEV_SDD:MANAGED:BEGIN -->"
MANAGED_END = "<!-- DEV_SDD:MANAGED:END -->"

TASK_LINE_RE = re.compile(
    r"^\s*-\s*\[([ xX>~])\]\s*(.*?)\s*<!--\s*DEV_SDD:TASK:id=([^;]+);name=([^;]+);state=([a-z_]+)\s*-->\s*$"
)


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    print("[START-WORK]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"Session: {data.get('session', {}).get('state', 'unknown')}")
    print(f"模式: {data.get('mode', {}).get('detected', 'unknown')}")
    print(f"计划: {data.get('plan', {}).get('summary', '无可用计划信息')}")
    print(f"下一步: {data.get('next_action', '请先补齐项目上下文')}")
    print("[/START-WORK]")


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    m = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if m:
        return m.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def detect_mode(project_claude: Path) -> dict[str, str]:
    content = safe_read_text(project_claude)
    if not content:
        return {"detected": "unknown", "source": "missing"}

    m = re.search(r"工作模式:\s*([LMH])", content)
    if m:
        return {"detected": m.group(1), "source": "projects/<PROJECT>/CLAUDE.md"}

    m2 = re.search(r"工作模式:\s*([^\n|]+)", content)
    if m2:
        raw = m2.group(1).strip()
        maybe = raw[0].upper() if raw else "unknown"
        return {"detected": maybe if maybe in {"L", "M", "H"} else raw, "source": "projects/<PROJECT>/CLAUDE.md"}
    return {"detected": "unknown", "source": "unparsed"}


@dataclass
class PlanResult:
    source: str
    summary: str
    next_action: str
    progress: dict[str, Any]
    nodes: list[dict[str, str]]


def _compute_next_action_from_batches(plan: dict[str, Any]) -> str:
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            state = module.get("state", "pending")
            if state in {"pending", "in_progress"}:
                return f"实现 {module.get('name', 'unknown')}（{batch.get('name', 'unknown')}）"
    return "所有模块已完成，可进入 validate-output"


def _load_plan_json(path: Path) -> PlanResult | None:
    if not path.exists():
        return None
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return PlanResult(
            source="plan.json",
            summary="plan.json 存在但解析失败",
            next_action="修复 docs/plan.json 的 JSON 格式错误",
            progress={"completed": 0, "total": 0, "percent": 0},
            nodes=[],
        )

    all_modules = [m for b in plan.get("batches", []) for m in b.get("modules", [])]
    total = len(all_modules)
    completed = sum(1 for m in all_modules if m.get("state") == "completed")
    in_progress = sum(1 for m in all_modules if m.get("state") == "in_progress")
    pending = sum(1 for m in all_modules if m.get("state", "pending") == "pending")
    percent = round(completed / total * 100) if total else 0
    next_action = _compute_next_action_from_batches(plan)
    nodes: list[dict[str, str]] = []
    for module in all_modules:
        module_id = str(module.get("id") or "").strip()
        if not module_id:
            continue
        nodes.append({
            "id": module_id,
            "name": str(module.get("name") or ""),
            "state": str(module.get("state") or "pending"),
        })
    return PlanResult(
        source="plan.json",
        summary=f"{completed}/{total} 完成（{percent}%）",
        next_action=next_action,
        progress={
            "completed": completed,
            "in_progress": in_progress,
            "pending": pending,
            "total": total,
            "percent": percent,
        },
        nodes=nodes,
    )


def _extract_task_name(line: str) -> str:
    text = re.sub(r"^-\s*\[[ xX~>]\]\s*", "", line).strip()
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text.strip() or "未命名任务"


def _load_plan_markdown(path: Path) -> PlanResult | None:
    if not path.exists():
        return None
    content = safe_read_text(path)
    if not content:
        return PlanResult(
            source=path.name,
            summary=f"{path.name} 存在但无法读取",
            next_action=f"检查 {path.name} 文件权限或编码",
            progress={"completed": 0, "pending": 0, "in_progress": 0, "total": 0, "percent": 0},
            nodes=[],
        )

    completed_lines = re.findall(r"^-\s*\[[xX]\]\s+.+$", content, re.MULTILINE)
    pending_lines = re.findall(r"^-\s*\[\s\]\s+.+$", content, re.MULTILINE)
    active_lines = re.findall(r"^-\s*\[>\]\s+.+$", content, re.MULTILINE)
    total = len(completed_lines) + len(pending_lines) + len(active_lines)
    percent = round(len(completed_lines) / total * 100) if total else 0

    if active_lines:
        next_action = f"继续 {_extract_task_name(active_lines[0])}"
    elif pending_lines:
        next_action = f"开始 {_extract_task_name(pending_lines[0])}"
    else:
        next_action = "阅读计划文档并定义第一个可执行模块"

    return PlanResult(
        source=path.name,
        summary=f"{len(completed_lines)}/{total} 完成（{percent}%）",
        next_action=next_action,
        progress={
            "completed": len(completed_lines),
            "in_progress": len(active_lines),
            "pending": len(pending_lines),
            "total": total,
            "percent": percent,
        },
        nodes=[],
    )


def detect_plan(project_docs: Path) -> PlanResult:
    prioritized: list[tuple[str, Path]] = [
        ("plan.json", project_docs / "plan.json"),
        ("PLAN.md", project_docs / "PLAN.md"),
        ("IMPLEMENTATION_PLAN.md", project_docs / "IMPLEMENTATION_PLAN.md"),
    ]

    json_result = _load_plan_json(prioritized[0][1])
    if json_result is not None:
        return json_result

    for _, path in prioritized[1:]:
        md_result = _load_plan_markdown(path)
        if md_result is not None:
            return md_result

    return PlanResult(
        source="none",
        summary="未检测到 plan.json / PLAN.md / IMPLEMENTATION_PLAN.md",
        next_action="先补齐 BRIEF.md 或 CONTEXT.md + SPEC.md + 计划文件",
        progress={"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
        nodes=[],
    )


def _sort_warnings(warnings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(warnings, key=lambda item: (
        str(item.get("reason") or ""),
        str(item.get("id") or ""),
        int(item.get("line") or 0),
        str(item.get("detail") or ""),
    ))


def reconcile_todo(project_root: Path, plan: PlanResult) -> dict[str, Any]:
    base = {
        "status": "skipped",
        "matched_ids": [],
        "orphan_ids": [],
        "conflict_ids": [],
        "missing_ids": [],
        "warnings": [],
    }

    if plan.source != "plan.json":
        base["warnings"] = [{"reason": "reconciliation_requires_plan_json", "source": plan.source}]
        return base

    plan_by_id: dict[str, dict[str, str]] = {}
    warnings: list[dict[str, Any]] = []
    for node in plan.nodes:
        task_id = str(node.get("id") or "").strip()
        if not task_id:
            continue
        if task_id in plan_by_id:
            warnings.append({"reason": "duplicate_plan_id", "id": task_id})
            continue
        plan_by_id[task_id] = {
            "name": str(node.get("name") or ""),
            "state": str(node.get("state") or "pending"),
        }

    todo_path = project_root / "docs" / "TODO.md"
    if not todo_path.exists():
        missing_ids = sorted(plan_by_id.keys())
        warnings.append({"reason": "todo_missing", "path": "docs/TODO.md"})
        return {
            "status": "todo_missing",
            "matched_ids": [],
            "orphan_ids": [],
            "conflict_ids": [],
            "missing_ids": missing_ids,
            "warnings": _sort_warnings(warnings),
        }

    content = safe_read_text(todo_path)
    mb = content.find(MANAGED_BEGIN)
    me = content.find(MANAGED_END)
    if mb < 0 or me < 0 or mb >= me:
        warnings.extend([
            {"reason": "managed_todo_block_missing", "path": "docs/TODO.md"},
            *({"reason": "missing_todo_id", "id": task_id} for task_id in sorted(plan_by_id.keys())),
        ])
        return {
            "status": "mismatch",
            "matched_ids": [],
            "orphan_ids": [],
            "conflict_ids": [],
            "missing_ids": sorted(plan_by_id.keys()),
            "warnings": _sort_warnings(warnings),
        }

    managed_start = content.find("\n", mb)
    if managed_start < 0:
        managed_start = me
    else:
        managed_start += 1
    managed_lines = content[managed_start:me].splitlines()

    parsed_items: dict[str, dict[str, str]] = {}
    duplicate_ids: set[str] = set()
    for idx, line in enumerate(managed_lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        m = TASK_LINE_RE.match(line)
        if not m:
            continue
        _, display_name, task_id, meta_name, meta_state = m.groups()
        if task_id in parsed_items:
            duplicate_ids.add(task_id)
            warnings.append({"reason": "duplicate_todo_id", "id": task_id, "line": idx})
            continue
        parsed_items[task_id] = {
            "display_name": display_name.strip(),
            "meta_name": meta_name.strip(),
            "meta_state": meta_state.strip(),
        }

    matched_ids: list[str] = []
    orphan_ids: list[str] = []
    conflict_ids: list[str] = []
    missing_ids: list[str] = []

    for task_id, item in parsed_items.items():
        plan_node = plan_by_id.get(task_id)
        if plan_node is None:
            orphan_ids.append(task_id)
            warnings.append({"reason": "orphan_todo_id", "id": task_id})
            continue

        has_conflict = False
        if item["meta_state"] != plan_node["state"]:
            warnings.append({
                "reason": "state_mismatch",
                "id": task_id,
                "todo": item["meta_state"],
                "plan": plan_node["state"],
            })
            has_conflict = True
        if item["meta_name"] != plan_node["name"]:
            warnings.append({
                "reason": "name_mismatch",
                "id": task_id,
                "todo": item["meta_name"],
                "plan": plan_node["name"],
            })
            has_conflict = True

        if has_conflict:
            conflict_ids.append(task_id)
        else:
            matched_ids.append(task_id)

    for task_id in sorted(plan_by_id.keys()):
        if task_id not in parsed_items:
            missing_ids.append(task_id)
            warnings.append({"reason": "missing_todo_id", "id": task_id})

    conflict_ids.extend(sorted(duplicate_ids))
    status = "aligned" if not warnings else "mismatch"
    return {
        "status": status,
        "matched_ids": sorted(set(matched_ids)),
        "orphan_ids": sorted(set(orphan_ids)),
        "conflict_ids": sorted(set(conflict_ids)),
        "missing_ids": sorted(set(missing_ids)),
        "warnings": _sort_warnings(warnings),
    }


def parse_handoff(handoff_path: Path) -> dict[str, Any] | None:
    if not handoff_path.exists():
        return None
    try:
        return json.loads(handoff_path.read_text(encoding="utf-8"))
    except Exception:
        return {"_invalid": True}


def parse_latest_session(session_dir: Path) -> dict[str, Any] | None:
    if not session_dir.exists():
        return None
    files = sorted(session_dir.glob("*.md"), reverse=True)
    if not files:
        return None
    latest = files[0]
    content = safe_read_text(latest)
    if not content:
        return {"file": str(latest), "status": "unknown", "task": "未知"}

    status = "in-progress" if "status: in-progress" in content else ("completed" if "status: completed" in content else "unknown")
    task_m = re.search(r"^task:\s*(.+)$", content, re.MULTILINE)
    next_m = re.search(r"^下次继续:\s*(.+)$", content, re.MULTILINE)
    return {
        "file": rel_path(latest, ROOT),
        "status": status,
        "task": task_m.group(1).strip() if task_m else "未记录",
        "next_step": next_m.group(1).strip() if next_m else "",
    }


def detect_session(project_root: Path, plan_next: str, plan_source: str) -> tuple[dict[str, Any], str, str]:
    handoff_path = project_root / "HANDOFF.json"
    handoff = parse_handoff(handoff_path)
    latest_session = parse_latest_session(project_root / "memory" / "sessions")

    if handoff is not None:
        if handoff.get("_invalid"):
            return ({
                "state": "RESUME",
                "handoff_exists": True,
                "handoff_valid": False,
                "latest_session": latest_session,
            }, "HANDOFF.json 存在但格式异常，先修复 HANDOFF.json 再继续", "HANDOFF.json")
        handoff_next = handoff.get("next_action")
        return ({
            "state": "RESUME",
            "handoff_exists": True,
            "handoff_valid": True,
            "handoff": {
                "timestamp": handoff.get("timestamp"),
                "last_completed_module": handoff.get("last_completed_module"),
                "current_state": handoff.get("current_state"),
                "next_action": handoff.get("next_action"),
            },
            "latest_session": latest_session,
        }, handoff_next or plan_next, "HANDOFF.json" if handoff_next else plan_source)

    if latest_session and latest_session.get("status") == "in-progress":
        return ({
            "state": "RESUME",
            "handoff_exists": False,
            "latest_session": latest_session,
        }, latest_session.get("next_step") or f"续接会话任务：{latest_session.get('task', '未记录任务')}", "session")

    return ({
        "state": "NEW SESSION",
        "handoff_exists": False,
        "latest_session": latest_session,
    }, plan_next, plan_source)


def build_context_files(root: Path, project_root: Path | None, project: str) -> dict[str, list[str]]:
    framework_files = [
        "memory/INDEX.md",
        "AGENTS.md",
    ]
    project_files: list[str] = []
    if project_root is not None:
        for path in [project_root / "CLAUDE.md", project_root / "memory" / "INDEX.md"]:
            if path.exists():
                project_files.append(rel_path(path, root))
    return {
        "framework": [p for p in framework_files if (root / p).exists()],
        "project": project_files,
    }


def run(project_arg: str | None) -> dict[str, Any]:
    active_project = detect_active_project(ROOT)
    project_root, target_label = workflow_cli_common.resolve_target_project(project_arg, ROOT)
    project = target_label or project_arg or active_project
    if not project:
        return {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，无法执行 start-work 上下文装配",
            "data": {
                "project": None,
                "context_files": {"framework": ["memory/INDEX.md", "AGENTS.md"], "project": []},
                "session": {"state": "NEW SESSION", "handoff_exists": False, "latest_session": None},
                "mode": {"detected": "unknown", "source": "missing_project"},
                "plan": {
                    "source": "none",
                    "summary": "无项目，未加载计划",
                    "progress": {"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
                    "next_action": "先执行 /project:new <name> 或 /project:switch <name>",
                },
                "next_action": "先执行 /project:new <name> 或 /project:switch <name>",
            },
        }

    context_files = build_context_files(ROOT, project_root, project)

    if project_root is None or not project_root.exists():
        next_action = f"项目 {project} 不存在；先执行 /project:new {project} 或 /project:switch <existing-project>"
        return {
            "status": STATUS_WARNING,
            "message": f"项目不存在：{project}",
            "data": {
                "project": project,
                "project_path": rel_path(project_root or (ROOT / "projects" / project), ROOT),
                "active_project": active_project,
                "context_files": context_files,
                "session": {"state": "NEW SESSION", "handoff_exists": False, "latest_session": None},
                "mode": {"detected": "unknown", "source": "missing_project_dir"},
                "plan": {
                    "source": "none",
                    "summary": "项目目录不存在，无法读取计划",
                    "progress": {"completed": 0, "in_progress": 0, "pending": 0, "total": 0, "percent": 0},
                    "next_action": next_action,
                },
                "next_action": next_action,
            },
        }

    mode = detect_mode(project_root / "CLAUDE.md")
    plan = detect_plan(project_root / "docs")
    reconciliation = reconcile_todo(project_root, plan)
    session, next_action, next_action_source = detect_session(project_root, plan.next_action, plan.source)

    status = STATUS_OK
    if mode.get("detected") == "unknown" or plan.source == "none" or reconciliation.get("status") in {"mismatch", "todo_missing"}:
        status = STATUS_WARNING

    return {
        "status": status,
        "message": f"start-work 检查完成：{project} | Session={session['state']} | Plan={plan.summary}",
            "data": {
                "project": project,
                "project_path": rel_path(project_root, ROOT),
                "active_project": active_project,
                "context_files": context_files,
                "session": session,
            "mode": mode,
            "plan": {
                "source": plan.source,
                "summary": plan.summary,
                "progress": plan.progress,
                "next_action": plan.next_action,
            },
            "reconciliation": reconciliation,
            "next_action": next_action,
            "next_action_source": next_action_source,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:start-work 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  生成 /DEV_SDD:start-work 所需的结构化上下文摘要。

示例:
  python3 .claude/tools/start-work/run.py
  python3 .claude/tools/start-work/run.py structured-light-stereo
  python3 .claude/tools/start-work/run.py --json
""",
    )
    parser.add_argument("project", nargs="?", help="可选：显式覆盖目标项目名或项目路径")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    args = parser.parse_args()

    result = run(args.project)
    out(result, args.json)

    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
