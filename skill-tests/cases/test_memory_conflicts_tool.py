#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: memory-conflicts arbitration tool tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/memory-conflicts/run.py"


def make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="memory_conflicts_project_", dir=str(FRAMEWORK_ROOT / "projects")))
    (root / "memory" / "rules").mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("# conflict fixture\n工作模式: L\n", encoding="utf-8")
    (root / "memory" / "INDEX.md").write_text("# memory\n", encoding="utf-8")
    (root / "memory" / "rules" / "old.md").write_text(
        "---\nid: MEM_TEST_CONFLICT\nstatus: deprecated\nconfidence: low\nupdated: 2026-01-01\n---\n# Same Rule\n必须先写旧规则。\n",
        encoding="utf-8",
    )
    (root / "memory" / "rules" / "new.md").write_text(
        "---\nid: MEM_TEST_CONFLICT\nstatus: active\nconfidence: high\nupdated: 2026-04-01\n---\n# Same Rule\n必须先写新规则，并保留证据。\n",
        encoding="utf-8",
    )
    return root


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"memory-conflicts tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_detects_duplicate_id_and_arbitrates_active_high_confidence_winner():
    project = make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(TOOL_PATH), "--project", project.name, "--json"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["status"] == "warning", payload
        conflicts = payload["data"]["conflicts"]
        match = next((item for item in conflicts if item["key"] == "MEM_TEST_CONFLICT"), None)
        assert match, f"应检测重复 memory id 冲突: {conflicts}"
        assert match["type"] == "duplicate_id"
        assert match["arbitration"]["winner"].endswith("new.md"), match["arbitration"]
        assert match["arbitration"]["decision"] in {"prefer_active_over_inactive", "keep_winner_review_losers"}
    finally:
        shutil.rmtree(project, ignore_errors=True)


if __name__ == "__main__":
    tests = [test_tool_exists_and_syntax_ok, test_detects_duplicate_id_and_arbitrates_active_high_confidence_winner]
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
    sys.exit(failed)
