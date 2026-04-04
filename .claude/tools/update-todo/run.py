#!/usr/bin/env python3
"""
update-todo/run.py

用途:
  /DEV_SDD:update-todo 的执行辅助 CLI。
  以 docs/plan.json 为权威状态源，按稳定 ID 合并 docs/TODO.md 的工具管理区，
  并保留用户备注区；冲突时返回结构化 confirmation metadata。

用法:
  python3 .claude/tools/update-todo/run.py [project-name-or-path] [--ids T-001,T-003] [--json] [--dry-run]
  python3 .claude/tools/update-todo/run.py [project-name-or-path] --confirm-overwrite <token>

示例:
  python3 .claude/tools/update-todo/run.py structured-light-stereo --json --dry-run
  python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/partial-merge-project --ids T-002,T-004 --json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
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

MANAGED_BEGIN = workflow_cli_common.MANAGED_BEGIN
MANAGED_END = workflow_cli_common.MANAGED_END
NOTES_BEGIN = workflow_cli_common.NOTES_BEGIN
NOTES_END = workflow_cli_common.NOTES_END

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
    print("[UPDATE_TODO]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"计划源: {data.get('plan_source', 'docs/plan.json')}")
    print(f"TODO: {data.get('todo_path', 'docs/TODO.md')}")
    print(f"dry-run: {'yes' if data.get('dry_run') else 'no'}")
    print(f"IDs: {', '.join(data.get('selected_ids', [])) or 'ALL'}")
    print(f"写入: {', '.join(item.get('path', '') for item in data.get('writes', [])) or '无'}")
    confirmation = data.get("confirmation") or {}
    if confirmation.get("required"):
        print(f"确认: required ({confirmation.get('token', '')})")
    print("[/UPDATE_TODO]")


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


def resolve_target(target_arg: str | None) -> tuple[Path | None, str | None]:
    return workflow_cli_common.resolve_target_project(target_arg, ROOT)


def parse_ids(raw_ids: str | None) -> list[str]:
    if not raw_ids:
        return []
    result: list[str] = []
    seen: set[str] = set()
    for part in raw_ids.split(","):
        item = part.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def icon_to_state(icon: str) -> str:
    normalized = icon.lower()
    if normalized == "x":
        return "completed"
    if icon == ">":
        return "in_progress"
    if icon == "~":
        return "skipped"
    return "pending"


def render_task_line(task_id: str, name: str, state: str) -> str:
    return workflow_cli_common.render_task_line(task_id, name, state)


def render_managed_todo(project: str, tasks: list[dict[str, str]]) -> str:
    return workflow_cli_common.render_managed_todo(project, tasks)


def render_legacy_baseline_todo(project: str, plan: dict[str, Any]) -> str:
    modules = [m for b in plan.get("batches", []) for m in b.get("modules", [])]
    active = [m.get("name", "") for m in modules if m.get("state") in {"pending", "in_progress"}]
    current = active[0] if active else "全部模块已完成，进入 validate-output"
    upcoming = active[1:3] or ["补充验收记录", "执行最终验证"]

    lines = [
        f"# {project} · 任务跟踪",
        "",
        "> ⚠️ 执行状态以 `docs/plan.json` 为准；此文件仅记录项目级备注、审计和人工跟进。",
        "",
        "---",
        "",
        "## 进行中",
        f"- [ ] {current}",
        "",
        "---",
        "",
        "## 待办",
    ]
    for item in upcoming:
        lines.append(f"- [ ] {item}")
    lines.extend([
        "",
        "---",
        "",
        "## 已完成",
        "<!-- 完成后移入此区 -->",
        "",
        "---",
        "",
        "## 已知问题",
        "<!-- 发现但暂不修复的问题 -->",
        "",
    ])
    return "\n".join(lines)


def build_confirmation_token(target_root: Path, conflicts: list[dict[str, Any]]) -> str:
    seed_parts = [f"{item.get('reason','')}:{item.get('id','')}:{item.get('line','')}" for item in conflicts]
    seed = f"{target_root.resolve()}|{'|'.join(sorted(seed_parts))}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


def ensure_stable_ids(plan: dict[str, Any]) -> tuple[list[dict[str, str]], bool, list[dict[str, Any]]]:
    modules = [m for b in plan.get("batches", []) for m in b.get("modules", []) if isinstance(m, dict)]
    used_ids: set[str] = set()
    duplicate_conflicts: list[dict[str, Any]] = []
    max_seq = 0
    for module in modules:
        current_id = str(module.get("id") or "").strip()
        if not current_id:
            continue
        if current_id in used_ids:
            duplicate_conflicts.append({
                "reason": "duplicate_plan_id",
                "id": current_id,
                "module": module.get("name", ""),
            })
            continue
        used_ids.add(current_id)
        m = re.fullmatch(r"T-(\d+)", current_id)
        if m:
            max_seq = max(max_seq, int(m.group(1)))

    changed = False
    next_seq = max_seq + 1
    for module in modules:
        current_id = str(module.get("id") or "").strip()
        if current_id:
            continue
        while f"T-{next_seq:03d}" in used_ids:
            next_seq += 1
        assigned = f"T-{next_seq:03d}"
        module["id"] = assigned
        used_ids.add(assigned)
        next_seq += 1
        changed = True

    tasks: list[dict[str, str]] = []
    for module in modules:
        tasks.append({
            "id": str(module.get("id")),
            "name": str(module.get("name") or ""),
            "state": str(module.get("state") or "pending"),
        })
    return tasks, changed, duplicate_conflicts


def parse_managed_todo(content: str) -> dict[str, Any]:
    mb = content.find(MANAGED_BEGIN)
    me = content.find(MANAGED_END)
    nb = content.find(NOTES_BEGIN)
    ne = content.find(NOTES_END)
    if min(mb, me, nb, ne) < 0:
        return {"ok": False, "reason": "missing_zone_markers"}
    if not (mb < me < nb < ne):
        return {"ok": False, "reason": "invalid_zone_order"}

    mb_line_end = content.find("\n", mb)
    if mb_line_end < 0:
        return {"ok": False, "reason": "invalid_zone_markers"}
    managed_start = mb_line_end + 1
    managed_end = me
    managed_inner = content[managed_start:managed_end]
    managed_lines = managed_inner.splitlines()
    had_trailing_newline = managed_inner.endswith("\n")

    parsed_items: dict[str, dict[str, Any]] = {}
    line_ids: list[str] = []
    conflicts: list[dict[str, Any]] = []

    for idx, line in enumerate(managed_lines):
        stripped = line.strip()
        if not stripped:
            line_ids.append("")
            continue
        m = TASK_LINE_RE.match(line)
        if not m:
            conflicts.append({
                "reason": "unparseable_managed_line",
                "line": idx + 1,
                "content": line,
            })
            line_ids.append("")
            continue
        icon, display_name, task_id, meta_name, meta_state = m.groups()
        if task_id in parsed_items:
            conflicts.append({
                "reason": "duplicate_todo_id",
                "id": task_id,
                "line": idx + 1,
            })
        parsed_items[task_id] = {
            "line_index": idx,
            "raw_line": line,
            "display_name": display_name.strip(),
            "display_state": icon_to_state(icon),
            "meta_name": meta_name.strip(),
            "meta_state": meta_state.strip(),
        }
        line_ids.append(task_id)

    return {
        "ok": True,
        "managed_start": managed_start,
        "managed_end": managed_end,
        "managed_lines": managed_lines,
        "had_trailing_newline": had_trailing_newline,
        "items": parsed_items,
        "line_ids": line_ids,
        "conflicts": conflicts,
    }


def compute_writes(todo_exists: bool, todo_before: str, todo_after: str, plan_changed: bool) -> list[dict[str, str]]:
    writes: list[dict[str, str]] = []
    plan_action = "maintain"
    if plan_changed:
        plan_action = "overwrite"
    writes.append({"path": "docs/plan.json", "action": plan_action})

    if not todo_exists:
        todo_action = "create"
    elif todo_before == todo_after:
        todo_action = "maintain"
    else:
        todo_action = "overwrite"
    writes.append({"path": "docs/TODO.md", "action": todo_action})
    return writes


def run(target_arg: str | None, ids_raw: str | None, dry_run: bool, confirm_overwrite: str | None) -> dict[str, Any]:
    target_root, target_label = resolve_target(target_arg)
    if target_root is None:
        return {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，也未提供目标路径，无法执行 UPDATE_TODO",
            "data": {
                "project": None,
                "dry_run": dry_run,
                "next_action": "传入项目路径，或先执行 /project:switch <name>",
            },
        }

    if not target_root.exists():
        return {
            "status": STATUS_ERROR,
            "message": f"目标项目目录不存在：{target_root}",
            "data": {
                "project": target_label,
                "project_root": str(target_root),
                "dry_run": dry_run,
                "next_action": "先创建项目目录，并确保其中包含 docs/plan.json",
            },
        }

    plan_path = target_root / "docs" / "plan.json"
    if not plan_path.exists():
        return {
            "status": STATUS_ERROR,
            "message": f"缺少执行真相源：{plan_path}",
            "data": {
                "project": target_label,
                "project_root": rel_path(target_root, ROOT),
                "dry_run": dry_run,
                "next_action": "先通过 INIT/REDEFINE 生成 docs/plan.json",
            },
        }

    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "status": STATUS_ERROR,
            "message": f"plan.json 解析失败: {exc}",
            "data": {
                "project": target_label,
                "project_root": rel_path(target_root, ROOT),
                "dry_run": dry_run,
                "next_action": "修复 docs/plan.json 的 JSON 格式后重试",
            },
        }

    tasks, plan_changed, plan_conflicts = ensure_stable_ids(plan)
    if plan_conflicts:
        return {
            "status": STATUS_ERROR,
            "message": "plan.json 中存在重复 stable ID，无法安全合并 TODO",
            "data": {
                "project": str(plan.get("project") or target_label),
                "project_root": rel_path(target_root, ROOT),
                "plan_source": "docs/plan.json",
                "todo_path": "docs/TODO.md",
                "dry_run": dry_run,
                "conflicts": plan_conflicts,
                "next_action": "修复 docs/plan.json 的重复 id 后重试",
            },
        }

    task_by_id = {task["id"]: task for task in tasks}
    selected_ids = parse_ids(ids_raw) or [task["id"] for task in tasks]
    missing_selected = [item for item in selected_ids if item not in task_by_id]
    if missing_selected:
        return {
            "status": STATUS_ERROR,
            "message": "请求更新的 stable ID 不存在于 plan.json",
            "data": {
                "project": str(plan.get("project") or target_label),
                "project_root": rel_path(target_root, ROOT),
                "plan_source": "docs/plan.json",
                "todo_path": "docs/TODO.md",
                "dry_run": dry_run,
                "selected_ids": selected_ids,
                "missing_ids": missing_selected,
                "next_action": "使用存在于 docs/plan.json 的任务 ID 重新执行",
            },
        }

    todo_path = target_root / "docs" / "TODO.md"
    todo_exists = todo_path.exists()
    todo_before = safe_read_text(todo_path) if todo_exists else ""
    generated_full = render_managed_todo(str(plan.get("project") or target_label), tasks)

    conflicts: list[dict[str, Any]] = []
    todo_after = todo_before
    merge_mode = "managed"

    if not todo_exists:
        merge_mode = "full_regenerate"
        todo_after = generated_full
    else:
        parsed = parse_managed_todo(todo_before)
        if not parsed.get("ok"):
            legacy = render_legacy_baseline_todo(str(plan.get("project") or target_label), plan)
            if todo_before == legacy or not todo_before.strip():
                merge_mode = "full_regenerate"
                todo_after = generated_full
            else:
                merge_mode = "requires_confirmation"
                conflicts.append({
                    "reason": "non_managed_todo_requires_full_regenerate",
                    "id": "*",
                    "detail": parsed.get("reason", "parse_failed"),
                })
        else:
            conflicts.extend(parsed.get("conflicts", []))

            items = parsed["items"]
            managed_lines = list(parsed["managed_lines"])
            line_ids = parsed["line_ids"]

            for selected_id in selected_ids:
                if selected_id in items:
                    item = items[selected_id]
                    local_edit = (
                        item["display_name"] != item["meta_name"]
                        or item["display_state"] != item["meta_state"]
                    )
                    if local_edit:
                        conflicts.append({
                            "reason": "local_managed_edit",
                            "id": selected_id,
                            "line": item["line_index"] + 1,
                            "current": item["raw_line"],
                            "proposed": render_task_line(selected_id, task_by_id[selected_id]["name"], task_by_id[selected_id]["state"]),
                        })

            for todo_id in [tid for tid in line_ids if tid]:
                if todo_id not in task_by_id:
                    conflicts.append({
                        "reason": "orphan_local_item",
                        "id": todo_id,
                    })

            if not conflicts or (confirm_overwrite and confirm_overwrite == build_confirmation_token(target_root, conflicts)):
                id_to_line = {
                    task_id: render_task_line(task_id, task_by_id[task_id]["name"], task_by_id[task_id]["state"])
                    for task_id in selected_ids
                }
                for task_id, line in id_to_line.items():
                    if task_id in items:
                        managed_lines[items[task_id]["line_index"]] = line
                    else:
                        managed_lines.append(line)

                inner = "\n".join(managed_lines)
                if parsed["had_trailing_newline"] and (inner or parsed["managed_lines"]):
                    inner += "\n"
                todo_after = todo_before[: parsed["managed_start"]] + inner + todo_before[parsed["managed_end"] :]

    data: dict[str, Any] = {
        "project": str(plan.get("project") or target_label),
        "project_root": rel_path(target_root, ROOT),
        "plan_source": "docs/plan.json",
        "todo_path": "docs/TODO.md",
        "dry_run": dry_run,
        "selected_ids": selected_ids,
        "merge_mode": merge_mode,
    }

    if conflicts:
        token = build_confirmation_token(target_root, conflicts)
        confirmation = {
            "required": True,
            "token": token,
            "conflicts": conflicts,
            "next_action": f"使用 --confirm-overwrite {token} 重新执行 UPDATE_TODO",
        }
        data["confirmation"] = confirmation
        if confirm_overwrite != token:
            data["writes"] = compute_writes(todo_exists, todo_before, todo_before, False)
            return {
                "status": STATUS_WARNING,
                "message": "检测到本地冲突或不可安全重建场景，需确认后才能覆盖",
                "data": data,
            }

    writes = compute_writes(todo_exists, todo_before, todo_after, plan_changed)
    data["writes"] = writes

    if not dry_run:
        if plan_changed:
            plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if (not todo_exists) or (todo_before != todo_after):
            todo_path.parent.mkdir(parents=True, exist_ok=True)
            todo_path.write_text(todo_after, encoding="utf-8")

    return {
        "status": STATUS_OK,
        "message": "UPDATE_TODO 预览完成：已按 stable ID 计算合并结果" if dry_run else "UPDATE_TODO 已完成：按 stable ID 更新 TODO 并保留用户备注区",
        "data": data,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:update-todo 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  基于 docs/plan.json 的稳定 ID 合并 docs/TODO.md 的工具管理区，
  支持按 --ids 进行部分更新，并在冲突时返回 confirmation metadata。

示例:
  python3 .claude/tools/update-todo/run.py structured-light-stereo --json --dry-run
  python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/partial-merge-project --ids T-002,T-004 --json
  python3 .claude/tools/update-todo/run.py skill-tests/fixtures/update_todo/conflict-project --ids T-003 --confirm-overwrite <token>
""",
    )
    parser.add_argument("project", nargs="?", help="可选：目标项目名或项目根目录路径")
    parser.add_argument("--ids", default=None, help="可选：仅更新指定 stable IDs，逗号分隔")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    parser.add_argument("--dry-run", action="store_true", help="仅预览将写入的文件，不实际落盘")
    parser.add_argument("--confirm-overwrite", default=None, help="冲突确认 token")
    args = parser.parse_args()

    result = run(args.project, args.ids, args.dry_run, args.confirm_overwrite)
    out(result, args.json)

    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
