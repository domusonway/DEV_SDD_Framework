#!/usr/bin/env python3
"""
plan-tracker/tracker.py
结构化进度追踪工具，替代纯 markdown PLAN.md 的手动维护

JSON plan 文件: projects/<PROJECT>/docs/plan.json
Markdown PLAN.md 由此工具自动生成（generated read-only view，不要手动编辑）

用途:
  追踪项目模块实现进度，输出结构化状态供 Agent 工具调用判断下一步行动。
  支持 --json flag，方便 Agent 解析当前进度和 next_action。

用法:
  python3 .claude/tools/plan-tracker/tracker.py status          # 查看进度
  python3 .claude/tools/plan-tracker/tracker.py status --json   # JSON 格式进度
  python3 .claude/tools/plan-tracker/tracker.py complete <module>   # 标记完成
  python3 .claude/tools/plan-tracker/tracker.py skip <module>       # 标记跳过
  python3 .claude/tools/plan-tracker/tracker.py reset <module>      # 重置为待完成
  python3 .claude/tools/plan-tracker/tracker.py render              # 重新生成 PLAN.md
  python3 .claude/tools/plan-tracker/tracker.py validate            # 检查所有模块已完成

示例:
  python3 .claude/tools/plan-tracker/tracker.py status --json
  python3 .claude/tools/plan-tracker/tracker.py complete request_parser
  python3 .claude/tools/plan-tracker/tracker.py skip cgi_handler --reason "暂不实现"
"""
import sys
import os
import re
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


CHECK_IMPL_PATH = Path(__file__).resolve().parents[2] / "hooks" / "observe-verify" / "check_impl.py"


def find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "docs" / "plan.json").exists() or (parent / "CLAUDE.md").exists():
            return parent
    return current


def get_project_name(root: Path) -> str:
    if (root / "docs" / "plan.json").exists():
        return root.name

    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return os.environ.get("PROJECT", "unknown")
    content = claude_md.read_text(encoding="utf-8")
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return os.environ.get("PROJECT", "unknown")


def load_plan(root: Path, project: str) -> dict[str, Any]:
    plan_path = project_path(root, project) / "docs" / "plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"plan.json 不存在: {plan_path}\n请先创建 plan.json（参见模板）")
    return json.loads(plan_path.read_text(encoding="utf-8"))


def save_plan(root: Path, project: str, plan: dict[str, Any]):
    plan_path = project_path(root, project) / "docs" / "plan.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2))


def project_path(root: Path, project: str) -> Path:
    if (root / "docs" / "plan.json").exists():
        return root
    return root / "projects" / project


def collect_plan_modules(plan: dict[str, Any]) -> list[dict[str, Any]]:
    batches = plan.get("batches")
    if isinstance(batches, list):
        return [m for b in batches if isinstance(b, dict) for m in b.get("modules", []) if isinstance(m, dict)]

    if "phases" in plan:
        raise ValueError("plan.json 使用旧 schema（phases/tasks）；请迁移为 batches/modules 后再运行 plan-tracker")

    raise ValueError("plan.json 缺少 batches/modules 结构；请使用 INIT/REDEFINE 生成标准计划")


def find_module_entry(plan: dict[str, Any], module_name: str) -> dict[str, Any] | None:
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            if module.get("name") == module_name:
                return module
    return None


def resolve_impl_target(root: Path, project: str, module: dict[str, Any]) -> Path:
    proj_root = project_path(root, project)
    explicit_path = str(module.get("impl_path") or module.get("path") or "").strip()
    if explicit_path:
        target = proj_root / explicit_path
        if target.exists():
            return target
        raise FileNotFoundError(f"模块 {module.get('name')} 的 impl_path 不存在: {target}")

    module_name = str(module.get("name") or "").strip()
    if not module_name:
        raise FileNotFoundError("模块缺少 name，无法定位实现路径")

    direct_candidates = [
        proj_root / module_name,
        proj_root / "modules" / module_name,
    ]
    for candidate in direct_candidates:
        if candidate.exists():
            return candidate

    modules_root = proj_root / "modules"
    if not modules_root.exists():
        raise FileNotFoundError(f"项目缺少 modules 目录: {modules_root}")

    matches = sorted(path for path in modules_root.rglob("*") if path.name == module_name)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        options = ", ".join(str(path.relative_to(proj_root)) for path in matches[:5])
        raise FileNotFoundError(f"模块 {module_name} 匹配到多个实现路径，请在 plan.json 中显式设置 path: {options}")

    raise FileNotFoundError(f"无法为模块 {module_name} 定位实现路径；请在 plan.json 中添加 impl_path 字段")


