#!/usr/bin/env python3
"""
PreToolUse Hook: 检测对测试文件的写入，要求提供理由
路径匹配: test_*.py 或 validate_*.py
输出 block + 说明（要求 Claude 先解释原因再决策）
"""
import json, sys, os, re

TEST_PATTERNS = [
    re.compile(r'test_.*\.py$'),
    re.compile(r'validate_.*\.py$'),
]

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    path = tool_input.get("path") or tool_input.get("file_path") or ""
    basename = os.path.basename(path)

    if any(p.match(basename) for p in TEST_PATTERNS):
        # Check if this is a CREATE (new file) vs MODIFY (existing)
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        abs_path = os.path.abspath(os.path.join(project_dir, path))
        is_new = not os.path.exists(abs_path)

        if not is_new:
            result = {
                "decision": "block",
                "reason": (
                    f"⚠️  BLOCKED: 检测到修改测试文件 {basename}\n\n"
                    "核心约束：测试失败时只允许修改实现代码，不允许修改测试。\n\n"
                    "如果测试本身确实有 bug（例如 fixture 生成逻辑错误），"
                    "请先在 HUMAN_NOTES.md 中记录修改原因，再重新提交本次操作。\n"
                    "合法修改必须：(1)在 HUMAN_NOTES.md 记录原因 (2)同步重新生成 fixture"
                )
            }
            print(json.dumps(result))

if __name__ == "__main__":
    main()
