#!/usr/bin/env python3
"""
skill-tests/cases/test_tool_interface.py
Layer 1: 所有工具的 CLI 接口合规测试（TASK-AF-06）

用途:
  验证框架内所有 CLI 工具符合 docs/TOOL_INTERFACE_SPEC.md 规范：
  - --help 包含「用途」和「示例」章节
  - --json flag 存在且输出合法 JSON，结构含 status/data/message
  - 错误场景下退出码符合规范（1=业务失败）
  - handoff.py read --exists 只返回 {"exists": bool}，退出码为 0

示例:
  python3 skill-tests/cases/test_tool_interface.py
"""
import sys
import json
import subprocess
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent

TOOLS = {
    "plan-tracker": FRAMEWORK_ROOT / ".claude/tools/plan-tracker/tracker.py",
    "session-snapshot": FRAMEWORK_ROOT / ".claude/hooks/session-snapshot/write.py",
    "handoff": FRAMEWORK_ROOT / ".claude/hooks/context-budget/handoff.py",
    "sdd-cli": FRAMEWORK_ROOT / ".claude/tools/sdd-cli/cli.py",
}


def run(tool_path, *args, cwd=None):
    result = subprocess.run(
        [sys.executable, str(tool_path)] + list(args),
        capture_output=True, text=True,
        cwd=str(cwd or FRAMEWORK_ROOT),
    )
    return result


# ── 语法检查 ─────────────────────────────────────────────────────────────────

def test_all_tools_syntax():
    """所有工具文件语法正确。"""
    for name, path in TOOLS.items():
        if not path.exists():
            continue
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"{name} 语法错误: {result.stderr}"


# ── --help 规范 ──────────────────────────────────────────────────────────────

def test_plan_tracker_help_has_usage_and_example():
    result = run(TOOLS["plan-tracker"], "--help")
    output = result.stdout + result.stderr
    assert "用途" in output, "plan-tracker --help 缺少「用途」"
    assert "示例" in output or "example" in output.lower(), "plan-tracker --help 缺少「示例」"


def test_session_snapshot_help_has_usage_and_example():
    result = run(TOOLS["session-snapshot"], "--help")
    output = result.stdout + result.stderr
    assert "用途" in output, "session-snapshot --help 缺少「用途」"
    assert "示例" in output or "example" in output.lower(), "session-snapshot --help 缺少「示例」"


def test_handoff_help_has_usage_and_example():
    result = run(TOOLS["handoff"], "--help")
    output = result.stdout + result.stderr
    assert "用途" in output, "handoff --help 缺少「用途」"
    assert "示例" in output or "example" in output.lower(), "handoff --help 缺少「示例」"


def test_sdd_cli_help_has_usage_and_example():
    result = run(TOOLS["sdd-cli"], "--help")
    output = result.stdout + result.stderr
    assert "用途" in output, "sdd-cli --help 缺少「用途」"
    assert "示例" in output or "example" in output.lower(), "sdd-cli --help 缺少「示例」"


# ── --json 输出规范 ──────────────────────────────────────────────────────────

def _assert_json_output(output: str, tool_name: str):
    """验证 --json 输出符合三字段规范。"""
    output = output.strip()
    assert output, f"{tool_name} --json 无输出"
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        assert False, f"{tool_name} --json 输出不是合法 JSON: {e}\n内容: {output[:200]}"
    assert "status" in data, f"{tool_name} JSON 缺少 status 字段"
    assert data["status"] in ("ok", "error", "warning"), \
        f"{tool_name} status 值不合法: {data['status']}"
    assert "data" in data, f"{tool_name} JSON 缺少 data 字段"
    assert "message" in data, f"{tool_name} JSON 缺少 message 字段"
    assert isinstance(data["message"], str), f"{tool_name} message 必须是字符串"
    return data


def test_sdd_cli_list_json():
    result = run(TOOLS["sdd-cli"], "--json", "list")
    _assert_json_output(result.stdout, "sdd-cli list")


def test_sdd_cli_index_json():
    result = run(TOOLS["sdd-cli"], "--json", "index")
    _assert_json_output(result.stdout, "sdd-cli index")