def run_impl_check(root: Path, project: str, module: dict[str, Any]) -> dict[str, Any]:
    target = resolve_impl_target(root, project, module)
    result = subprocess.run(
        [sys.executable, str(CHECK_IMPL_PATH), str(target)],
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + (result.stderr or "")
    target_display = str(target.relative_to(project_path(root, project)))
    return {
        "passed": result.returncode == 0,
        "target": target_display,
        "output": output.strip(),
    }


def fail_invalid_plan_schema(args, message: str):
    if getattr(args, "json", False):
        print(json.dumps({"status": "error", "message": message, "data": None}, ensure_ascii=False))
    else:
        print(f"❌ {message}")
    sys.exit(1)


def render_markdown(root: Path, project: str, plan: dict[str, Any], quiet: bool = False):
    """从 plan.json 生成 PLAN.md（generated read-only view）"""
    modules = collect_plan_modules(plan)
    md_path = project_path(root, project) / "docs" / "PLAN.md"
    lines = [
        f"# {plan.get('project', project)} · 实现计划",
        "",
        "> ⚠️ 此文件由 plan-tracker 自动生成，请勿手动编辑。修改 plan.json 后运行 `tracker.py render`",
        "",
    ]
    status_icon = {"pending": "- [ ]", "completed": "- [x]", "skipped": "- [~]", "in_progress": "- [>]"}
    for batch in plan.get("batches", []):
        lines.append(f"### {batch['name']}")
        if batch.get("description"):
            lines.append(f"_{batch['description']}_")
        lines.append("")
        for module in batch.get("modules", []):
            state = module.get("state", "pending")
            icon = status_icon.get(state, "- [ ]")
            complexity = module.get("complexity", "M")
            risk = module.get("risk", "")
            risk_str = f" ⚠️ {risk}" if risk else ""
            completed_str = f" ✅ {module.get('completed_at', '')}" if state == "completed" else ""
            lines.append(f"{icon} **{module['name']}** — 估算: {complexity}{risk_str}{completed_str}")
            if module.get("deps"):
                lines.append(f"   - 依赖: {', '.join(module['deps'])}")
        lines.append("")
    completed = sum(1 for m in modules if m.get("state") == "completed")
    total = len(modules)
    lines.append("---")
    lines.append(f"**进度: {completed}/{total}**")
    lines.append(f"_最后更新: {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    md_path.write_text("\n".join(lines), encoding="utf-8")
    if not quiet:
        print(f"[plan-tracker] ✅ PLAN.md 已更新 ({completed}/{total} 完成)")


def _compute_next_action(plan: dict[str, Any]) -> str:
    """计算当前最高优先级的未完成模块名（按批次顺序）。"""
    for batch in plan.get("batches", []):
        for module in batch.get("modules", []):
            state = module.get("state", "pending")
            if state == "in_progress":
                return f"继续实现 {module['name']}（{batch['name']}）"
            if state == "pending":
                return f"实现 {module['name']}（{batch['name']}）"
    return "所有模块已完成，可进入 validate-output"


def cmd_status(args, root, project):
    try:
        plan = load_plan(root, project)
    except FileNotFoundError as e:
        if args.json:
            print(json.dumps({"status": "error", "message": str(e), "data": None}, ensure_ascii=False))
        else:
            print(f"❌ {e}")
        sys.exit(1)

    try:
        all_modules = collect_plan_modules(plan)
    except ValueError as e:
        fail_invalid_plan_schema(args, str(e))
    completed_list = [m["name"] for m in all_modules if m.get("state") == "completed"]
    pending_list = [m["name"] for m in all_modules if m.get("state") == "pending"]
    skipped_list = [m["name"] for m in all_modules if m.get("state") == "skipped"]
    total = len(all_modules)
    completed_count = len(completed_list)
    percent = round(completed_count / total * 100) if total else 0
    next_action = _compute_next_action(plan)

    if args.json:
        # TASK-AF-02: 结构化 JSON 输出
        batches_data = []
        for batch in plan.get("batches", []):
            batches_data.append({
                "name": batch["name"],
                "modules": [
                    {
                        "name": m["name"],
                        "state": m.get("state", "pending"),
                        "complexity": m.get("complexity", "M"),
                    }
                    for m in batch.get("modules", [])
                ],
            })
        print(json.dumps({
            "status": "ok",
            "message": f"{project}: {completed_count}/{total} 完成 ({percent}%)",
            "data": {
                "project": project,
                "completed": completed_count,
                "total": total,
                "percent": percent,
                "next_action": next_action,
                "completed_modules": completed_list,
                "pending_modules": pending_list,
                "skipped_modules": skipped_list,
                "batches": batches_data,
            },
        }, ensure_ascii=False, indent=2))
    else:
        print(f"\n📋 {plan.get('project', project)} · 计划进度")
        print(f"{'─'*40}")
        print(f"  ✅ 已完成: {completed_count}")
        print(f"  ⏳ 待完成: {len(pending_list)}")
        print(f"  ⏭️  已跳过: {len(skipped_list)}")
        print(f"  总计: {total}  进度: {percent}%")
        print(f"  ▶ 下一步: {next_action}")
        print()
        for batch in plan.get("batches", []):
            print(f"  [{batch['name']}]")
            for m in batch.get("modules", []):
                state = m.get("state", "pending")
                icon = {"completed": "✅", "pending": "⬜", "skipped": "⏭️", "in_progress": "🔄"}.get(state, "⬜")
                print(f"    {icon} {m['name']} ({m.get('complexity', 'M')})")
        print()


def cmd_complete(args, root, project):
    plan = load_plan(root, project)
    try:
        collect_plan_modules(plan)
    except ValueError as e:
        fail_invalid_plan_schema(args, str(e))

    module_name = args.module
    module = find_module_entry(plan, module_name)
    if module is None:
        if args.json:
            print(json.dumps({"status": "error", "message": f"未找到模块: {module_name}", "data": None}, ensure_ascii=False))
        else:
            print(f"❌ 未找到模块: {module_name}")
        sys.exit(1)

    try:
        impl_check = run_impl_check(root, project, module)
    except FileNotFoundError as e:
        if args.json:
            print(json.dumps({
                "status": "error",
                "message": str(e),
                "data": {"module": module_name},
            }, ensure_ascii=False))
        else:
            print(f"❌ {e}")
        sys.exit(1)

    if not impl_check["passed"]:
        message = f"模块 {module_name} 未通过实现完整性检查，禁止标记完成"
        if args.json:
            print(json.dumps({
                "status": "error",
                "message": message,
                "data": {
                    "module": module_name,
                    "target": impl_check["target"],
                    "impl_check_output": impl_check["output"],
                },
            }, ensure_ascii=False))
        else:
            print(f"❌ {message}")
            if impl_check["output"]:
                print(impl_check["output"])
        sys.exit(1)

    module["state"] = "completed"
    module["completed_at"] = datetime.now().strftime("%Y-%m-%d")
    save_plan(root, project, plan)
    render_markdown(root, project, plan, quiet=args.json)
    next_action = _compute_next_action(plan)
    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"{module_name} 已标记为完成",
            "data": {"module": module_name, "next_action": next_action},
        }, ensure_ascii=False))
    else:
        print(f"[plan-tracker] ✅ {module_name} 已标记为完成")
        print(f"  ▶ 下一步: {next_action}")


