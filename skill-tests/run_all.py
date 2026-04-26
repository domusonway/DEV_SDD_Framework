#!/usr/bin/env python3
"""
DEV SDD Framework Skill Tests
用法：
  python3 skill-tests/run_all.py              # Layer 1（文档结构，无 API）
  python3 skill-tests/run_all.py --layer 2    # + 触发测试
  python3 skill-tests/run_all.py --layer 3    # 全量（行为测试）
  python3 skill-tests/run_all.py --layer 3 --skill tdd-cycle   # 只测指定 skill
  python3 skill-tests/run_all.py --layer 3 --regenerate        # 先增量生成再测

Layer 2/3 的测试用例从 skill-tests/generated/cases.json 读取。
cases.json 由 generate_cases.py 生成，可提交到 git，无需手动维护。
"""

import sys
import os
import json
import time
import argparse
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

FRAMEWORK_ROOT = Path(__file__).parent.parent
CASES_DIR = Path(__file__).parent / "cases"
GENERATED_DIR = Path(__file__).parent / "generated"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

CASES_FILE = GENERATED_DIR / "cases.json"

def load_dotenv():
    path = FRAMEWORK_ROOT / ".env"
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


load_dotenv()

COMMON_TOOL = FRAMEWORK_ROOT / ".claude" / "tools" / "workflow_cli_common.py"
COMMON_SPEC = None
workflow_cli_common = None
if COMMON_TOOL.exists():
    import importlib.util
    COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", COMMON_TOOL)
    assert COMMON_SPEC and COMMON_SPEC.loader
    workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
    COMMON_SPEC.loader.exec_module(workflow_cli_common)

FRAMEWORK_CONFIG = workflow_cli_common.load_framework_config(FRAMEWORK_ROOT) if workflow_cli_common else {}
SKILL_TEST_CONFIG = workflow_cli_common.get_config_value(FRAMEWORK_CONFIG, "models.skill_tests", {}) if workflow_cli_common else {}
BAILIAN_CONFIG = workflow_cli_common.get_config_value(FRAMEWORK_CONFIG, "providers.bailian", {}) if workflow_cli_common else {}
ANTHROPIC_CONFIG = workflow_cli_common.get_config_value(FRAMEWORK_CONFIG, "providers.anthropic", {}) if workflow_cli_common else {}

MODEL_PROVIDER = os.environ.get("SKILL_TEST_MODEL_PROVIDER", SKILL_TEST_CONFIG.get("provider", "bailian")).strip().lower()
BAILIAN_BASE_URL = os.environ.get("DASHSCOPE_API_BASE", BAILIAN_CONFIG.get("base_url", "https://dashscope.aliyuncs.com/compatible-mode/v1")).rstrip("/")
BAILIAN_API_KEY = os.environ.get(BAILIAN_CONFIG.get("api_key_env", "DASHSCOPE_API_KEY"), "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", ANTHROPIC_CONFIG.get("base_url", "https://api.anthropic.com")).rstrip("/")
ANTHROPIC_API_KEY = os.environ.get(ANTHROPIC_CONFIG.get("api_key_env", "ANTHROPIC_AUTH_TOKEN")) or os.environ.get(ANTHROPIC_CONFIG.get("fallback_api_key_env", "ANTHROPIC_API_KEY"), "")
MODEL = os.environ.get("SKILL_TEST_MODEL") or ("claude-sonnet-4-6" if MODEL_PROVIDER == "anthropic" else os.environ.get("MEMORY_SEARCH_LLM_MODEL") or SKILL_TEST_CONFIG.get("model") or "qwen-flash")

# ── Layer 1 测试文件列表（v3.1 更新）────────────────────────────────────────
LAYER1_FILES = [
    # 原有 skills
    "test_complexity_assess.py",
    "test_context_probe_tool.py",
    "test_prompt_policy.py",
    "test_tdd_cycle.py",
    "test_diagnose_bug.py",
    "test_memory_update.py",
    "test_doc_template_tool.py",
    "test_memory_conflicts_tool.py",
    "test_memory_search_tool.py",
    "test_memory_usage_tool.py",
    "test_validate_output.py",
    "test_framework_health_tool.py",
    "test_review_cockpit_tool.py",
    "test_dev_sdd_dashboard_tool.py",
    "test_model_behavior_tool.py",
    # 原有 hooks
    "test_hook_network_guard.py",
    "test_hook_post_green.py",
    "test_hook_stuck_detector.py",
    # v3.0 新增 skills
    "test_observe_verify.py",
    "test_sub_agent_isolation.py",
    # v3.0 新增 hooks/tools
    "test_context_budget.py",
    "test_plan_tracker_completion_guard.py",
    # v3.1 新增：Meta-Skill Loop 全组件测试
    "test_meta_skill_loop.py",
    "test_start_work_tool.py",
    "test_redefine_tool.py",
    "test_update_todo_tool.py",
    "test_fix_tool.py",
    "test_workflow_cli_contracts.py",
    "test_workflow_drift_guards.py",
    "test_workflow_migration_docs.py",
]

