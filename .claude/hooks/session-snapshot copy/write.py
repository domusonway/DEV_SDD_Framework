#!/usr/bin/env python3
"""
session-snapshot/write.py
将会话快照写入 projects/<PROJECT>/memory/sessions/ 目录

用途:
  记录会话开始、检查点、结束事件，支持跨会话续接。
  --json 模式和 --latest flag 供 Agent 在启动协议中快速判断是否有待续接的会话。

用法:
  python3 write.py start "<task>"
  python3 write.py checkpoint "<event>" "<result>" "<state>"
  python3 write.py end "<completed>" "<interrupted>" "<next_step>"
  python3 write.py list [--json] [--latest]

示例:
  python3 write.py start "实现 request_parser 模块"
  python3 write.py checkpoint "request_parser GREEN" "5/5 PASS" "批次1/3"
  python3 write.py end "完成 request_parser" "response 模块进行中" "继续实现 response 模块"
  python3 write.py list --json --latest
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


def get_session_dir(root: Path, project: str) -> Path:
    session_dir = root / "projects" / project / "memory" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_current_session_file(session_dir: Path):
    today = datetime.now().strftime("%Y-%m-%d")
    files = sorted(session_dir.glob(f"{today}_*.md"), reverse=True)
    for f in files:
        content = f.read_text(encoding="utf-8")
        if "status: in-progress" in content:
            return f
    return None


def create_session_file(session_dir: Path, session_id: str) -> Path:
    filename = f"{session_id}.md"
    return session_dir / filename


def _parse_session_meta(fpath: Path) -> dict:
    """从 session 文件提取元数据，供 --json 输出使用。"""
    content = fpath.read_text(encoding="utf-8")
    meta = {
        "session_id": fpath.stem,
        "status": "in-progress" if "status: in-progress" in content else "completed",
        "checkpoints": content.count("[CHECKPOINT"),
        "file": fpath.name,
    }
    task_m = re.search(r"^task:\s*(.+)$", content, re.MULTILINE)
    if task_m:
        meta["task"] = task_m.group(1).strip()
    next_m = re.search(r"下次继续:\s*(.+)", content)
    if next_m:
        meta["next_action"] = next_m.group(1).strip()
    return meta


def cmd_start(args):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    now = datetime.now()
    session_id = now.strftime("%Y-%m-%d_%H-%M")
    time_str = now.strftime("%H:%M")
    prev = get_current_session_file(session_dir)
    resume_note = f"续接 {prev.stem}" if prev else "新会话"
    filepath = create_session_file(session_dir, session_id)
    content = f"""---
status: in-progress
session_id: {session_id}
project: {project}
task: {args.task}
---

[SESSION-START]
时间: {time_str}
加载记忆: 待填写
项目状态: 待填写
续接: {resume_note}
[/SESSION-START]
"""
    filepath.write_text(content, encoding="utf-8")
    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"已创建 session: {filepath.name}",
            "data": {"session_id": session_id, "file": filepath.name, "resumed_from": prev.stem if prev else None},
        }, ensure_ascii=False))
    else:
        print(f"[session-snapshot] 已创建: {filepath.name}")
    return str(filepath)


def cmd_checkpoint(args):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    filepath = get_current_session_file(session_dir)
    if not filepath:
        msg = "无 in-progress session，请先执行 start"
        if args.json:
            print(json.dumps({"status": "warning", "message": msg, "data": None}, ensure_ascii=False))
        else:
            print(f"[session-snapshot] ⚠️  {msg}")
        return
    time_str = datetime.now().strftime("%H:%M")
    block = f"""
[CHECKPOINT {time_str}]
事件: {args.event}
决策/结果: {args.result}
当前状态: {args.state}
[/CHECKPOINT]
"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(block)
    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"检查点已写入: {filepath.name}",
            "data": {"file": filepath.name, "event": args.event},
        }, ensure_ascii=False))
    else:
        print(f"[session-snapshot] ✅ 检查点已写入: {filepath.name}")


