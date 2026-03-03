#!/usr/bin/env python3
"""
PostToolUse Hook: 捕获 pytest 运行结果，追加到 tests/results_log.txt
用于 Memory 积累和趋势分析
"""
import json, sys, os, re
from datetime import datetime

PYTEST_PATTERN = re.compile(
    r'(PASSED|FAILED|ERROR|passed|failed|error).*?(\d+\s+(?:passed|failed|error))',
    re.IGNORECASE
)
SUMMARY_PATTERN = re.compile(
    r'(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) error)?',
    re.IGNORECASE
)

def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    output = data.get("tool_output", "") or ""
    if not isinstance(output, str):
        output = str(output)

    # Only log if this looks like a pytest run
    if "pytest" not in output.lower() and "passed" not in output.lower():
        sys.exit(0)

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", ".")
    log_path = os.path.join(project_dir, "tests", "results_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # Extract summary line
    summary_match = SUMMARY_PATTERN.search(output)
    summary = summary_match.group(0) if summary_match else "no summary"

    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] {summary}\n")

if __name__ == "__main__":
    main()