ROUTING_SYSTEM = """
你是一个遵循 DEV SDD 框架的 AI 编程助手。

框架的"按需加载地图"如下：

| 当前任务 | 读取路径 |
|---------|---------|
| 收到开发任务 | .claude/skills/complexity-assess/SKILL.md |
| TDD 实现阶段 | .claude/skills/tdd-cycle/SKILL.md |
| VALIDATE 阶段（每模块）| .claude/skills/observe-verify/SKILL.md |
| 出现 Bug / RED > 2次 | .claude/skills/diagnose-bug/SKILL.md |
| 所有测试 GREEN 后 | .claude/skills/validate-output/SKILL.md |
| 项目完成后 | .claude/skills/memory-update/SKILL.md |
| H 模式多模块规划 | .claude/agents/planner.md |
| H 模式 sub-agent 隔离 | .claude/skills/sub-agent-isolation/SKILL.md |
| 写任何网络代码后 | .claude/hooks/network-guard/HOOK.md（立即执行）|
| RED 超过 2 次 | .claude/hooks/stuck-detector/HOOK.md（立即执行）|
| 所有测试 GREEN | .claude/hooks/post-green/HOOK.md（立即执行）|
| 每模块 UPDATE-PLAN 后 | .claude/hooks/context-budget/HOOK.md（立即检查）|
| 项目交付后 | .claude/agents/memory-keeper.md（含 Meta-Skill Loop）|
| 审核框架候选 | /project:skill-review |

当我描述一个场景，请告诉我应该读取哪个文件及原因。
""".strip()


def call_bailian_model(user_message, system="", max_tokens=600, retries=2):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user_message})
    payload = {"model": MODEL, "messages": messages, "max_tokens": max_tokens}
    for attempt in range(retries + 1):
        try:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                f"{BAILIAN_BASE_URL}/chat/completions",
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {BAILIAN_API_KEY}",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if attempt < retries and e.code in (429, 500, 502, 503, 504):
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"Bailian API {e.code}: {body[:150]}") from e
        except Exception:
            if attempt < retries:
                time.sleep(3)
                continue
            raise


def call_anthropic_model(user_message, system="", max_tokens=600, retries=2):
    payload = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": user_message}],
    }
    if system:
        payload["system"] = system
    for attempt in range(retries + 1):
        try:
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                f"{ANTHROPIC_BASE_URL}/v1/messages", data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read())
                return result["content"][0]["text"]
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            if attempt < retries and e.code in (429, 529):
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(f"API {e.code}: {body[:150]}") from e
        except Exception as e:
            if attempt < retries:
                time.sleep(3)
                continue
            raise


def call_model(user_message, system="", max_tokens=600, retries=2):
    if MODEL_PROVIDER == "anthropic":
        return call_anthropic_model(user_message, system=system, max_tokens=max_tokens, retries=retries)
    if MODEL_PROVIDER == "bailian":
        return call_bailian_model(user_message, system=system, max_tokens=max_tokens, retries=retries)
    raise RuntimeError(f"unsupported SKILL_TEST_MODEL_PROVIDER: {MODEL_PROVIDER}")


def judge(response, criterion):
    prompt = f"""你是严格的测试评估器。判断【模型响应】是否满足【验证标准】。

【验证标准】
{criterion}

【模型响应】
{response}

仅输出 JSON：{{"passed": true或false, "reason": "一句话原因"}}"""
    result = call_model(prompt, max_tokens=150)
    result_text = result or ""
    try:
        clean = result_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        d = json.loads(clean)
        return bool(d["passed"]), str(d.get("reason", ""))
    except Exception:
        lower = result_text.lower()
        if '"passed": true' in lower or '"passed":true' in lower:
            return True, result_text
        return False, f"无法解析: {result_text[:80]}"


def load_cases(skill_filter=None):
    if not CASES_FILE.exists():
        return {}
    data = json.loads(CASES_FILE.read_text())
    skills = data.get("skills", {})
    if skill_filter:
        skills = {k: v for k, v in skills.items() if skill_filter in k}
    return skills


