#!/usr/bin/env python3
"""
skill-tests/cases/test_workflow_migration_docs.py
Layer 1: workflow migration docs regression guard

用途:
  固化 README.md 中迁移/发布指引的关键语义，防止工作流入口和回退说明漂移。
"""

from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).parent.parent.parent
README_PATH = FRAMEWORK_ROOT / "README.md"


def read_readme() -> str:
    assert README_PATH.exists(), f"README 不存在: {README_PATH}"
    return README_PATH.read_text(encoding="utf-8")


def test_workflow_migration_commands_and_artifacts_are_documented():
    content = read_readme()

    for fragment in ["INIT", "REDEFINE", "UPDATE_TODO", "START_WORK", "FIX", "plan.json", "TODO"]:
        assert fragment in content, f"README.md 缺少迁移/工作流关键片段: {fragment}"

    assert "INIT → REDEFINE → UPDATE_TODO → START_WORK → FIX" in content, "README.md 缺少推荐命令流"
    assert "`plan.json` 为准" in content, "README.md 缺少 plan.json 权威性说明"
    assert "`TODO.md` 为管理视图" in content, "README.md 缺少 TODO 管理视图说明"


def test_workflow_migration_fallback_and_compatibility_guidance_exist():
    content = read_readme()

    for fragment in ["回滚", "fallback", "兼容别名", "兼容", "旧 markdown 只能作为 fallback 参考"]:
        assert fragment in content, f"README.md 缺少回退/兼容指引: {fragment}"

    assert "REDEFIND" in content, "README.md 缺少兼容别名说明"
    assert "START_WORK" in content and "FIX" in content, "README.md 缺少迁移后 fallback 工作流"


if __name__ == "__main__":
    tests = [
        test_workflow_migration_commands_and_artifacts_are_documented,
        test_workflow_migration_fallback_and_compatibility_guidance_exist,
    ]
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  ✅ {test.__name__}")
        except AssertionError as exc:
            print(f"  ❌ {test.__name__}: {exc}")
            failed += 1
        except Exception as exc:
            print(f"  ❌ {test.__name__} [ERROR]: {exc}")
            failed += 1
    print(f"\n{'─' * 50}")
    print(f"  {len(tests) - failed}/{len(tests)} 通过")
    raise SystemExit(failed)