def cmd_skip(args, root, project):
    plan = load_plan(root, project)
    try:
        collect_plan_modules(plan)
    except ValueError as e:
        fail_invalid_plan_schema(args, str(e))
    found = False
    for batch in plan.get("batches", []):
        for m in batch.get("modules", []):
            if m["name"] == args.module:
                m["state"] = "skipped"
                m["skip_reason"] = args.reason or "待修复"
                found = True
                break
    if not found:
        if args.json:
            print(json.dumps({"status": "error", "message": f"未找到模块: {args.module}", "data": None}, ensure_ascii=False))
        else:
            print(f"❌ 未找到模块: {args.module}")
        sys.exit(1)
    save_plan(root, project, plan)
    render_markdown(root, project, plan, quiet=args.json)
    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"{args.module} 已标记为跳过: {args.reason or '待修复'}",
            "data": {"module": args.module, "reason": args.reason or "待修复"},
        }, ensure_ascii=False))
    else:
        print(f"[plan-tracker] ⏭️  {args.module} 已标记为跳过: {args.reason or '待修复'}")


def cmd_validate(args, root, project):
    plan = load_plan(root, project)
    try:
        all_modules = collect_plan_modules(plan)
    except ValueError as e:
        fail_invalid_plan_schema(args, str(e))

    unfinished = [m for m in all_modules if m.get("state") in {"pending", "in_progress"}]
    if unfinished:
        msg = f"仍有未完成模块: {', '.join(m['name'] for m in unfinished)}"
        if args.json:
            print(json.dumps({"status": "error", "message": msg, "data": {"pending": [m["name"] for m in unfinished]}}, ensure_ascii=False))
        else:
            print(f"❌ {msg}")
        sys.exit(1)
    invalid_modules = []
    for module in all_modules:
        if module.get("state") != "completed":
            continue
        try:
            impl_check = run_impl_check(root, project, module)
        except FileNotFoundError as e:
            invalid_modules.append({"module": module.get("name"), "error": str(e)})
            continue
        if not impl_check["passed"]:
            invalid_modules.append({
                "module": module.get("name"),
                "target": impl_check["target"],
                "impl_check_output": impl_check["output"],
            })

    if invalid_modules:
        msg = "以下 completed 模块未通过实现完整性检查"
        if args.json:
            print(json.dumps({"status": "error", "message": msg, "data": {"invalid_modules": invalid_modules}}, ensure_ascii=False))
        else:
            print(f"❌ {msg}")
            for item in invalid_modules:
                print(f"- {item['module']}: {item.get('target') or item.get('error')}")
        sys.exit(1)

    if args.json:
        print(json.dumps({"status": "ok", "message": "所有模块已完成（或跳过），且实现完整性检查通过，可以进入 validate-output", "data": None}, ensure_ascii=False))
    else:
        print("✅ 所有模块已完成（或跳过），且实现完整性检查通过，可以进入 validate-output")