def run_l1_file(test_file):
    path = CASES_DIR / test_file
    if not path.exists():
        return {"name": test_file, "status": "MISSING", "stdout": "", "stderr": "文件不存在"}
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True, text=True, timeout=30
    )
    return {
        "name": test_file,
        "status": "PASS" if result.returncode == 0 else "FAIL",
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_layer1(skill_filter=None):
    files = LAYER1_FILES
    if skill_filter:
        files = [f for f in files if skill_filter in f]
    print(f"\n{'─'*56}")
    print(f"  Layer 1 · 文档结构测试（无 API）")
    print(f"{'─'*56}")
    results = []
    for f in files:
        try:
            r = run_l1_file(f)
        except subprocess.TimeoutExpired:
            r = {"name": f, "status": "TIMEOUT", "stdout": "", "stderr": "超时"}
        icon = "✅" if r["status"] == "PASS" else ("⚠️" if r["status"] == "MISSING" else "❌")
        name = f.replace("test_", "").replace(".py", "")
        print(f"  {icon} {name:<44} {r['status']}")
        if r["status"] == "FAIL":
            for line in (r["stdout"] + r["stderr"]).strip().splitlines():
                if line.strip():
                    print(f"      {line}")
        results.append({"layer": 1, **r})
    return results


def run_layer2(cases):
    print(f"\n{'─'*56}")
    print(f"  Layer 2 · 触发测试（Skill 选择正确性）")
    print(f"{'─'*56}")
    results = []
    for skill_id, skill_data in cases.items():
        for case in skill_data.get("layer2", []):
            name = f"[{skill_id}] {case['name']}"
            try:
                response = call_model(f"场景描述：{case['scenario']}", system=ROUTING_SYSTEM)
                passed, reason = judge(response, case["criterion"])
                status = "PASS" if passed else "FAIL"
                print(f"  {'✅' if passed else '❌'} {name}")
                if not passed:
                    print(f"       原因: {reason}")
                results.append({
                    "layer": 2, "skill": skill_id, "name": name,
                    "status": status, "reason": reason,
                })
            except Exception as e:
                print(f"  ⚠️  {name} [ERROR: {str(e)[:60]}]")
                results.append({
                    "layer": 2, "skill": skill_id, "name": name,
                    "status": "ERROR", "reason": str(e),
                })
    return results


def run_layer3(cases):
    print(f"\n{'─'*56}")
    print(f"  Layer 3 · 行为测试（约束遵守验证）")
    print(f"{'─'*56}")
    results = []
    for skill_id, skill_data in cases.items():
        l3_cases = skill_data.get("layer3", [])
        if not l3_cases:
            continue
        print(f"\n  ── {skill_id}")
        for case in l3_cases:
            name = case["name"]
            system = case.get("system_content", "")
            try:
                response = call_model(case["prompt"], system=system)
                passed, reason = judge(response, case["criterion"])
                status = "PASS" if passed else "FAIL"
                rule_src = case.get("rule_source", "")
                print(f"  {'✅' if passed else '❌'} {name}")
                if rule_src:
                    print(f"       规则来源: 「{rule_src}」")
                if not passed:
                    print(f"       原因: {reason}")
                results.append({
                    "layer": 3, "skill": skill_id, "name": name,
                    "status": status, "reason": reason, "rule_source": rule_src,
                })
            except Exception as e:
                print(f"  ⚠️  {name} [ERROR: {str(e)[:60]}]")
                results.append({
                    "layer": 3, "skill": skill_id, "name": name,
                    "status": "ERROR", "reason": str(e),
                })
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--skill", type=str, default=None)
    parser.add_argument("--regenerate", action="store_true",
                        help="执行前先增量更新 cases.json")
    args = parser.parse_args()

    if args.regenerate and args.layer >= 2:
        print("⚙  增量更新 cases.json ...")
        cmd = [sys.executable, str(Path(__file__).parent / "generate_cases.py"), "--diff"]
        if args.skill:
            cmd += ["--skill", args.skill]
        subprocess.run(cmd, check=False)
        print()

    print("=" * 56)
    print("  DEV SDD Framework — Skill Tests v3.1")
    print(f"  Layer: {args.layer}  |  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.layer >= 2:
        print(f"  Model: {MODEL_PROVIDER}/{MODEL}")
    if args.skill:
        print(f"  Filter: {args.skill}")
    print("=" * 56)

    all_results = []
    all_results += run_layer1(args.skill)

    if args.layer >= 2:
        cases = load_cases(args.skill)
        if not cases:
            print(f"\n  ⚠️  未找到 cases.json，请先执行:")
            print(f"     python3 skill-tests/generate_cases.py")
        else:
            all_results += run_layer2(cases)

    if args.layer >= 3:
        cases = load_cases(args.skill)
        if cases:
            all_results += run_layer3(cases)

    passed = sum(1 for r in all_results if r["status"] == "PASS")
    total = len(all_results)
    failed_items = [r for r in all_results if r["status"] not in ("PASS",)]

    print(f"\n{'='*56}")
    print(f"  总结: {passed}/{total} 通过  {'✅' if passed == total else '❌'}")
    if failed_items:
        print(f"\n  失败项:")
        for r in failed_items:
            print(f"    [L{r['layer']}] {r['name']} [{r['status']}]")

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = REPORTS_DIR / f"report_L{args.layer}_{ts}.json"
    report = {
        "timestamp": datetime.now().isoformat(),
        "framework_version": "v3.1",
        "layer": args.layer,
        "skill_filter": args.skill,
        "passed": passed,
        "total": total,
        "pass_rate": f"{passed/total*100:.1f}%" if total else "0%",
        "results": all_results,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n  报告: {report_path}")
    print("=" * 56)
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
