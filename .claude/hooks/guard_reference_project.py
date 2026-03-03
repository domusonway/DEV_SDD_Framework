#!/usr/bin/env python3
"""
PreToolUse Hook: 防止写入参考项目目录（只读基准，禁止修改）
保护目录：reference_project/ 或 REFERENCE_DIR 环境变量指定的目录
"""
import json, sys, os

PROTECTED_DIRS = ["reference_project"]  # 可通过环境变量扩展

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    path = tool_input.get("path") or tool_input.get("file_path") or ""
    if not path:
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    abs_path = os.path.abspath(os.path.join(project_dir, path))

    for protected in PROTECTED_DIRS:
        protected_abs = os.path.abspath(os.path.join(project_dir, protected))
        if abs_path.startswith(protected_abs + os.sep) or abs_path == protected_abs:
            result = {
                "decision": "block",
                "reason": (
                    f"🚫 BLOCKED: 禁止写入参考项目目录\n"
                    f"路径: {path}\n"
                    f"参考项目是只读基准，所有实现必须写在 modules/ 下。\n"
                    f"如需查看参考代码请使用 Read 工具。"
                )
            }
            print(json.dumps(result))
            return

if __name__ == "__main__":
    main()
