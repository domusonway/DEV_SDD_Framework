#!/usr/bin/env python3
"""
context-budget/handoff.py
在 Context Budget 危险时执行 Session 交接

用法:
  python3 .claude/hooks/context-budget/handoff.py write \
      --module request_parser \
      --state GREEN \
      --next "实现 response 模块，从批次1继续" \
      --pending "response router static_handler"

  python3 .claude/hooks/context-budget/handoff.py read
  python3 .claude/hooks/context-budget/handoff.py clear
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
    """从 PLAN.md 读取进度（兼容 markdown checklist 格式）"""
    plan_path = root / "projects" / project / "docs" / "PLAN.md"
    if not plan_path.exists():
        return {"completed": [], "in_progress": [], "pending": []}

    content = plan_path.read_text(encoding="utf-8")
    completed = re.findall(r"- \[x\] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)
    pending = re.findall(r"- \[ \] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)
    skipped = re.findall(r"- \[~\] (.+?)(?:\s*—.*)?$", content, re.MULTILINE)

    # 清理模块名
    def clean(items):
        return [re.sub(r"\s*\(.*?\)", "", i).strip() for i in items]

    return {
        "completed": clean(completed),
        "in_progress": [],
        "pending": clean(pending),
        "skipped": clean(skipped),
    }


def get_interface_snapshots(root: Path, project: str) -> dict:
    """从 memory/INDEX.md 读取接口快照状态"""
    index_path = root / "projects" / project / "memory" / "INDEX.md"
    if not index_path.exists():
        return {}

    content = index_path.read_text(encoding="utf-8")
    # 匹配接口快照表格行
    snapshots = {}
    for line in content.splitlines():
        # | module | func | in | out | 🟢/🟡/🔴 |
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
    print(f"[handoff] ✅ 已写入: {handoff_path.relative_to(root)}")
    print(f"[handoff] 下一步: {args.next}")
    print(f"[handoff] 待完成模块: {', '.join(pending_list)}")


def cmd_read(args):
    root = find_project_root()
    project = get_project_name(root)
    handoff_path = root / "projects" / project / "HANDOFF.json"

    if not handoff_path.exists():
        print("[handoff] 无 HANDOFF.json，正常启动")
        return

    data = json.loads(handoff_path.read_text(encoding="utf-8"))

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
        print(f"[handoff] ✅ HANDOFF.json 已清除（已读取）")
    else:
        print("[handoff] 无 HANDOFF.json 需要清除")


def main():
    parser = argparse.ArgumentParser(description="Context Budget Handoff Tool")
    subparsers = parser.add_subparsers(dest="cmd")

    # write
    write_p = subparsers.add_parser("write", help="写入交接文件")
    write_p.add_argument("--module", required=True, help="最后完成的模块名")
    write_p.add_argument("--state", default="GREEN", help="当前状态 GREEN/RED/REFACTOR")
    write_p.add_argument("--next", required=True, help="下一步行动（一句话）")
    write_p.add_argument("--pending", default="", help="待完成模块列表，空格分隔")
    write_p.add_argument("--blockers", default="", help="阻塞项，分号分隔")
    write_p.add_argument("--notes", default="", help="给下个 session 的上下文说明")
    write_p.add_argument("--reason", default="context_budget", help="交接原因")

    # read
    subparsers.add_parser("read", help="读取并显示交接信息")

    # clear
    subparsers.add_parser("clear", help="清除交接文件（已读取后调用）")

    args = parser.parse_args()

    if args.cmd == "write":
        cmd_write(args)
    elif args.cmd == "read":
        cmd_read(args)
    elif args.cmd == "clear":
        cmd_clear(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