def cmd_end(args):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    filepath = get_current_session_file(session_dir)
    if not filepath:
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%d_%H-%M")
        filepath = create_session_file(session_dir, session_id)
        filepath.write_text(
            f"---\nstatus: in-progress\nsession_id: {session_id}\n"
            f"project: {project}\ntask: 未记录\n---\n\n",
            encoding="utf-8",
        )
    time_str = datetime.now().strftime("%H:%M")
    block = f"""
[SESSION-END]
时间: {time_str}
完成了: {args.completed}
未完成: {args.interrupted}
下次继续: {args.next_step}
记忆候选: 无
[/SESSION-END]
"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(block)
    content = filepath.read_text(encoding="utf-8")
    content = content.replace("status: in-progress", "status: completed", 1)
    filepath.write_text(content, encoding="utf-8")
    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"会话已关闭: {filepath.name}",
            "data": {"file": filepath.name, "next_action": args.next_step},
        }, ensure_ascii=False))
    else:
        print(f"[session-snapshot] ✅ 会话已关闭: {filepath.name}")


def cmd_list(args):
    """TASK-AF-03: 支持 --json 和 --latest flag。"""
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)
    n = getattr(args, "n", 14)
    files = sorted(session_dir.glob("*.md"), reverse=True)[:n]

    if not files:
        empty_data = None if getattr(args, "latest", False) else []
        if args.json:
            print(json.dumps({"status": "ok", "message": "暂无 session 记录", "data": empty_data}, ensure_ascii=False))
        else:
            print("[session-snapshot] 暂无 session 记录")
        return

    sessions = [_parse_session_meta(f) for f in files]

    # --latest: 只返回最新一条（Agent 启动协议 Step 2.5 使用）
    # data 是单个 dict 或 null，不是列表
    if getattr(args, "latest", False):
        latest = sessions[0] if sessions else None
        if args.json:
            print(json.dumps({
                "status": "ok",
                "message": f"最新 session: {latest['session_id']}" if latest else "无记录",
                "data": latest,  # dict or None, never list
            }, ensure_ascii=False))
        else:
            if latest:
                status_icon = "🔄" if latest["status"] == "in-progress" else "✅"
                print(f"{status_icon} {latest['session_id']}  [{latest['checkpoints']} checkpoints]")
                if latest.get("task"):
                    print(f"   任务: {latest['task'][:60]}")
                if latest.get("next_action"):
                    print(f"   下次继续: {latest['next_action'][:60]}")
        return

    if args.json:
        print(json.dumps({
            "status": "ok",
            "message": f"最近 {len(sessions)} 条 session 记录（项目: {project}）",
            "data": sessions,
        }, ensure_ascii=False))
    else:
        print(f"\n最近 session 记录（项目: {project}）\n{'─'*50}")
        for s in sessions:
            status_icon = "✅ completed" if s["status"] == "completed" else "🔄 in-progress"
            task = s.get("task", "未知任务")[:40]
            print(f"  {s['session_id']}  {status_icon}  [{s['checkpoints']} checkpoints]  {task}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Session Snapshot — 会话过程记录工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  记录每次会话的开始、决策检查点、结束事件，支持跨会话续接。
  Agent 在启动协议 Step 2.5 中调用 list --latest --json 快速判断是否有未完成任务。

示例:
  python3 write.py start "实现 request_parser 模块"
  python3 write.py checkpoint "request_parser GREEN" "5/5 PASS" "批次1/3"
  python3 write.py end "完成 request_parser" "response 进行中" "继续实现 response"
  python3 write.py list --latest --json
  python3 write.py list --json
""",
    )
    parser.add_argument("--json", action="store_true", help="输出机器友好的 JSON")
    subparsers = parser.add_subparsers(dest="cmd")

    sp = subparsers.add_parser("start", help="创建新 session")
    sp.add_argument("task", nargs="?", default="未指定任务", help="本次会话的任务描述")

    sp = subparsers.add_parser("checkpoint", help="追加决策检查点")
    sp.add_argument("event", nargs="?", default="未知事件")
    sp.add_argument("result", nargs="?", default="")
    sp.add_argument("state", nargs="?", default="")

    sp = subparsers.add_parser("end", help="关闭当前 session")
    sp.add_argument("completed", nargs="?", default="未记录")
    sp.add_argument("interrupted", nargs="?", default="无")
    sp.add_argument("next_step", nargs="?", default="待定")

    # TASK-AF-03: list 支持 --json 和 --latest
    sp = subparsers.add_parser("list", help="列出最近 session 记录")
    sp.add_argument("--latest", action="store_true",
                    help="只返回最新一条（Agent 启动协议专用）")
    sp.add_argument("-n", type=int, default=14,
                    help="返回最近 N 条（默认 14）")

    args = parser.parse_args()

    dispatch = {
        "start": cmd_start,
        "checkpoint": cmd_checkpoint,
        "end": cmd_end,
        "list": cmd_list,
    }

    if args.cmd in dispatch:
        dispatch[args.cmd](args)
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
