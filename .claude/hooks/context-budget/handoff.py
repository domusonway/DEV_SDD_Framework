#!/usr/bin/env python3
"""
context-budget/handoff.py
在 Context Budget 危险时执行 Session 交接

用途:
  写入、读取、清除 HANDOFF.json 交接文件。
  Agent 在启动协议 Step 2.5 中先调用 read --exists --json 快速判断是否有待续接任务，
  再按需调用 read --json 获取完整交接信息。

用法:
  python3 handoff.py write --module <m> --state <s> --next "<action>" [选项]
  python3 handoff.py read [--json] [--exists]
  python3 handoff.py clear [--json]

示例:
  # 写入交接
  python3 handoff.py write --module request_parser --state GREEN --next "实现 response 模块"

  # Agent 启动时：快速探测
  python3 handoff.py read --exists --json
  # 返回: {"exists": true} 或 {"exists": false}

  # 读取完整交接信息
  python3 handoff.py read --json

  # 清除（已读取后调用）
  python3 handoff.py clear --json
"""
import sys
import os
import re
import json
import argparse
from datetime import datetime
from pathlib import Path


def find_project_root() -> Path:
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


def get_project_name(root: Path) -> str:
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return os.environ.get("PROJECT", "unknown")
    content = claude_md.read_text(encoding="utf-8")
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return os.environ.get("PROJECT", "unknown")


def get_plan_progress(root: Path, project: str) -> dict:
    plan_path = root / "projects" / project / "docs" / "PLAN.md"
    if not plan_path.exists():
        return {"completed": [], "in_progress": [], "pending": []}
    content = plan_path.read_text(encoding="utf-8")
    completed = re.findall(r"- \[x\] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)
    pending = re.findall(r"- \[ \] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)
    skipped = re.findall(r"- \[~\] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)

    def clean(items):
        return [re.sub(r"\s*\(.*?\)", "", i).strip() for i in items]

    return {
        "completed": clean(completed),
        "in_progress": [],
        "pending": clean(pending),
        "skipped": clean(skipped),
    }


def get_interface_snapshots(root: Path, project: str) -> dict:
    index_path = root / "projects" / project / "memory" / "INDEX.md"
    if not index_path.exists():
        return {}
    content = index_path.read_text(encoding="utf-8")
    snapshots = {}
    for line in content.splitlines():
        parts = [p.strip() for p in line.split("|") if p.strip()]
        if len(parts) >= 5 and any(e in parts[-1] for e in ["🟢", "🟡", "🔴"]):
            module = parts[0]
            status = parts[-1]
            snapshots[module] = {"status": status}
    return snapshots


def cmd_write(args):
    root = find_project_root()
    project = get_project_name(root)
    handoff_path = root / "projects" / project / "HANDOFF.json"
    # 确保目录存在
    handoff_path.parent.mkdir(parents=True, exist_ok=True)

    pending_list = args.pending.split() if args.pending else []
    plan_progress = get_plan_progress(root, project)
    if not pending_list:
        pending_list = plan_progress.get("pending", [])
    interface_snapshots = get_interface_snapshots(root, project)

    handoff = {
        "timestamp": datetime.now().isoformat(),
        "session_ended_reason": args.reason,
        "project": project,
        "last_completed_module": args.module,
        "current_state": args.state,
        "next_action": args.next,
        "blockers": args.blockers.split(";") if args.blockers else [],
        "plan_progress": {
            "completed": plan_progress.get("completed", []),
            "in_progress": plan_progress.get("in_progress", []),
            "pending": pending_list,
            "skipped": plan_progress.get("skipped", []),
        },
        "interface_snapshots": interface_snapshots,
        "context_notes": args.notes or "",
    }
    handoff_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2))

    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"HANDOFF.json 已写入: {handoff_path.relative_to(root)}",
            "data": {"file": str(handoff_path.relative_to(root)), "next_action": args.next},
        }, ensure_ascii=False))
    else:
        print(f"[handoff] ✅ 已写入: {handoff_path.relative_to(root)}")
        print(f"[handoff] 下一步: {args.next}")
        print(f"[handoff] 待完成模块: {', '.join(pending_list)}")


