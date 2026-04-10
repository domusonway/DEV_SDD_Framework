#!/usr/bin/env python3
"""
session-snapshot write.py

用途:
  将会话快照写入 projects/<PROJECT>/memory/sessions/ 目录，并支持统一 JSON CLI 输出。

示例:
  python3 write.py start "实现 projects 模块"
  python3 write.py checkpoint "projects VALIDATE" "5/5 PASS" "GREEN"
  python3 write.py end "完成 projects" "无" "开始 workorders"
  python3 write.py --json list --latest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def find_project_root() -> Path:
    """Find framework root or current project root."""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "memory" / "sessions").exists() or (parent / "CLAUDE.md").exists():
            return parent
    return current


def get_project_name(root: Path) -> str:
    """Read current project from project root or framework CLAUDE.md."""
    if (root / "memory" / "sessions").exists():
        return root.name

    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return os.environ.get("PROJECT", "unknown")
    content = claude_md.read_text(encoding="utf-8")
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return os.environ.get("PROJECT", "unknown")


def project_path(root: Path, project: str) -> Path:
    if (root / "memory" / "sessions").exists():
        return root
    return root / "projects" / project


def get_session_dir(root: Path, project: str) -> Path:
    session_dir = project_path(root, project) / "memory" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_current_session_file(session_dir: Path) -> Path | None:
    today = datetime.now().strftime("%Y-%m-%d")
    files = sorted(session_dir.glob(f"{today}_*.md"), reverse=True)
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        if "status: in-progress" in content:
            return file_path
    return None


def create_session_file(session_dir: Path, session_id: str) -> Path:
    return session_dir / f"{session_id}.md"


def parse_session_file(file_path: Path) -> dict[str, Any]:
    content = file_path.read_text(encoding="utf-8")
    task_match = re.search(r"^task: (.+)$", content, re.MULTILINE)
    session_id_match = re.search(r"^session_id: (.+)$", content, re.MULTILINE)
    project_match = re.search(r"^project: (.+)$", content, re.MULTILINE)
    status = "completed" if "status: completed" in content else "in-progress"
    next_action_match = re.search(r"^下次继续: (.+)$", content, re.MULTILINE)
    return {
        "session_id": (session_id_match.group(1).strip() if session_id_match else file_path.stem),
        "project": project_match.group(1).strip() if project_match else "unknown",
        "task": task_match.group(1).strip() if task_match else "未知任务",
        "status": status,
        "checkpoint_count": content.count("[CHECKPOINT"),
        "next_action": next_action_match.group(1).strip() if next_action_match else None,
        "path": file_path.name,
    }


def emit(args, *, status: str, message: str, data: Any) -> None:
    if args.json:
        print(json.dumps({"status": status, "message": message, "data": data}, ensure_ascii=False))
    else:
        print(message)


def cmd_start(args) -> int:
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)

    now = datetime.now()
    session_id = now.strftime("%Y-%m-%d_%H-%M")
    time_str = now.strftime("%H:%M")

    prev = get_current_session_file(session_dir)
    resume_note = f"续接 {prev.stem}" if prev else "新会话"
    filepath = create_session_file(session_dir, session_id)
    filepath.write_text(
        f"---\n"
        f"status: in-progress\n"
        f"session_id: {session_id}\n"
        f"project: {project}\n"
        f"task: {args.task}\n"
        f"---\n\n"
        f"[SESSION-START]\n"
        f"时间: {time_str}\n"
        f"加载记忆: 待填写\n"
        f"项目状态: 待填写\n"
        f"续接: {resume_note}\n"
        f"[/SESSION-START]\n",
        encoding="utf-8",
    )
    emit(args, status="ok", message=f"[session-snapshot] 已创建: {filepath.name}", data=parse_session_file(filepath))
    return 0


def cmd_checkpoint(args) -> int:
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    filepath = get_current_session_file(session_dir)
    if not filepath:
        emit(args, status="warning", message="[session-snapshot] ⚠️  无 in-progress session，请先执行 start", data=None)
        return 0

    time_str = datetime.now().strftime("%H:%M")
    with open(filepath, "a", encoding="utf-8") as handle:
        handle.write(
            f"\n[CHECKPOINT {time_str}]\n"
            f"事件: {args.event}\n"
            f"决策/结果: {args.result}\n"
            f"当前状态: {args.state}\n"
            f"[/CHECKPOINT]\n"
        )
    emit(args, status="ok", message=f"[session-snapshot] ✅ 检查点已写入: {filepath.name}", data=parse_session_file(filepath))
    return 0


def cmd_end(args) -> int:
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    filepath = get_current_session_file(session_dir)
    if not filepath:
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%d_%H-%M")
        filepath = create_session_file(session_dir, session_id)
        filepath.write_text(
            f"---\nstatus: in-progress\nsession_id: {session_id}\nproject: {project}\ntask: 未记录\n---\n\n",
            encoding="utf-8",
        )

    time_str = datetime.now().strftime("%H:%M")
    with open(filepath, "a", encoding="utf-8") as handle:
        handle.write(
            f"\n[SESSION-END]\n"
            f"时间: {time_str}\n"
            f"完成了: {args.completed}\n"
            f"未完成: {args.interrupted}\n"
            f"下次继续: {args.next_step}\n"
            f"沉淀决策: {args.decision}\n"
            f"记忆动作: {args.memory_action}\n"
            f"[/SESSION-END]\n"
        )

    content = filepath.read_text(encoding="utf-8")
    filepath.write_text(content.replace("status: in-progress", "status: completed", 1), encoding="utf-8")
    emit(args, status="ok", message=f"[session-snapshot] ✅ 会话已关闭: {filepath.name}", data=parse_session_file(filepath))
    return 0


def cmd_list(args) -> int:
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    files = sorted(session_dir.glob("*.md"), reverse=True)[:14]
    records = [parse_session_file(file_path) for file_path in files]

    if args.latest:
        latest = records[0] if records else None
        emit(args, status="ok", message=f"最近 session（项目: {project}）", data=latest)
        return 0

    if args.json:
        emit(args, status="ok", message=f"最近 session 记录（项目: {project}）", data=records)
        return 0

    if not records:
        print("[session-snapshot] 暂无 session 记录")
        return 0

    print(f"\n最近 session 记录（项目: {project}）\n{'─' * 50}")
    for record in records:
        icon = "✅ completed" if record["status"] == "completed" else "🔄 in-progress"
        print(f"  {record['session_id']}  {icon}  [{record['checkpoint_count']} checkpoints]  {record['task'][:40]}")
    print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="session-snapshot 会话快照工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  将会话快照写入 projects/<PROJECT>/memory/sessions/ 目录，并支持统一 JSON CLI 输出。

示例:
  python3 write.py start "实现 projects 模块"
  python3 write.py checkpoint "projects VALIDATE" "5/5 PASS" "GREEN"
  python3 write.py end "完成 projects" "无" "开始 workorders"
  python3 write.py --json list --latest
""",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON envelope")
    subparsers = parser.add_subparsers(dest="cmd")

    start_parser = subparsers.add_parser("start", help="创建新 session")
    start_parser.add_argument("task", nargs="?", default="未指定任务")
    start_parser.set_defaults(handler=cmd_start)

    checkpoint_parser = subparsers.add_parser("checkpoint", help="追加 checkpoint")
    checkpoint_parser.add_argument("event", nargs="?", default="未知事件")
    checkpoint_parser.add_argument("result", nargs="?", default="")
    checkpoint_parser.add_argument("state", nargs="?", default="")
    checkpoint_parser.set_defaults(handler=cmd_checkpoint)

    end_parser = subparsers.add_parser("end", help="关闭当前 session")
    end_parser.add_argument("completed", nargs="?", default="未记录")
    end_parser.add_argument("interrupted", nargs="?", default="无")
    end_parser.add_argument("next_step", nargs="?", default="待定")
    end_parser.add_argument("decision", nargs="?", default="no_sedimentation")
    end_parser.add_argument("memory_action", nargs="?", default="无")
    end_parser.set_defaults(handler=cmd_end)

    list_parser = subparsers.add_parser("list", help="列出最近 session")
    list_parser.add_argument("--latest", action="store_true", help="仅返回最新一条")
    list_parser.set_defaults(handler=cmd_list)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not hasattr(args, "handler"):
        parser.print_help()
        sys.exit(0)
    sys.exit(args.handler(args))


if __name__ == "__main__":
    main()
