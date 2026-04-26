#!/usr/bin/env python3
from __future__ import annotations

"""Layer2/Layer3 model behavior validation readiness and dry-run helper."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)
CASES_FILE = ROOT / "skill-tests" / "generated" / "cases.json"


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _load_cases(skill: str | None = None) -> dict[str, Any]:
    if not CASES_FILE.exists():
        return {}
    data = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    skills = data.get("skills", {})
    if skill:
        skills = {name: value for name, value in skills.items() if skill in name}
    return skills


def _counts(skills: dict[str, Any]) -> dict[str, int]:
    layer2 = sum(len(skill.get("layer2", [])) for skill in skills.values())
    layer3 = sum(len(skill.get("layer3", [])) for skill in skills.values())
    return {"skills": len(skills), "layer2_cases": layer2, "layer3_cases": layer3, "total_cases": layer2 + layer3}


def _api_config() -> dict[str, Any]:
    _load_dotenv()
    framework_config = workflow_cli_common.load_framework_config(ROOT)
    skill_config = workflow_cli_common.get_config_value(framework_config, "models.skill_tests", {}) or {}
    provider = os.environ.get("SKILL_TEST_MODEL_PROVIDER", skill_config.get("provider", "bailian")).strip().lower()
    if provider == "anthropic":
        provider_config = workflow_cli_common.get_config_value(framework_config, "providers.anthropic", {}) or {}
        primary_key_env = provider_config.get("api_key_env", "ANTHROPIC_AUTH_TOKEN")
        fallback_key_env = provider_config.get("fallback_api_key_env", "ANTHROPIC_API_KEY")
        key = os.environ.get(primary_key_env) or os.environ.get(fallback_key_env) or ""
        base_url = os.environ.get("ANTHROPIC_BASE_URL", provider_config.get("base_url", "https://api.anthropic.com"))
        model = os.environ.get("SKILL_TEST_MODEL", skill_config.get("model", "claude-sonnet-4-6"))
        key_env = f"{primary_key_env}|{fallback_key_env}"
    else:
        provider_config = workflow_cli_common.get_config_value(framework_config, "providers.bailian", {}) or {}
        key_env = provider_config.get("api_key_env", "DASHSCOPE_API_KEY")
        key = os.environ.get(key_env) or ""
        base_url = os.environ.get("DASHSCOPE_API_BASE", provider_config.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1"))
        model = os.environ.get("SKILL_TEST_MODEL") or os.environ.get("MEMORY_SEARCH_LLM_MODEL") or skill_config.get("model") or "qwen-flash"
    return {
        "provider": provider,
        "base_url": base_url,
        "api_key_present": bool(key),
        "api_key_env": key_env,
        "model": model,
        "live_command": "python3 skill-tests/run_all.py --layer 3",
    }


def readiness(skill: str | None = None) -> dict[str, Any]:
    skills = _load_cases(skill)
    counts = _counts(skills)
    issues = []
    if not CASES_FILE.exists():
        issues.append({"level": "high", "message": "skill-tests/generated/cases.json is missing"})
    if counts["total_cases"] == 0:
        issues.append({"level": "high", "message": "no Layer2/Layer3 cases found"})
    api = _api_config()
    if not api["api_key_present"]:
        issues.append({"level": "medium", "message": f"{api['api_key_env']} is not set; live behavior tests cannot run"})
    status = "ok"
    if any(issue["level"] == "high" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"
    return {
        "status": status,
        "cases_file": workflow_cli_common.rel_path(CASES_FILE, ROOT),
        "counts": counts,
        "api": api,
        "issues": issues,
    }


def dry_run(skill: str | None = None, layer: int = 3, max_cases: int = 20) -> dict[str, Any]:
    skills = _load_cases(skill)
    selected = []
    for skill_id, skill_data in skills.items():
        if layer >= 2:
            for case in skill_data.get("layer2", []):
                selected.append({
                    "layer": 2,
                    "skill": skill_id,
                    "name": case.get("name", ""),
                    "prompt_preview": str(case.get("scenario", ""))[:180],
                    "criterion": case.get("criterion", ""),
                })
        if layer >= 3:
            for case in skill_data.get("layer3", []):
                selected.append({
                    "layer": 3,
                    "skill": skill_id,
                    "name": case.get("name", ""),
                    "prompt_preview": str(case.get("prompt", ""))[:180],
                    "criterion": case.get("criterion", ""),
                })
    counts = _counts(skills)
    return {
        "status": "ok" if counts["total_cases"] else "error",
        "mode": "dry_run_no_api",
        "counts": counts,
        "selected_count": len(selected),
        "sample_cases": selected[:max(0, max_cases)],
        "next_live_command": "python3 skill-tests/run_all.py --layer 3" + (f" --skill {skill}" if skill else ""),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD Layer2/Layer3 model behavior validation helper")
    parser.add_argument("command", choices=["readiness", "dry-run"])
    parser.add_argument("--skill", default=None)
    parser.add_argument("--layer", type=int, default=3, choices=[2, 3])
    parser.add_argument("--max-cases", type=int, default=20)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    data = readiness(args.skill) if args.command == "readiness" else dry_run(args.skill, args.layer, args.max_cases)
    status = data.get("status", "ok")
    payload = {"status": status, "message": f"model behavior {args.command}: {status}", "data": data}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
        if args.command == "readiness":
            for issue in data.get("issues", []):
                print(f"- [{issue['level']}] {issue['message']}")
        else:
            print(f"cases: {data['selected_count']}")
    return 1 if status == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
