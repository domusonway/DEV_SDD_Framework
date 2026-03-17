#!/usr/bin/env python3
"""
session-snapshot write.py
将会话快照写入 projects/<PROJECT>/memory/sessions/ 目录

用法:
  python3 write.py start "<task>"
  python3 write.py checkpoint "<event>" "<result>" "<state>"
  python3 write.py end "<completed>" "<interrupted>" "<next_step>"

PROJECT 从环境变量或 CLAUDE.md 读取。
"""
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────────────────────────────

def find_project_root() -> Path:
    """从当前目录向上找到包含 CLAUDE.md 的框架根目录"""
    current = Path.cwd()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    return current


def get_project_name(root: Path) -> str:
    """从 CLAUDE.md 读取当前激活项目名"""
    claude_md = root / "CLAUDE.md"
    if not claude_md.exists():
        return os.environ.get("PROJECT", "unknown")
    content = claude_md.read_text(encoding="utf-8")
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return os.environ.get("PROJECT", "unknown")


def get_session_dir(root: Path, project: str) -> Path:
    """返回 sessions 目录，不存在则创建"""
    session_dir = root / "projects" / project / "memory" / "sessions"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def get_current_session_file(session_dir: Path) -> Path | None:
    """找到今天最新的 in-progress session 文件"""
    today = datetime.now().strftime("%Y-%m-%d")
    files = sorted(session_dir.glob(f"{today}_*.md"), reverse=True)
    for f in files:
        content = f.read_text(encoding="utf-8")
        if "status: in-progress" in content:
            return f
    return None


def create_session_file(session_dir: Path, session_id: str) -> Path:
    """创建新的 session 文件"""
    filename = f"{session_id}.md"
    return session_dir / filename


# ── 命令实现 ──────────────────────────────────────────────────────────────────

def cmd_start(task: str):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)

    now = datetime.now()
    session_id = now.strftime("%Y-%m-%d_%H-%M")
    time_str = now.strftime("%H:%M")

    # 检查是否有上次 in-progress
    prev = get_current_session_file(session_dir)
    resume_note = f"续接 {prev.stem}" if prev else "新会话"

    filepath = create_session_file(session_dir, session_id)

    content = f"""---
status: in-progress
session_id: {session_id}
project: {project}
task: {task}
---

[SESSION-START]
时间: {time_str}
加载记忆: 待填写
项目状态: 待填写
续接: {resume_note}
[/SESSION-START]
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"[session-snapshot] 已创建: {filepath.name}")
    return str(filepath)


def cmd_checkpoint(event: str, result: str, state: str):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)

    filepath = get_current_session_file(session_dir)
    if not filepath:
        print("[session-snapshot] ⚠️  无 in-progress session，请先执行 start")
        return

    time_str = datetime.now().strftime("%H:%M")
    block = f"""
[CHECKPOINT {time_str}]
事件: {event}
决策/结果: {result}
当前状态: {state}
[/CHECKPOINT]
"""
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(block)
    print(f"[session-snapshot] ✅ 检查点已写入: {filepath.name}")


def cmd_end(completed: str, interrupted: str, next_step: str):
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)

    filepath = get_current_session_file(session_dir)
    if not filepath:
        # 无 in-progress 文件，创建一个简单的结束记录
        now = datetime.now()
        session_id = now.strftime("%Y-%m-%d_%H-%M")
        filepath = create_session_file(session_dir, session_id)
        filepath.write_text(
            f"---\nstatus: in-progress\nsession_id: {session_id}\n"
            f"project: {project}\ntask: 未记录\n---\n\n",
            encoding="utf-8"
        )

    time_str = datetime.now().strftime("%H:%M")
    block = f"""
[SESSION-END]
时间: {time_str}
完成了: {completed}
未完成: {interrupted}
下次继续: {next_step}
记忆候选: 无
[/SESSION-END]
"""
    # 追加 session-end
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(block)

    # 更新 status 为 completed
    content = filepath.read_text(encoding="utf-8")
    content = content.replace("status: in-progress", "status: completed", 1)
    filepath.write_text(content, encoding="utf-8")

    print(f"[session-snapshot] ✅ 会话已关闭: {filepath.name}")


def cmd_list():
    """列出最近 7 天的 session 文件及状态"""
    root = find_project_root()
    project = get_project_name(root)
    session_dir = get_session_dir(root, project)

    files = sorted(session_dir.glob("*.md"), reverse=True)[:14]
    if not files:
        print("[session-snapshot] 暂无 session 记录")
        return

    print(f"\n最近 session 记录（项目: {project}）\n{'─'*50}")
    for f in files:
        content = f.read_text(encoding="utf-8")
        status = "✅ completed" if "status: completed" in content else "🔄 in-progress"
        checkpoints = content.count("[CHECKPOINT")
        task_match = re.search(r"^task: (.+)$", content, re.MULTILINE)
        task = task_match.group(1)[:40] if task_match else "未知任务"
        print(f"  {f.stem}  {status}  [{checkpoints} checkpoints]  {task}")
    print()


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python3 write.py <start|checkpoint|end|list> [args...]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        task = sys.argv[2] if len(sys.argv) > 2 else "未指定任务"
        cmd_start(task)

    elif cmd == "checkpoint":
        event = sys.argv[2] if len(sys.argv) > 2 else "未知事件"
        result = sys.argv[3] if len(sys.argv) > 3 else ""
        state = sys.argv[4] if len(sys.argv) > 4 else ""
        cmd_checkpoint(event, result, state)

    elif cmd == "end":
        completed = sys.argv[2] if len(sys.argv) > 2 else "未记录"
        interrupted = sys.argv[3] if len(sys.argv) > 3 else "无"
        next_step = sys.argv[4] if len(sys.argv) > 4 else "待定"
        cmd_end(completed, interrupted, next_step)

    elif cmd == "list":
        cmd_list()

    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
