#!/usr/bin/env python3
"""测试 context-budget HOOK 文档结构完整性"""
from pathlib import Path
import subprocess, sys

HOOK_PATH = Path(__file__).parent.parent.parent / ".claude/hooks/context-budget/HOOK.md"
HANDOFF_PY = Path(__file__).parent.parent.parent / ".claude/hooks/context-budget/handoff.py"
TRACKER_PY = Path(__file__).parent.parent.parent / ".claude/tools/plan-tracker/tracker.py"


def test_hook_exists():
    assert HOOK_PATH.exists(), f"HOOK.md 不存在: {HOOK_PATH}"


def test_handoff_py_exists():
    assert HANDOFF_PY.exists(), f"handoff.py 不存在: {HANDOFF_PY}"


def test_tracker_py_exists():
    assert TRACKER_PY.exists(), f"tracker.py 不存在: {TRACKER_PY}"


def test_hook_has_decision_tree():
    content = HOOK_PATH.read_text()
    assert "充裕" in content and "紧张" in content and "危险" in content, \
        "应包含三种 budget 状态的决策树"


def test_hook_has_handoff_json_format():
    content = HOOK_PATH.read_text()
    assert "HANDOFF.json" in content, "应定义 HANDOFF.json 格式"
    assert "next_action" in content, "HANDOFF.json 应包含 next_action 字段"


def test_hook_has_git_checkpoint():
    content = HOOK_PATH.read_text()
    assert "git" in content and "commit" in content, "应要求在 budget 危险时提交 git checkpoint"


def test_hook_mentions_json_over_markdown():
    content = HOOK_PATH.read_text()
    assert "JSON" in content, "应说明为什么用 JSON 而不是 markdown（模型不会随意覆盖）"


def test_handoff_py_syntax():
    """handoff.py 语法正确"""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(HANDOFF_PY)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"handoff.py 语法错误: {result.stderr}"


def test_handoff_py_has_subcommands():
    """handoff.py 支持 write/read/clear 子命令"""
    result = subprocess.run(
        [sys.executable, str(HANDOFF_PY), "--help"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    for cmd in ["write", "read", "clear"]:
        assert cmd in output, f"handoff.py 应支持子命令: {cmd}"


def test_tracker_py_syntax():
    """tracker.py 语法正确"""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(TRACKER_PY)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"tracker.py 语法错误: {result.stderr}"


def test_tracker_py_has_subcommands():
    """tracker.py 支持 status/complete/skip/validate 子命令"""
    result = subprocess.run(
        [sys.executable, str(TRACKER_PY), "--help"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    for cmd in ["status", "complete", "skip", "validate"]:
        assert cmd in output, f"tracker.py 应支持子命令: {cmd}"


if __name__ == "__main__":
    tests = [
        test_hook_exists,
        test_handoff_py_exists,
        test_tracker_py_exists,
        test_hook_has_decision_tree,
        test_hook_has_handoff_json_format,
        test_hook_has_git_checkpoint,
        test_hook_mentions_json_over_markdown,
        test_handoff_py_syntax,
        test_handoff_py_has_subcommands,
        test_tracker_py_syntax,
        test_tracker_py_has_subcommands,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
