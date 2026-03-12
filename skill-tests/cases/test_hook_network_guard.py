#!/usr/bin/env python3
"""测试 network-guard HOOK 文档和脚本"""
from pathlib import Path
import subprocess, sys

HOOK_DIR = Path(__file__).parent.parent.parent / ".claude/hooks/network-guard"

def test_hook_md_exists():
    assert (HOOK_DIR / "HOOK.md").exists()

def test_check_py_exists():
    assert (HOOK_DIR / "check.py").exists()

def test_hook_md_has_checklist():
    content = (HOOK_DIR / "HOOK.md").read_text()
    assert "recv" in content and "sendall" in content

def test_check_py_detects_bare_except():
    import tempfile, os
    bad_code = """
import socket
def handle(conn):
    while True:
        data = conn.recv(4096)
        buf = data
    try:
        x = 1
    except Exception:
        pass
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(bad_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_DIR / "check.py"), fname],
            capture_output=True, text=True
        )
        # Should detect issues (non-zero exit or warning output)
        has_issue = result.returncode != 0 or "⚠️" in result.stdout or "❌" in result.stdout
        assert has_issue, f"check.py 未检测到问题\n stdout: {result.stdout}"
    finally:
        os.unlink(fname)

def test_check_py_passes_clean_code():
    import tempfile, os
    good_code = """
import socket
def handle(conn):
    while True:
        data = conn.recv(4096)
        if not data:
            break
    try:
        x = 1
    except (socket.timeout, ConnectionResetError, OSError):
        pass
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(good_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(HOOK_DIR / "check.py"), fname],
            capture_output=True, text=True
        )
        assert result.returncode == 0, f"clean code 误报\n stdout: {result.stdout}"
    finally:
        os.unlink(fname)

if __name__ == "__main__":
    tests = [test_hook_md_exists, test_check_py_exists, test_hook_md_has_checklist,
             test_check_py_detects_bare_except, test_check_py_passes_clean_code]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✅ {t.__name__}")
        except AssertionError as e:
            print(f"  ❌ {t.__name__}: {e}")
            failed += 1
    sys.exit(failed)