def cmd_read(args):
    root = find_project_root()
    project = get_project_name(root)
    handoff_path = root / "projects" / project / "HANDOFF.json"

    exists = handoff_path.exists()

    # TASK-AF-04: --exists flag：只返回存在性，不加载内容
    if getattr(args, "exists", False):
        print(json.dumps({"exists": exists}, ensure_ascii=False))
        return

    if not exists:
        if args.json:
            print(json.dumps({"status": "ok", "message": "无 HANDOFF.json，正常启动", "data": None}, ensure_ascii=False))
        else:
            print("[handoff] 无 HANDOFF.json，正常启动")
        return

    data = json.loads(handoff_path.read_text(encoding="utf-8"))

    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"检测到交接文件 (原因: {data.get('session_ended_reason', 'unknown')})",
            "data": data,
        }, ensure_ascii=False))
    else:
        print(f"\n[HANDOFF 检测到]")
        print(f"  时间: {data.get('timestamp', 'unknown')}")
        print(f"  原因: {data.get('session_ended_reason', 'unknown')}")
        print(f"  上次完成: {data.get('last_completed_module', 'N/A')} ({data.get('current_state', '')})")
        print(f"  ▶ 下一步: {data.get('next_action', '未指定')}")
        pending = data.get("plan_progress", {}).get("pending", [])
        if pending:
            print(f"  待完成: {', '.join(pending)}")
        blockers = data.get("blockers", [])
        if blockers:
            print(f"  ⚠️ 阻塞项: {'; '.join(blockers)}")
        notes = data.get("context_notes", "")
        if notes:
            print(f"  注意: {notes}")


def cmd_clear(args):
    root = find_project_root()
    project = get_project_name(root)
    handoff_path = root / "projects" / project / "HANDOFF.json"

    if handoff_path.exists():
        handoff_path.unlink()
        if args.json:
            print(json.dumps({"status": "ok", "message": "HANDOFF.json 已清除", "data": None}, ensure_ascii=False))
        else:
            print(f"[handoff] ✅ HANDOFF.json 已清除（已读取）")
    else:
        if args.json:
            print(json.dumps({"status": "ok", "message": "无 HANDOFF.json 需要清除", "data": None}, ensure_ascii=False))
        else:
            print("[handoff] 无 HANDOFF.json 需要清除")


def main():
    parser = argparse.ArgumentParser(
        description="Context Budget Handoff Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  管理 Context Budget 危险时的 Session 交接文件。
  Agent 启动协议先用 read --exists --json 探测是否有交接，再决定是否全量读取。

示例:
  # 写入交接（Context Budget 危险时）
  python3 handoff.py write --module request_parser --state GREEN --next "实现 response 模块"

  # Agent 启动：快速探测（退出码始终为 0）
  python3 handoff.py read --exists --json
  # {"exists": true} 或 {"exists": false}

  # 读取完整交接信息
  python3 handoff.py read --json

  # 清除（已读取后调用）
  python3 handoff.py clear --json
""",
    )
    parser.add_argument("--json", action="store_true", help="输出机器友好的 JSON")
    subparsers = parser.add_subparsers(dest="cmd")

    write_p = subparsers.add_parser("write", help="写入交接文件")
    write_p.add_argument("--json", action="store_true", help="输出机器友好的 JSON")
    write_p.add_argument("--module", required=True, help="最后完成的模块名")
    write_p.add_argument("--state", default="GREEN", help="当前状态 GREEN/RED/REFACTOR")
    write_p.add_argument("--next", required=True, help="下一步行动（一句话）")
    write_p.add_argument("--pending", default="", help="待完成模块列表，空格分隔")
    write_p.add_argument("--blockers", default="", help="阻塞项，分号分隔")
    write_p.add_argument("--notes", default="", help="给下个 session 的上下文说明")
    write_p.add_argument("--reason", default="context_budget", help="交接原因")

    # TASK-AF-04: read 新增 --exists flag
    read_p = subparsers.add_parser("read", help="读取并显示交接信息")
    read_p.add_argument("--json", action="store_true", help="输出机器友好的 JSON")
    read_p.add_argument(
        "--exists",
        action="store_true",
        help="只返回 {\"exists\": true/false}，不加载内容（Agent 启动探测专用）",
    )

    clear_p = subparsers.add_parser("clear", help="清除交接文件（已读取后调用）")
    clear_p.add_argument("--json", action="store_true", help="输出机器友好的 JSON")

    args = parser.parse_args()

    if args.cmd == "write":
        cmd_write(args)
    elif args.cmd == "read":
        cmd_read(args)
    elif args.cmd == "clear":
        cmd_clear(args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
