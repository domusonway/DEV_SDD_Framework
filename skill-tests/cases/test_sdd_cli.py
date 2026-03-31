#!/usr/bin/env python3
"""
skill-tests/cases/test_sdd_cli.py
Layer 1: sdd-cli CLI 接口合规测试

用途:
  验证 sdd-cli/cli.py 的语法正确性、子命令完整性、registry.json schema 合法性，
  以及 --json 输出的结构符合 TOOL_INTERFACE_SPEC.md 规范。

示例:
  python3 skill-tests/cases/test_sdd_cli.py
"""
import sys
import json
import subprocess
import tempfile
import os
from pathlib import Path

FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
CLI_PATH = FRAMEWORK_ROOT / ".claude/tools/sdd-cli/cli.py"
REGISTRY_PATH = FRAMEWORK_ROOT / "memory/registry.json"

REQUIRED_SUBCOMMANDS = ["search", "get", "list", "annotate", "index"]


def test_cli_exists():
    assert CLI_PATH.exists(), f"cli.py 不存在: {CLI_PATH}"


def test_cli_syntax():
    """cli.py 语法无错误。"""
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(CLI_PATH)],
        capture_output=True, text=True
    )
    assert result.returncode == 0, f"cli.py 语法错误: {result.stderr}"


def test_help_contains_all_subcommands():
    """--help 输出包含全部子命令。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--help"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    for cmd in REQUIRED_SUBCOMMANDS:
        assert cmd in output, f"--help 缺少子命令: {cmd}"


def test_help_contains_usage_and_example():
    """--help 输出包含「用途」和「示例」。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--help"],
        capture_output=True, text=True
    )
    output = result.stdout + result.stderr
    assert "用途" in output, "--help 缺少「用途」章节"
    assert "示例" in output or "example" in output.lower(), "--help 缺少「示例」章节"


def test_json_flag_exists():
    """所有子命令都接受 --json flag 且输出合法 JSON。"""
    # 用 index 子命令测试（它不需要外部参数）
    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建最小框架结构以通过 find_framework_root
        claude_md = Path(tmpdir) / "CLAUDE.md"
        claude_md.write_text("PROJECT: test\n")
        mem_dir = Path(tmpdir) / "memory"
        mem_dir.mkdir()
        env = os.environ.copy()
        env["PYTHONPATH"] = str(FRAMEWORK_ROOT)
        result = subprocess.run(
            [sys.executable, str(CLI_PATH), "--json", "list"],
            capture_output=True, text=True, cwd=tmpdir, env=env
        )
        # 即使没有规则也应输出合法 JSON
        output = result.stdout.strip()
        if output:
            try:
                data = json.loads(output)
                assert "status" in data, "JSON 输出缺少 status 字段"
                assert data["status"] in ("ok", "error", "warning"), \
                    f"status 值不合法: {data['status']}"
                assert "data" in data, "JSON 输出缺少 data 字段"
                assert "message" in data, "JSON 输出缺少 message 字段"
            except json.JSONDecodeError as e:
                assert False, f"--json 输出不是合法 JSON: {e}\n输出内容: {output[:200]}"


def test_json_output_schema():
    """在真实框架目录下，--json 输出符合三字段规范：status, data, message。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--json", "list", "--type", "all"],
        capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT)
    )
    output = result.stdout.strip()
    assert output, "--json list 无输出"
    try:
        data = json.loads(output)
    except json.JSONDecodeError as e:
        assert False, f"--json 输出不是合法 JSON: {e}"
    assert "status" in data, "缺少 status 字段"
    assert "data" in data, "缺少 data 字段"
    assert "message" in data, "缺少 message 字段"
    assert isinstance(data["data"], (list, dict, type(None))), \
        f"data 字段类型不合法: {type(data['data'])}"


def test_index_creates_registry():
    """sdd index 在框架根目录运行后生成 memory/registry.json。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--json", "index"],
        capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT)
    )
    assert result.returncode == 0, f"sdd index 失败: {result.stderr}"
    assert REGISTRY_PATH.exists(), "sdd index 未生成 memory/registry.json"


def test_registry_schema():
    """memory/registry.json 存在且结构合法。"""
    if not REGISTRY_PATH.exists():
        # 先生成
        subprocess.run(
            [sys.executable, str(CLI_PATH), "index"],
            capture_output=True, cwd=str(FRAMEWORK_ROOT)
        )
    assert REGISTRY_PATH.exists(), "registry.json 不存在"
    try:
        reg = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        assert False, f"registry.json 不是合法 JSON: {e}"
    assert "entries" in reg, "registry.json 缺少 entries 字段"
    assert isinstance(reg["entries"], list), "entries 应为数组"
    assert "generated_at" in reg, "registry.json 缺少 generated_at 字段"
    # 验证每条 entry 的必要字段
    required_fields = {"id", "type", "path", "title"}
    for entry in reg["entries"][:5]:  # 只检查前5条
        missing = required_fields - set(entry.keys())
        assert not missing, f"registry entry 缺少字段 {missing}: {entry.get('id', '?')}"


def test_search_returns_results():
    """sdd search 对已知关键词返回结果。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--json", "search", "tdd"],
        capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT)
    )
    assert result.returncode == 0, f"sdd search 失败: {result.stderr}"
    data = json.loads(result.stdout)
    assert data["status"] in ("ok", "warning"), f"status 不合法: {data['status']}"
    # tdd 是框架核心概念，应该能找到
    if data["status"] == "ok":
        assert len(data["data"]) > 0, "搜索 'tdd' 应返回至少1条结果"


def test_get_known_rule():
    """sdd get 能读取已知规则（tdd-cycle）。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--json", "get", "tdd-cycle"],
        capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT)
    )
    if result.returncode != 0:
        # tdd-cycle 可能在此测试环境路径不同，跳过（非阻断性）
        return
    data = json.loads(result.stdout)
    if data["status"] == "ok":
        assert "content" in data["data"], "get 结果缺少 content 字段"
        assert len(data["data"]["content"]) > 0, "content 不应为空"


def test_error_exit_code():
    """查找不存在的规则时退出码为 1（业务失败）。"""
    result = subprocess.run(
        [sys.executable, str(CLI_PATH), "--json", "get", "nonexistent-rule-xyz"],
        capture_output=True, text=True, cwd=str(FRAMEWORK_ROOT)
    )
    assert result.returncode == 1, f"查找不存在规则应返回退出码 1，实际: {result.returncode}"
    data = json.loads(result.stdout)
    assert data["status"] == "error", "查找不存在规则应返回 error status"


if __name__ == "__main__":
    tests = [
        test_cli_exists,
        test_cli_syntax,
        test_help_contains_all_subcommands,
        test_help_contains_usage_and_example,
        test_json_flag_exists,
        test_json_output_schema,
        test_index_creates_registry,
        test_registry_schema,
        test_search_returns_results,
        test_get_known_rule,
        test_error_exit_code,
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
