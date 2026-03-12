#!/usr/bin/env python3
"""测试 post-green HOOK 文档和脚本"""
from pathlib import Path
import sys

HOOK_DIR = Path(__file__).parent.parent.parent / ".claude/hooks/post-green"

def test_hook_md_exists():
    assert (HOOK_DIR / "HOOK.md").exists()

def test_run_sh_exists():
    assert (HOOK_DIR / "run.sh").exists()

def test_hook_md_references_validate():
    content = (HOOK_DIR / "HOOK.md").read_text()
    assert "validate-output" in content, "应引用 validate-output skill"

def test_hook_md_references_memory():
    content = (HOOK_DIR / "HOOK.md").read_text()
    assert "memory" in content.lower(), "应引用记忆沉淀"

def test_run_sh_is_executable():
    import os, stat
    path = HOOK_DIR / "run.sh"
    mode = os.stat(path).st_mode
    assert mode & stat.S_IXUSR, "run.sh 应有执行权限"

def test_run_sh_has_pytest_command():
    content = (HOOK_DIR / "run.sh").read_text()
    assert "pytest" in content, "run.sh 应包含 pytest 命令"

if __name__ == "__main__":
    tests = [test_hook_md_exists, test_run_sh_exists,
             test_hook_md_references_validate, test_hook_md_references_memory,
             test_run_sh_is_executable, test_run_sh_has_pytest_command]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
