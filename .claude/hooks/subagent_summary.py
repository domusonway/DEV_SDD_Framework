#!/usr/bin/env python3
"""
SubagentStop Hook: 记录 subagent 完成事件到运行日志
"""
import json, sys, os
from datetime import datetime

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    log_path = os.path.join(project_dir, "tests", "results_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    agent_name = data.get("agent_name", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] subagent-stop: {agent_name}\n")

if __name__ == "__main__":
    main()
