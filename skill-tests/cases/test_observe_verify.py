#!/usr/bin/env python3
"""测试 observe-verify SKILL 文档结构完整性"""
from pathlib import Path
import subprocess, sys

SKILL_PATH = Path(__file__).parent.parent.parent / ".claude/skills/observe-verify/SKILL.md"
CHECK_IMPL = Path(__file__).parent.parent.parent / ".claude/hooks/observe-verify/check_impl.py"
CHECK_CONTRACT = Path(__file__).parent.parent.parent / ".claude/hooks/observe-verify/check_contract.py"


def test_skill_exists():
    assert SKILL_PATH.exists(), f"SKILL.md 不存在: {SKILL_PATH}"


def test_has_three_layers():
    content = SKILL_PATH.read_text()
    for layer in ["Layer 1", "Layer 2", "Layer 3"]:
        assert layer in content, f"缺少验证层级: {layer}"


def test_has_observe_principle():
    content = SKILL_PATH.read_text()
    assert "观察" in content or "Observe" in content, "应强调观察先于判断原则"


def test_has_checkpoint_record_format():
    content = SKILL_PATH.read_text()
    assert "CHECKPOINT" in content, "应要求将验证结果记录到 CHECKPOINT"


def test_check_impl_exists():
    assert CHECK_IMPL.exists(), f"check_impl.py 不存在: {CHECK_IMPL}"


def test_check_contract_exists():
    assert CHECK_CONTRACT.exists(), f"check_contract.py 不存在: {CHECK_CONTRACT}"


def test_check_impl_detects_pass():
    """check_impl.py 能检测出裸 pass 函数"""
    import tempfile, os
    bad_code = """
def parse_request(conn):
    pass

def build_response(status_code, body):
    pass
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(bad_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(CHECK_IMPL), fname],
            capture_output=True, text=True
        )
        assert result.returncode != 0, "check_impl.py 应检测到裸 pass 并返回非零退出码"
        assert "pass" in result.stdout.lower() or "OV_IMPL" in result.stdout, \
            f"应输出 OV_IMPL 规则违规，实际输出: {result.stdout}"
    finally:
        os.unlink(fname)


def test_check_impl_passes_complete_code():
    """check_impl.py 不应误报完整实现"""
    import tempfile, os
    good_code = """
def build_response(status_code: int, body: bytes) -> bytes:
    status_text = {200: "OK", 404: "Not Found"}.get(status_code, "Unknown")
    header = f"HTTP/1.0 {status_code} {status_text}\\r\\n"
    return header.encode() + b"\\r\\n" + body
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(good_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(CHECK_IMPL), fname],
            capture_output=True, text=True
        )
        assert result.returncode == 0, \
            f"完整实现不应报错，实际输出: {result.stdout}"
    finally:
        os.unlink(fname)


def test_check_impl_detects_hardcoded_return():
    """check_impl.py 能检测出未使用参数的可疑函数（硬编码返回）"""
    import tempfile, os
    suspicious_code = """
def route(path: str, htdocs_root: str) -> str:
    return "static"
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(suspicious_code)
        fname = f.name
    try:
        result = subprocess.run(
            [sys.executable, str(CHECK_IMPL), fname],
            capture_output=True, text=True
        )
        # 硬编码是 WARNING 级别，不一定非零退出，但应有输出
        has_warning = "OV_IMPL_004" in result.stdout or "⚠️" in result.stdout
        assert has_warning, f"应对未使用参数发出警告，实际输出: {result.stdout}"
    finally:
        os.unlink(fname)


def make_plan_workspace(module_body: str) -> tuple[Path, Path]:
    import tempfile, json

    workspace_root = Path(tempfile.mkdtemp(prefix="observe_verify_plan_"))
    project_name = "demo_project"
    project_root = workspace_root / "projects" / project_name
    impl_dir = project_root / "harness"
    spec_dir = project_root / "modules" / "demo"
    docs_dir = project_root / "docs"

    impl_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    (workspace_root / "CLAUDE.md").write_text(
        f"PROJECT: {project_name}\nPROJECT_PATH: projects/{project_name}\n",
        encoding="utf-8",
    )
    (impl_dir / "demo.py").write_text(module_body, encoding="utf-8")
    (spec_dir / "SPEC.md").write_text(
        """# SPEC: demo\n\n```python\ndef run_demo(value: int) -> int: ...\n```\n""",
        encoding="utf-8",
    )
    (docs_dir / "plan.json").write_text(
        json.dumps(
            {
                "project": "demo_project",
                "batches": [
                    {
                        "name": "Batch 1",
                        "modules": [
                            {
                                "id": "T-001",
                                "name": "demo",
                                "spec_path": "modules/demo/SPEC.md",
                                "impl_path": "harness/demo.py",
                                "path": "harness/demo.py",
                                "state": "pending",
                            }
                        ],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return workspace_root, project_root


def test_check_impl_resolves_impl_path_from_plan_module():
    import shutil

    workspace_root, _project_root = make_plan_workspace("def run_demo(value: int) -> int:\n    return value + 1\n")
    try:
        result = subprocess.run(
            [sys.executable, str(CHECK_IMPL), "--module", "demo"],
            capture_output=True,
            text=True,
            cwd=str(workspace_root),
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "检查通过" in result.stdout
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


def test_check_contract_resolves_spec_and_impl_from_plan_module():
    import shutil

    workspace_root, _project_root = make_plan_workspace("def run_demo(value: int) -> int:\n    return value + 1\n")
    try:
        result = subprocess.run(
            [sys.executable, str(CHECK_CONTRACT), "--module", "demo"],
            capture_output=True,
            text=True,
            cwd=str(workspace_root),
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert "CONTRACT OK" in result.stdout
    finally:
        shutil.rmtree(workspace_root, ignore_errors=True)


if __name__ == "__main__":
    tests = [
        test_skill_exists,
        test_has_three_layers,
        test_has_observe_principle,
        test_has_checkpoint_record_format,
        test_check_impl_exists,
        test_check_contract_exists,
        test_check_impl_detects_pass,
        test_check_impl_passes_complete_code,
        test_check_impl_detects_hardcoded_return,
        test_check_impl_resolves_impl_path_from_plan_module,
        test_check_contract_resolves_spec_and_impl_from_plan_module,
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
