#!/usr/bin/env python3
"""
redefine/run.py

用途:
  /DEV_SDD:redefine 的执行辅助 CLI。
  读取目标项目 docs/CONTEXT.md 的规划输入，重建 docs/plan.json，
  并按固定顺序重新生成 docs/PLAN.md 与 docs/TODO.md。

用法:
  python3 .claude/tools/redefine/run.py [project-name-or-path] [--json] [--dry-run]
  python3 .claude/tools/redefine/run.py --alias REDEFIND [project-name-or-path] [--json] [--dry-run]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime
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


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    print("[REDEFINE]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"输入: {data.get('input_source', 'docs/CONTEXT.md')}")
    print(f"计划源: {data.get('plan_source', 'docs/plan.json')}")
    print(f"dry-run: {'yes' if data.get('dry_run') else 'no'}")
    print(f"写入顺序: {', '.join(item.get('path', '') for item in data.get('writes', []))}")
    alias = data.get("alias") or {}
    if alias.get("used"):
        print(f"兼容别名: {alias.get('name')}")
    print("[/REDEFINE]")


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def resolve_target(target_arg: str | None) -> tuple[Path | None, str | None]:
    return workflow_cli_common.resolve_target_project(target_arg, ROOT)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def extract_section(content: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", content[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(content)
    return content[start:end].strip()


def parse_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            raw = stripped[2:].strip()
            return raw.split("·", 1)[0].strip() or fallback
    return fallback


def parse_deps(raw: str) -> list[str]:
    text = raw.strip()
    if not text or text in {"无", "None", "none", "-"}:
        return []
    parts = [item.strip(" `") for item in re.split(r"[、,，/]", text) if item.strip()]
    return [part for part in parts if part and part not in {"无", "None", "none"}]


def parse_modules(content: str) -> list[dict[str, Any]]:
    section = extract_section(content, "模块划分")
    if not section:
        return []

    matches = list(re.finditer(r"^(#{3,6})\s+(.+)$", section, re.MULTILINE))
    modules: list[dict[str, Any]] = []
    heading_stack: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        name = match.group(2).strip()
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        body = section[start:end]
        fields: dict[str, str] = {}
        for line in body.splitlines():
            field_match = re.match(r"^-\s*([^:：]+)[:：]\s*(.+)$", line.strip())
            if field_match:
                fields[field_match.group(1).strip()] = field_match.group(2).strip()
        if not fields:
            heading_stack.append((level, name))
            continue
        group = None
        for _, ancestor_name in reversed(heading_stack):
            cleaned = ancestor_name.strip().strip("/")
            if cleaned:
                group = cleaned
                break
        modules.append({
            "name": name,
            "path": f"modules/{group}/{name}" if group else f"modules/{name}",
            "deps": parse_deps(fields.get("依赖", "无")),
        })
        heading_stack.append((level, name))
    return modules


def build_batches(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = [dict(module) for module in modules]
    completed: set[str] = set()
    batches: list[dict[str, Any]] = []
    batch_no = 1

    while remaining:
        ready = [module for module in remaining if set(module.get("deps", [])) <= completed]
        if not ready:
            ready = list(remaining)

        batch_modules = []
        for module in ready:
            batch_modules.append({
                "name": module["name"],
                "complexity": "M",
                "risk": "" if set(module.get("deps", [])) <= completed else "依赖关系待整理",
                "deps": module.get("deps", []),
                "state": "pending",
                "completed_at": None,
            })
            completed.add(module["name"])

        batches.append({
            "name": f"批次 {batch_no}",
            "description": "无依赖，可并行实现" if batch_no == 1 else f"依赖前序批次输出接口（Batch {batch_no - 1}）",
            "modules": batch_modules,
        })
        remaining = [module for module in remaining if module not in ready]
        batch_no += 1
    return batches


def load_existing_plan(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def build_redefined_plan(project_name: str, modules: list[dict[str, Any]], existing_plan: dict[str, Any] | None) -> dict[str, Any]:
    today = date.today().isoformat()
    new_plan = {
        "project": project_name,
        "created": today,
        "batches": build_batches(modules),
    }
    if not existing_plan:
        return new_plan

    previous_states: dict[str, dict[str, Any]] = {}
    for batch in existing_plan.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for module in batch.get("modules", []):
            if not isinstance(module, dict):
                continue
            module_name = str(module.get("name", ""))
            if not module_name:
                continue
            previous_states[module_name] = {
                "state": module.get("state", "pending"),
                "completed_at": module.get("completed_at"),
                "complexity": module.get("complexity"),
                "risk": module.get("risk"),
            }

    for batch in new_plan.get("batches", []):
        if not isinstance(batch, dict):
            continue
        for module in batch.get("modules", []):
            if not isinstance(module, dict):
                continue
            name = module.get("name", "")
            if name not in previous_states:
                continue
            preserved = previous_states[name]
            module["state"] = preserved.get("state") or "pending"
            module["completed_at"] = preserved.get("completed_at")
            if preserved.get("complexity"):
                module["complexity"] = preserved["complexity"]
            if preserved.get("risk") is not None:
                module["risk"] = preserved["risk"]
    return new_plan


def render_plan_markdown(plan: dict[str, Any]) -> str:
    status_icon = {"pending": "- [ ]", "completed": "- [x]", "skipped": "- [~]", "in_progress": "- [>]"}
    lines = [
        f"# {plan.get('project', 'unknown')} · 实现计划",
        "",
        "> ⚠️ 此文件是 `docs/plan.json` 的派生/生成视图，用于人类阅读；执行状态以 `plan.json` 为准，请勿手动编辑。",
        "",
        "## 实现批次",
        "",
    ]
    for batch in plan.get("batches", []):
        lines.append(f"### {batch.get('name', '')}")
        if batch.get("description"):
            lines.append(f"_{batch['description']}_")
        lines.append("")
        for module in batch.get("modules", []):
            deps = module.get("deps", [])
            dep_suffix = f" — 依赖: {', '.join(deps)}" if deps else ""
            lines.append(
                f"{status_icon.get(module.get('state', 'pending'), '- [ ]')} **{module.get('name', '')}** "
                f"— 估算: {module.get('complexity', 'M')}{dep_suffix}"
            )
        lines.append("")

    all_modules = [module for batch in plan.get("batches", []) for module in batch.get("modules", [])]
    completed = sum(1 for module in all_modules if module.get("state") == "completed")
    lines.extend([
        "---",
        f"**进度: {completed}/{len(all_modules)}**",
        f"_最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
    ])
    return "\n".join(lines)


def render_todo(project_name: str, plan: dict[str, Any]) -> str:
    return workflow_cli_common.render_managed_todo(project_name, workflow_cli_common.plan_tasks(plan))


def analyze_writes(target_root: Path, file_payloads: list[tuple[str, str]]) -> list[dict[str, str]]:
    writes: list[dict[str, str]] = []
    for rel, content in file_payloads:
        target = target_root / rel
        if not target.exists():
            writes.append({"path": rel, "action": "create"})
            continue
        current = safe_read_text(target)
        if current == content:
            writes.append({"path": rel, "action": "maintain"})
        else:
            writes.append({"path": rel, "action": "overwrite"})
    return writes


def write_files(target_root: Path, file_payloads: list[tuple[str, str]]) -> None:
    for rel, content in file_payloads:
        path = target_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def calc_changes(existing_plan: dict[str, Any] | None, new_plan: dict[str, Any]) -> dict[str, list[str]]:
    old_modules = {
        module.get("name", "")
        for batch in (existing_plan or {}).get("batches", [])
        for module in batch.get("modules", [])
        if module.get("name")
    }
    new_modules = {
        module.get("name", "")
        for batch in new_plan.get("batches", [])
        for module in batch.get("modules", [])
        if module.get("name")
    }
    return {
        "added_modules": sorted(new_modules - old_modules),
        "removed_modules": sorted(old_modules - new_modules),
        "preserved_modules": sorted(old_modules & new_modules),
    }


def parse_alias(alias: str | None) -> tuple[bool, dict[str, Any], str | None]:
    if not alias:
        return True, {"used": False, "name": None}, None
    normalized = alias.strip().upper()
    if normalized != "REDEFIND":
        return False, {"used": False, "name": alias}, f"不支持的 alias: {alias}；仅兼容 REDEFIND"
    return True, {"used": True, "name": "REDEFIND"}, None


def run(target_arg: str | None, dry_run: bool, alias: str | None) -> dict[str, Any]:
    ok_alias, alias_meta, alias_error = parse_alias(alias)
    if not ok_alias:
        return {
            "status": STATUS_ERROR,
            "message": alias_error or "alias 无效",
            "data": {
                "alias": alias_meta,
                "next_action": "移除 --alias，或改用 --alias REDEFIND",
                "dry_run": dry_run,
            },
        }

    target_root, target_label = resolve_target(target_arg)
    if target_root is None:
        return {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，也未提供目标路径，无法执行 REDEFINE",
            "data": {
                "project": None,
                "alias": alias_meta,
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
                "alias": alias_meta,
                "dry_run": dry_run,
                "next_action": "先创建项目目录，并确保其中包含 docs/CONTEXT.md",
            },
        }

    context_path = target_root / "docs" / "CONTEXT.md"
    context_content = safe_read_text(context_path)
    if not context_content:
        return {
            "status": STATUS_ERROR,
            "message": f"缺少重定义输入文档：{context_path}",
            "data": {
                "project": target_label,
                "project_root": rel_path(target_root, ROOT),
                "alias": alias_meta,
                "dry_run": dry_run,
                "next_action": "补齐项目 docs/CONTEXT.md 后重新运行 REDEFINE",
            },
        }

    modules = parse_modules(context_content)
    project_name = parse_title(context_content, target_root.name)
    existing_plan_path = target_root / "docs" / "plan.json"
    existing_plan = load_existing_plan(existing_plan_path)
    new_plan = build_redefined_plan(project_name, modules, existing_plan)
    workflow_cli_common.ensure_plan_stable_ids(new_plan)

    file_payloads = [
        ("docs/plan.json", json.dumps(new_plan, ensure_ascii=False, indent=2) + "\n"),
        ("docs/PLAN.md", render_plan_markdown(new_plan)),
        ("docs/TODO.md", render_todo(project_name, new_plan)),
    ]
    writes = analyze_writes(target_root, file_payloads)
    changes = calc_changes(existing_plan, new_plan)

    if not dry_run:
        write_files(target_root, file_payloads)

    message = "REDEFINE 预览完成：已按 CONTEXT 计算 plan.json 与派生文档"
    if not dry_run:
        message = "REDEFINE 已完成：plan.json 已更新并重建派生文档"
    if alias_meta.get("used"):
        message = f"{message}（兼容别名 REDEFIND 已映射到 REDEFINE 语义）"

    return {
        "status": STATUS_OK,
        "message": message,
        "data": {
            "project": project_name,
            "project_root": rel_path(target_root, ROOT),
            "input_source": "docs/CONTEXT.md",
            "plan_source": "docs/plan.json",
            "dry_run": dry_run,
            "alias": alias_meta,
            "propagation": [
                "update:docs/plan.json",
                "regenerate:docs/PLAN.md",
                "regenerate:docs/TODO.md",
            ],
            "writes": writes,
            "changes": changes,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:redefine 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  基于项目 docs/CONTEXT.md 重定义规划，更新 docs/plan.json，
  并按固定顺序重建 docs/PLAN.md 与 docs/TODO.md。

示例:
  python3 .claude/tools/redefine/run.py structured-light-stereo --json --dry-run
  python3 .claude/tools/redefine/run.py skill-tests/fixtures/redefine/plan-change-project --json
  python3 .claude/tools/redefine/run.py --alias REDEFIND skill-tests/fixtures/redefine/plan-change-project --json --dry-run
""",
    )
    parser.add_argument("project", nargs="?", help="可选：目标项目名或项目根目录路径")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    parser.add_argument("--dry-run", action="store_true", help="仅预览将写入的文件，不实际落盘")
    parser.add_argument("--alias", default=None, help="兼容旧命令别名（仅支持 REDEFIND）")
    args = parser.parse_args()

    result = run(args.project, args.dry_run, args.alias)
    out(result, args.json)

    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