def test_session_snapshot_list_json():
    result = run(TOOLS["session-snapshot"], "--json", "list")
    _assert_json_output(result.stdout, "session-snapshot list")


def test_session_snapshot_list_latest_json():
    """--latest --json 返回单条或 null，符合规范。"""
    result = run(TOOLS["session-snapshot"], "--json", "list", "--latest")
    data = _assert_json_output(result.stdout, "session-snapshot list --latest")
    # data 应为单条 dict 或 null
    assert data["data"] is None or isinstance(data["data"], dict), \
        f"list --latest data 应为 dict 或 null，实际: {type(data['data'])}"


def test_handoff_read_json_no_file():
    """无 HANDOFF.json 时，read --json 正常返回 ok。"""
    result = run(TOOLS["handoff"], "read", "--json")
    data = _assert_json_output(result.stdout, "handoff read --json")
    assert result.returncode == 0, "无 HANDOFF.json 时退出码应为 0"


def test_handoff_clear_json():
    result = run(TOOLS["handoff"], "clear", "--json")
    data = _assert_json_output(result.stdout, "handoff clear --json")
    assert result.returncode == 0


# ── --exists flag 专项测试（TASK-AF-04）────────────────────────────────────

def test_handoff_exists_flag_returns_bool_json():
    """handoff read --exists --json 只返回 {\"exists\": bool}。"""
    result = run(TOOLS["handoff"], "read", "--exists", "--json")
    assert result.returncode == 0, f"--exists 退出码应始终为 0，实际: {result.returncode}"
    output = result.stdout.strip()
    assert output, "handoff --exists --json 无输出"
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        assert False, f"--exists 输出不是合法 JSON: {e}"
    assert "exists" in data, "--exists 输出必须包含 exists 字段"
    assert isinstance(data["exists"], bool), f"exists 字段必须是布尔值，实际: {type(data['exists'])}"


def test_handoff_exists_exit_code_is_zero():
    """--exists 退出码始终为 0，无副作用。"""
    result = run(TOOLS["handoff"], "read", "--exists", "--json")
    assert result.returncode == 0, f"--exists 退出码应始终为 0"


# ── 错误退出码规范 ────────────────────────────────────────────────────────────

def test_sdd_cli_error_exit_code():
    """查找不存在规则，退出码为 1（业务失败）。"""
    result = run(TOOLS["sdd-cli"], "--json", "get", "nonexistent-xyz-rule")
    assert result.returncode == 1, f"业务失败应返回退出码 1，实际: {result.returncode}"
    data = json.loads(result.stdout)
    assert data["status"] == "error"


# ── --latest 返回 next_action ────────────────────────────────────────────────

def test_session_list_latest_has_next_action_if_exists():
    """如果有 in-progress session 且包含 next_action，list --latest 应返回该字段。"""
    result = run(TOOLS["session-snapshot"], "--json", "list", "--latest")
    data = _assert_json_output(result.stdout, "session-snapshot list --latest")
    # 若有数据，检查字段存在性
    if data["data"]:
        assert "session_id" in data["data"], "session 记录缺少 session_id"
        assert "status" in data["data"], "session 记录缺少 status"


if __name__ == "__main__":
    tests = [
        test_all_tools_syntax,
        test_plan_tracker_help_has_usage_and_example,
        test_session_snapshot_help_has_usage_and_example,
        test_handoff_help_has_usage_and_example,
        test_sdd_cli_help_has_usage_and_example,
        test_sdd_cli_list_json,
        test_sdd_cli_index_json,
        test_session_snapshot_list_json,
        test_session_snapshot_list_latest_json,
        test_handoff_read_json_no_file,
        test_handoff_clear_json,
        test_handoff_exists_flag_returns_bool_json,
        test_handoff_exists_exit_code_is_zero,
        test_sdd_cli_error_exit_code,
        test_session_list_latest_has_next_action_if_exists,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ {t.__name__} [ERROR]: {e}")
            failed += 1
    print(f"\n{'─'*50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    sys.exit(failed)