def main():
    parser = argparse.ArgumentParser(
        description="Plan Tracker — 结构化进度管理",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  追踪项目模块实现进度，输出结构化状态供 Agent 工具调用判断下一步行动。
  --json 模式返回 next_action 字段，Agent 可直接读取下一个待实现的模块。

示例:
  python3 .claude/tools/plan-tracker/tracker.py status
  python3 .claude/tools/plan-tracker/tracker.py status --json
  python3 .claude/tools/plan-tracker/tracker.py complete request_parser
  python3 .claude/tools/plan-tracker/tracker.py skip cgi_handler --reason "暂不实现"
  python3 .claude/tools/plan-tracker/tracker.py validate
""",
    )
    parser.add_argument("--json", action="store_true", help="输出机器友好的 JSON")
    subparsers = parser.add_subparsers(dest="cmd")

    subparsers.add_parser("status", help="查看进度")
    subparsers.add_parser("render", help="重新生成 PLAN.md")
    subparsers.add_parser("validate", help="验证所有模块已完成")

    complete_p = subparsers.add_parser("complete", help="标记模块完成")
    complete_p.add_argument("module", help="模块名")

    skip_p = subparsers.add_parser("skip", help="标记模块跳过")
    skip_p.add_argument("module", help="模块名")
    skip_p.add_argument("--reason", default="", help="跳过原因")

    reset_p = subparsers.add_parser("reset", help="重置模块状态")
    reset_p.add_argument("module", help="模块名")

    args = parser.parse_args()
    root = find_project_root()
    project = get_project_name(root)

    dispatch = {
        "status": cmd_status,
        "complete": cmd_complete,
        "skip": cmd_skip,
        "validate": cmd_validate,
        "render": lambda a, r, p: render_markdown(r, p, load_plan(r, p), quiet=a.json),
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args, root, project)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
