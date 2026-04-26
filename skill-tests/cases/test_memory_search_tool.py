#!/usr/bin/env python3
from __future__ import annotations

"""Layer 1: memory-search tool tests."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


FRAMEWORK_ROOT = Path(__file__).resolve().parent.parent.parent
TOOL_PATH = FRAMEWORK_ROOT / ".claude/tools/memory-search/run.py"
START_WORK = FRAMEWORK_ROOT / ".claude/tools/start-work/run.py"
CONTEXT_PROBE_SKILL = FRAMEWORK_ROOT / ".claude/skills/context-probe/SKILL.md"
ENV_EXAMPLE = FRAMEWORK_ROOT / ".env.example"
CONFIG_YAML = FRAMEWORK_ROOT / "config.yaml"


def make_project() -> Path:
    root = Path(tempfile.mkdtemp(prefix="memory_search_project_", dir=str(FRAMEWORK_ROOT / "projects")))
    (root / "docs").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "testing").mkdir(parents=True, exist_ok=True)
    (root / "memory" / "sessions").mkdir(parents=True, exist_ok=True)
    (root / "CLAUDE.md").write_text("# test\n工作模式: L\n", encoding="utf-8")
    (root / "memory" / "INDEX.md").write_text("# memory\n", encoding="utf-8")
    (root / "memory" / "testing" / "typeerror-bytes-str.md").write_text(
        "# TypeError bytes str rule\n遇到 TypeError bytes str 时先检查 SPEC dtype。\n",
        encoding="utf-8",
    )
    (root / "docs" / "plan.json").write_text(
        json.dumps({"project": root.name, "batches": [{"name": "B1", "modules": [{"id": "T-001", "name": "m", "state": "pending"}]}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    return root


def test_tool_exists_and_syntax_ok():
    assert TOOL_PATH.exists(), f"memory-search tool 不存在: {TOOL_PATH}"
    result = subprocess.run([sys.executable, "-m", "py_compile", str(TOOL_PATH)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_memory_search_finds_project_memory_and_records_loaded():
    project = make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(TOOL_PATH), "TypeError bytes str", "--project", project.name, "--record-loaded", "--json"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)["data"]
        paths = [hit["path"] for hit in data["hits"]]
        assert any("typeerror-bytes-str.md" in path for path in paths), f"应命中项目 memory: {paths}"
        assert data["recorded_events"], "--record-loaded 应记录 loaded 事件"
        assert (project / "memory" / "memory_usage.jsonl").exists()
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_start_work_includes_memory_search_hits():
    project = make_project()
    try:
        result = subprocess.run(
            [sys.executable, str(START_WORK), project.name, "--json", "--task", "TypeError bytes str"],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)["data"]
        hits = data.get("memory_search", {}).get("hits") or []
        assert hits, "start-work --task 应包含 memory_search hits"
        assert any("typeerror-bytes-str.md" in hit["path"] for hit in hits)
    finally:
        shutil.rmtree(project, ignore_errors=True)


def test_semantic_search_uses_local_vector_db_without_api():
    project = make_project()
    vector_db = Path(tempfile.mkdtemp(prefix="memory_search_vectors_")) / "vectors.sqlite"
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(TOOL_PATH),
                "SPEC dtype TypeError",
                "--project",
                project.name,
                "--mode",
                "hybrid",
                "--embedding-provider",
                "local",
                "--vector-db",
                str(vector_db),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(FRAMEWORK_ROOT),
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)["data"]
        assert data["mode"] == "hybrid"
        assert data["semantic"]["enabled"] is True
        assert data["semantic"]["embedding_model"] == "text-embedding-v4"
        assert data["semantic"]["dimensions"] == 1024
        assert data["semantic_hits"], "local semantic path 应产生 semantic hits"
        assert vector_db.exists(), "semantic search 应写入 SQLite vector db"
    finally:
        shutil.rmtree(project, ignore_errors=True)
        shutil.rmtree(vector_db.parent, ignore_errors=True)


def test_context_probe_skill_references_memory_search():
    content = CONTEXT_PROBE_SKILL.read_text(encoding="utf-8")
    assert ".claude/tools/memory-search/run.py" in content
    assert "--record-loaded" in content
    assert "--mode hybrid" in content


def test_env_example_documents_bailian_semantic_search_config():
    content = ENV_EXAMPLE.read_text(encoding="utf-8")
    assert "Non-secret defaults live in config.yaml" in content
    assert "DASHSCOPE_API_KEY=" in content
    assert "DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1" in content


def test_config_yaml_documents_supported_model_config():
    content = CONFIG_YAML.read_text(encoding="utf-8")
    assert "providers:" in content
    assert "bailian:" in content
    assert "api_key_env: DASHSCOPE_API_KEY" in content
    assert "models:" in content
    assert "memory_search:" in content
    assert "embedding_model: text-embedding-v4" in content
    assert "skill_tests:" in content
    assert "model: qwen-flash" in content


if __name__ == "__main__":
    tests = [
        test_tool_exists_and_syntax_ok,
        test_memory_search_finds_project_memory_and_records_loaded,
        test_start_work_includes_memory_search_hits,
        test_semantic_search_uses_local_vector_db_without_api,
        test_context_probe_skill_references_memory_search,
        test_env_example_documents_bailian_semantic_search_config,
        test_config_yaml_documents_supported_model_config,
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
    sys.exit(failed)
