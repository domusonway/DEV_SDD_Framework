#!/usr/bin/env python3
"""
init/run.py

用途:
  /DEV_SDD:init 的执行辅助 CLI。
  从项目 `docs/CONTEXT.md` 推导初始化文档，生成结构化 `plan.json` 及其派生视图，
  并在覆盖现有用户可见文档前返回结构化确认信息。

用法:
  python3 .claude/tools/init/run.py [project-name-or-path] [--json] [--dry-run]
  python3 .claude/tools/init/run.py [project-name-or-path] --confirm-overwrite <token>

示例:
  python3 .claude/tools/init/run.py structured-light-stereo --json --dry-run
  python3 .claude/tools/init/run.py projects/demo-project --json
  python3 .claude/tools/init/run.py projects/demo-project --confirm-overwrite abc123def456
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)


STATUS_OK = "ok"
STATUS_WARNING = "warning"
STATUS_ERROR = "error"


def out(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    status_val = str(payload.get("status") or "")
    icon = {STATUS_OK: "✅", STATUS_WARNING: "⚠️", STATUS_ERROR: "❌"}.get(status_val, "ℹ️")
    print(f"{icon}  {payload.get('message', '')}")
    data = payload.get("data") or {}
    print("[INIT]")
    print(f"项目: {data.get('project', 'unknown')}")
    print(f"来源: {data.get('source_context', 'docs/CONTEXT.md')}")
    print(f"dry-run: {'yes' if data.get('dry_run') else 'no'}")
    print(f"计划文件: {data.get('plan_source', 'docs/plan.json')}")
    print(f"待写入: {', '.join(item['path'] for item in data.get('writes', [])) or '无'}")
    confirmation = data.get("confirmation") or {}
    if confirmation.get("required"):
        print(f"确认: required ({confirmation.get('token', '')})")
    print("[/INIT]")


def find_framework_root() -> Path:
    return workflow_cli_common.find_framework_root(__file__)


ROOT = find_framework_root()


def safe_read_text(path: Path) -> str:
    return workflow_cli_common.safe_read_text(path)


def parse_project_from_text(content: str) -> str | None:
    if not content:
        return None
    match = re.search(r"^PROJECT:\s*(.+)$", content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def detect_active_project(root: Path) -> str | None:
    return workflow_cli_common.detect_active_project(root)


def rel_path(path: Path, base: Path) -> str:
    return workflow_cli_common.rel_path(path, base)


def resolve_target(target_arg: str | None) -> tuple[Path | None, str | None]:
    return workflow_cli_common.resolve_target_project(target_arg, ROOT)


def extract_section(content: str, heading: str) -> str:
    pattern = re.compile(rf"^##\s+{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(content)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"^##\s+.+$", content[start:], re.MULTILINE)
    end = start + next_match.start() if next_match else len(content)
    return content[start:end].strip()


def first_nonempty_paragraph(section: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section) if part.strip()]
    return paragraphs[0] if paragraphs else ""


def parse_title(content: str, fallback: str) -> str:
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            raw = stripped[2:].strip()
            return raw.split("·", 1)[0].strip() or fallback
    return fallback


def parse_tech_stack(content: str) -> dict[str, str]:
    section = extract_section(content, "技术栈") or extract_section(content, "技术栈约定")
    data: dict[str, str] = {}
    for line in section.splitlines():
        match = re.match(r"^-\s*([^:：]+)[:：]\s*(.+)$", line.strip())
        if match:
            data[match.group(1).strip()] = match.group(2).strip()
    return data


def parse_deps(raw: str) -> list[str]:
    text = raw.strip()
    if not text or text in {"无", "None", "none", "-"}:
        return []
    parts = [item.strip(" `") for item in re.split(r"[、,，/]", text) if item.strip()]
    return [part for part in parts if part and part not in {"无", "None", "none"}]


def parse_directory_tree_paths(content: str) -> list[str]:
    paths: list[str] = []
    in_block = False
    stack: list[str] = []

    for raw_line in content.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("```"):
            in_block = not in_block
            if not in_block:
                stack = []
            continue
        if not in_block or not stripped:
            continue
        marker_match = re.match(r"^(?P<prefix>(?:│   |    )*)(?:├── |└── )(?P<name>.+?)\s*(?:#.*)?$", line)
        if not marker_match:
            continue
        prefix = marker_match.group("prefix")
        name = marker_match.group("name").strip()
        level = len(prefix) // 4
        while len(stack) > level:
            stack.pop()
        is_dir = name.endswith("/")
        clean_name = name.rstrip("/")
        full_path = "/".join(stack + [clean_name])
        paths.append(full_path)
        if is_dir:
            stack.append(clean_name)
    return paths


def infer_impl_path(module_name: str, group: str | None, directory_paths: list[str]) -> str:
    normalized_group = (group or "").strip("/")
    expected_names = [module_name, f"{module_name}.py", f"{module_name}.ts", f"{module_name}.tsx", f"{module_name}.js"]

    prioritized: list[str] = []
    fallback: list[str] = []
    for path in directory_paths:
        tail = path.split("/")[-1]
        if tail not in expected_names:
            continue
        if normalized_group and f"/{normalized_group}/" in f"/{path}/":
            prioritized.append(path)
        else:
            fallback.append(path)

    candidates = prioritized or fallback
    if candidates:
        return candidates[0]
    return f"modules/{normalized_group}/{module_name}".replace("//", "/") if normalized_group else f"modules/{module_name}"


def parse_modules(content: str) -> list[dict[str, Any]]:
    section = extract_section(content, "模块划分")
    if not section:
        return []

    directory_paths = parse_directory_tree_paths(content)

    matches = list(re.finditer(r"^(#{3,6})\s+(.+)$", section, re.MULTILINE))
    modules: list[dict[str, Any]] = []
    heading_stack: list[tuple[int, str]] = []
    for index, match in enumerate(matches):
        level = len(match.group(1))
        name = match.group(2).strip()
        while heading_stack and heading_stack[-1][0] >= level:
            heading_stack.pop()
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        body = section[start:end]
        fields: dict[str, str] = {}
        for line in body.splitlines():
            field_match = re.match(r"^-\s*([^:：]+)[:：]\s*(.+)$", line.strip())
            if field_match:
                fields[field_match.group(1).strip()] = field_match.group(2).strip()
        if not fields:
            heading_stack.append((level, name))
            continue
        group = None
        for _, ancestor_name in reversed(heading_stack):
            cleaned = ancestor_name.strip().strip("/")
            if cleaned:
                group = cleaned
                break
        spec_path = f"modules/{group}/{name}/SPEC.md" if group else f"modules/{name}/SPEC.md"
        impl_path = infer_impl_path(name, group, directory_paths)
        modules.append({
            "name": name,
            "spec_path": spec_path,
            "impl_path": impl_path,
            "responsibility": fields.get("职责", "见 docs/CONTEXT.md 模块说明"),
            "input": fields.get("输入", "见 docs/CONTEXT.md 模块说明"),
            "output": fields.get("输出", "见 docs/CONTEXT.md 模块说明"),
            "deps": parse_deps(fields.get("依赖", "无")),
        })
        heading_stack.append((level, name))
    return modules


def determine_mode(module_count: int) -> tuple[str, str]:
    if module_count <= 1:
        return "L", "L 轻量"
    if module_count <= 5:
        return "M", "M 标准"
    return "H", "H 完整"


def build_batches(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    remaining = [dict(module) for module in modules]
    completed: set[str] = set()
    batches: list[dict[str, Any]] = []
    batch_no = 1

    while remaining:
        ready = [module for module in remaining if set(module.get("deps", [])) <= completed]
        if not ready:
            ready = list(remaining)
        batch_modules = []
        for module in ready:
            batch_modules.append({
                "name": module["name"],
                "spec_path": module.get("spec_path") or f"modules/{module['name']}/SPEC.md",
                "impl_path": module.get("impl_path") or f"modules/{module['name']}",
                "path": module.get("impl_path") or f"modules/{module['name']}",
                "complexity": "M",
                "risk": "" if set(module.get("deps", [])) <= completed else "依赖关系待整理",
                "deps": module.get("deps", []),
                "state": "pending",
                "completed_at": None,
            })
            completed.add(module["name"])

        batches.append({
            "name": f"批次 {batch_no}",
            "description": "无依赖，可并行实现" if batch_no == 1 else f"依赖前序批次输出接口（Batch {batch_no - 1}）",
            "modules": batch_modules,
        })
        remaining = [module for module in remaining if module not in ready]
        batch_no += 1
    return batches


def build_plan(project_name: str, modules: list[dict[str, Any]]) -> dict[str, Any]:
    today = date.today().isoformat()
    batches = build_batches(modules)
    return {
        "project": project_name,
        "created": today,
        "batches": batches,
        "milestones": [
            {
                "name": "M1: 初始化完成",
                "condition": "首批模块进入 TDD",
                "target_date": today,
            },
            {
                "name": "M2: 计划稳定",
                "condition": "所有批次已确认并可执行",
                "target_date": today,
            },
            {
                "name": "M3: 交付就绪",
                "condition": "validate-output 通过",
                "target_date": today,
            },
        ],
    }


def render_plan_markdown(plan: dict[str, Any]) -> str:
    status_icon = {"pending": "- [ ]", "completed": "- [x]", "skipped": "- [~]", "in_progress": "- [>]"}
    lines = [
        f"# {plan.get('project', 'unknown')} · 实现计划",
        "",
        "> ⚠️ 此文件是 `docs/plan.json` 的派生/生成视图，用于人类阅读；执行状态以 `plan.json` 为准，请勿手动编辑。",
        "",
        "## 实现批次",
        "",
    ]
    for batch in plan.get("batches", []):
        lines.append(f"### {batch['name']}")
        if batch.get("description"):
            lines.append(f"_{batch['description']}_")
        lines.append("")
        for module in batch.get("modules", []):
            deps = module.get("deps", [])
            dep_suffix = f" — 依赖: {', '.join(deps)}" if deps else ""
            lines.append(f"{status_icon.get(module.get('state', 'pending'), '- [ ]')} **{module['name']}** — 估算: {module.get('complexity', 'M')}{dep_suffix}")
        lines.append("")

    all_modules = [module for batch in plan.get("batches", []) for module in batch.get("modules", [])]
    lines.extend([
        "---",
        f"**进度: 0/{len(all_modules)}**",
        "",
        "## 里程碑",
        "",
        "| 里程碑 | 条件 | 目标日期 |",
        "|------|------|---------|",
    ])
    for milestone in plan.get("milestones", []):
        lines.append(f"| {milestone.get('name', '')} | {milestone.get('condition', '')} | {milestone.get('target_date', '')} |")
    return "\n".join(lines) + "\n"


def render_todo(project_name: str, modules: list[dict[str, Any]]) -> str:
    current = modules[0]["name"] if modules else "根据 plan.json 定义首个模块"
    upcoming = [module["name"] for module in modules[1:3]] or ["补齐模块 SPEC", "运行 complexity-assess"]
    lines = [
        f"# {project_name} · 任务跟踪",
        "",
        "> ⚠️ 执行状态以 `docs/plan.json` 为准；此文件仅记录项目级备注、审计和人工跟进。",
        "",
        "---",
        "",
        "## 进行中",
        f"- [ ] {current}",
        "",
        "---",
        "",
        "## 待办",
    ]
    for item in upcoming:
        lines.append(f"- [ ] {item}")
    lines.extend([
        "",
        "---",
        "",
        "## 已完成",
        "<!-- 完成后移入此区 -->",
        "",
        "---",
        "",
        "## STUCK 记录",
        "<!-- stuck-detector 触发时在此记录 -->",
        "",
        "---",
        "",
        "## 已知问题",
        "<!-- 发现但暂不修复的问题 -->",
        "",
    ])
    return "\n".join(lines)


def render_claude(project_name: str, goal: str, background: str, modules: list[dict[str, Any]], tech_stack: dict[str, str]) -> str:
    complexity, mode = determine_mode(len(modules))
    created = date.today().isoformat()
    description = goal or background or "未在 docs/CONTEXT.md 提供项目描述"
    language = tech_stack.get("语言", "未在 docs/CONTEXT.md 声明")
    test_framework = tech_stack.get("测试框架", "未在 docs/CONTEXT.md 声明")
    dependencies = tech_stack.get("主要依赖", "未在 docs/CONTEXT.md 声明")

    lines = [
        f"# {project_name} · 项目上下文入口",
        f"> 创建日期: {created} | 复杂度: {complexity} | 工作模式: {mode}",
        "",
        "---",
        "",
        "## 项目简介",
        description,
        "",
        "---",
        "",
        "## 技术栈",
        f"- 语言: {language}",
        f"- 测试框架: {test_framework}",
        f"- 主要依赖: {dependencies}",
        "",
        "---",
        "",
        "## 项目特有约束（覆盖框架默认规则时在此声明）",
        "",
        "<!-- INIT 根据 docs/CONTEXT.md 生成此入口；后续约束可在此补充。 -->",
        "",
        "---",
        "",
        "## 模块列表",
        "",
        "| 模块 | 实现路径 | SPEC | 状态 |",
        "|------|----------|------|------|",
    ]
    for module in modules:
        name = module["name"]
        impl_path = str(module.get("impl_path") or f"modules/{name}").rstrip("/")
        spec_path = str(module.get("spec_path") or f"modules/{name}/SPEC.md")
        lines.append(f"| {name} | {impl_path} | [SPEC]({spec_path}) | 🔴 未开始 |")

    if not modules:
        lines.append("| 待定义模块 | modules/<name>/ 或项目实际代码目录 | [SPEC](modules/<name>/SPEC.md) | 🔴 未开始 |")

    lines.extend([
        "",
        "---",
        "",
        "## 按需加载地图（项目级补充）",
        "",
        "| 场景 | 读取路径 |",
        "|------|---------|",
        "| 项目背景 | `docs/CONTEXT.md` |",
        "| 执行计划（权威状态） | `docs/plan.json` |",
        "| 执行计划（只读视图） | `docs/PLAN.md` |",
        "| 当前执行备注 | `docs/TODO.md` |",
        "| 项目记忆 | `memory/INDEX.md` |",
        "| 上次会话 | `memory/sessions/` 最新文件 |",
        "",
        "> 项目执行状态以 `docs/plan.json` 为准；`docs/PLAN.md` 是生成的只读视图，`docs/TODO.md` 仅记录项目级执行备注、临时跟进和审计信息。",
        "",
        "---",
        "",
        "## 验收标准",
        "- `docs/plan.json` 保持为执行真相源",
        "- `docs/PLAN.md` / `docs/TODO.md` 仅作为派生视图或补充记录",
        "- 后续模块开发遵循 SPEC → tests → implementation 的 TDD 流程",
        "",
    ])
    return "\n".join(lines)


def render_readme(project_name: str, goal: str, background: str, modules: list[dict[str, Any]]) -> str:
    lines = [
        f"# {project_name}",
        "",
        "## 项目目标",
        goal or "未在 docs/CONTEXT.md 提供项目目标",
        "",
        "## 背景",
        background or "未在 docs/CONTEXT.md 提供背景说明",
        "",
        "## 初始化约定",
        "- `docs/CONTEXT.md` 是 INIT 的输入来源",
        "- `docs/plan.json` 是执行状态真相源",
        "- `docs/PLAN.md` 与 `docs/TODO.md` 为派生/补充文档",
        "- `modules/` 默认承载规格文档；实现代码路径由 `plan.json.impl_path` 显式声明",
        "",
        "## 模块概览",
    ]
    if modules:
        for module in modules:
            lines.append(f"- **{module['name']}**: {module.get('responsibility', '见 docs/CONTEXT.md 模块说明')}")
    else:
        lines.append("- 待在 docs/CONTEXT.md 中补充模块定义")
    lines.append("")
    return "\n".join(lines)


def infer_python_version(tech_stack: dict[str, str]) -> str:
    language = tech_stack.get("语言", "")
    match = re.search(r"Python\s+([0-9]+(?:\.[0-9]+)?)", language, re.IGNORECASE)
    if match:
        return match.group(1)
    return "3.11"


def slugify_env_name(project_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", project_name.lower()).strip("-")
    return slug or "dev-sdd-project"


def render_env_readme(project_name: str, python_version: str, env_name: str) -> str:
    """Generate env/README.md content."""
    lines = [
        f"# {project_name} - 运行环境说明",
        "",
        "本目录仅面向 Ubuntu 开发环境，使用 conda 管理项目依赖并提供一键进入脚本。",
        "",
        "## 环境初始化",
        "",
        f"1. 确保 Ubuntu 已安装 conda，默认环境名为 `{env_name}`：",
        "   ```bash",
        "   conda --version",
        "   ```",
        "",
        "2. 一键创建并进入项目环境：",
        "   ```bash",
        "   bash env/start.sh",
        "   ```",
        "",
        "   首次执行会自动创建 conda 环境、安装 pip 依赖并进入项目根目录。",
        "",
        f"3. 手动管理环境（可选，Python {python_version}）：",
        "   ```bash",
        "   conda env create -f env/environment.yml",
        f"   conda activate {env_name}",
        "   pip install -r env/requirements.txt",
        "   ```",
        "",
        "## 依赖管理",
        "",
        "- conda 基础环境定义放在 `env/environment.yml` 中",
        "- Python 包依赖放在 `env/requirements.txt` 中",
        "- 更新 pip 依赖后可使用 `pip freeze > env/requirements.txt` 刷新锁定文件",
        "",
        "## 一键脚本说明",
        "",
        "- `env/start.sh` 仅考虑 Ubuntu shell（bash）",
        "- 环境不存在时自动创建，存在时直接激活",
        "- 脚本会进入项目根目录并打开交互 shell",
        "",
        "> ⚠️ 请勿直接在系统 Python 环境中安装项目依赖，以免造成版本冲突和环境污染。",
    ]
    return "\n".join(lines)


def render_env_requirements() -> str:
    """Generate env/requirements.txt content."""
    lines = [
        "# DEV SDD Framework 项目依赖",
        "# 根据实际项目需求添加具体依赖包",
        "",
        "PyYAML>=6.0",
        "pytest>=8.0",
        "",
        "# 其他依赖请根据 SPEC.md 与技术栈继续补充",
    ]
    return "\n".join(lines)


def render_env_environment_yml(env_name: str, python_version: str) -> str:
    lines = [
        f"name: {env_name}",
        "channels:",
        "  - conda-forge",
        "  - defaults",
        "dependencies:",
        f"  - python={python_version}",
        "  - pip",
        "  - pip:",
        "      - -r requirements.txt",
        "",
    ]
    return "\n".join(lines)


def render_env_start_script(env_name: str) -> str:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "SCRIPT_DIR=\"$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" && pwd)\"",
        "PROJECT_ROOT=\"$(cd \"${SCRIPT_DIR}/..\" && pwd)\"",
        f"ENV_NAME=\"${{DEV_SDD_CONDA_ENV:-{env_name}}}\"",
        "",
        "if ! command -v conda >/dev/null 2>&1; then",
        "  echo \"[env/start.sh] 未检测到 conda，请先在 Ubuntu 上安装 Miniconda/Anaconda\" >&2",
        "  exit 1",
        "fi",
        "",
        "CONDA_BASE=\"$(conda info --base)\"",
        "source \"${CONDA_BASE}/etc/profile.d/conda.sh\"",
        "",
        "if ! conda env list | awk '{print $1}' | grep -Fxq \"${ENV_NAME}\"; then",
        "  echo \"[env/start.sh] 创建 conda 环境: ${ENV_NAME}\"",
        "  conda env create -f \"${SCRIPT_DIR}/environment.yml\" -n \"${ENV_NAME}\"",
        "fi",
        "",
        "conda activate \"${ENV_NAME}\"",
        "cd \"${PROJECT_ROOT}\"",
        "echo \"[env/start.sh] 已进入 ${ENV_NAME} @ ${PROJECT_ROOT}\"",
        "exec \"${SHELL:-/bin/bash}\" -i",
        "",
    ]
    return "\n".join(lines)


def diff_preview(old: str, new: str, fromfile: str, tofile: str, limit: int = 60) -> list[str]:
    lines = list(difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=fromfile,
        tofile=tofile,
        lineterm="",
    ))
    return lines[:limit]


def build_confirmation_token(target_root: Path, conflicts: list[dict[str, Any]]) -> str:
    joined = "|".join(sorted(conflict["path"] for conflict in conflicts))
    seed = f"{target_root.resolve()}|{joined}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:12]


@dataclass
class InitSpec:
    project_name: str
    goal: str
    background: str
    tech_stack: dict[str, str]
    modules: list[dict[str, Any]]
    plan: dict[str, Any]
    files: dict[str, str]


def build_init_spec(target_root: Path) -> InitSpec:
    context_path = target_root / "docs" / "CONTEXT.md"
    content = safe_read_text(context_path)
    if not content:
        raise FileNotFoundError(f"缺少初始化来源文档: {context_path}")

    project_name = parse_title(content, target_root.name)
    goal = first_nonempty_paragraph(extract_section(content, "项目目标"))
    background = first_nonempty_paragraph(extract_section(content, "背景"))
    tech_stack = parse_tech_stack(content)
    python_version = infer_python_version(tech_stack)
    env_name = slugify_env_name(project_name)
    modules = parse_modules(content)
    plan = build_plan(project_name, modules)
    workflow_cli_common.ensure_plan_stable_ids(plan)
    managed_todo = workflow_cli_common.render_managed_todo(project_name, workflow_cli_common.plan_tasks(plan))
    files = {
        "CLAUDE.md": render_claude(project_name, goal, background, modules, tech_stack),
        "AGENTS.md": "./CLAUDE.md\n",
        "README.md": render_readme(project_name, goal, background, modules),
        "docs/plan.json": json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
        "docs/PLAN.md": render_plan_markdown(plan),
        "docs/TODO.md": managed_todo,
        "env/README.md": render_env_readme(project_name, python_version, env_name),
        "env/requirements.txt": render_env_requirements(),
        "env/environment.yml": render_env_environment_yml(env_name, python_version),
        "env/start.sh": render_env_start_script(env_name),
    }
    return InitSpec(
        project_name=project_name,
        goal=goal,
        background=background,
        tech_stack=tech_stack,
        modules=modules,
        plan=plan,
        files=files,
    )


def analyze_writes(target_root: Path, files: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    writes: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for rel, content in files.items():
        target = target_root / rel
        exists = target.exists()
        current = safe_read_text(target) if exists else ""
        action = "create"
        if exists and current == content:
            action = "maintain"
        elif exists:
            action = "overwrite"
            conflicts.append({
                "path": rel,
                "reason": "existing_content_differs",
                "diff_preview": diff_preview(current, content, f"current/{rel}", f"generated/{rel}"),
            })
        writes.append({"path": rel, "action": action})
    return writes, conflicts


def write_files(target_root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = target_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        if rel == "env/start.sh":
            path.chmod(path.stat().st_mode | 0o111)


def run(target_arg: str | None, dry_run: bool, confirm_overwrite: str | None) -> dict[str, Any]:
    target_root, target_label = resolve_target(target_arg)
    if target_root is None:
        return {
            "status": STATUS_WARNING,
            "message": "未检测到激活项目，也未提供目标路径，无法执行 INIT",
            "data": {
                "project": None,
                "next_action": "传入项目路径，或先执行 /project:switch <name>",
                "dry_run": dry_run,
            },
        }

    if not target_root.exists():
        return {
            "status": STATUS_ERROR,
            "message": f"目标项目目录不存在：{target_root}",
            "data": {
                "project": target_label,
                "project_root": str(target_root),
                "dry_run": dry_run,
                "next_action": "先创建项目目录，并确保其中包含 docs/CONTEXT.md",
            },
        }

    try:
        spec = build_init_spec(target_root)
    except FileNotFoundError as exc:
        return {
            "status": STATUS_ERROR,
            "message": str(exc),
            "data": {
                "project": target_label,
                "project_root": rel_path(target_root, ROOT),
                "dry_run": dry_run,
                "next_action": "补齐项目 docs/CONTEXT.md 后重新运行 INIT",
            },
        }

    writes, conflicts = analyze_writes(target_root, spec.files)
    data: dict[str, Any] = {
        "project": spec.project_name,
        "project_root": rel_path(target_root, ROOT),
        "source_context": rel_path(target_root / "docs" / "CONTEXT.md", ROOT),
        "plan_source": "docs/plan.json",
        "dry_run": dry_run,
        "writes": writes,
        "module_count": len(spec.modules),
        "modules": [module["name"] for module in spec.modules],
    }

    if conflicts:
        token = build_confirmation_token(target_root, conflicts)
        confirmation = {
            "required": True,
            "token": token,
            "conflicts": conflicts,
            "diff_preview": [line for conflict in conflicts for line in conflict["diff_preview"]][:120],
            "next_action": f"使用 --confirm-overwrite {token} 重新执行 INIT",
        }
        data["confirmation"] = confirmation
        if confirm_overwrite != token:
            return {
                "status": STATUS_WARNING,
                "message": "检测到现有初始化目标与生成内容冲突，需确认后才能覆盖",
                "data": data,
            }

    if not dry_run:
        write_files(target_root, spec.files)

    return {
        "status": STATUS_OK,
        "message": "INIT 计划已生成，plan.json 现为执行真相源" if dry_run else "INIT 已完成：项目引导文档和 plan.json 已生成",
        "data": data,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DEV_SDD:init 执行辅助 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
用途:
  从项目 docs/CONTEXT.md 初始化项目入口文档与 docs/plan.json，
  并在覆盖现有内容前返回结构化确认信息。

示例:
  python3 .claude/tools/init/run.py structured-light-stereo --json --dry-run
  python3 .claude/tools/init/run.py skill-tests/fixtures/init/empty-project --json
  python3 .claude/tools/init/run.py projects/demo --confirm-overwrite abc123def456
""",
    )
    parser.add_argument("project", nargs="?", help="可选：目标项目名或项目根目录路径")
    parser.add_argument("--json", action="store_true", help="输出机器可解析 JSON")
    parser.add_argument("--dry-run", action="store_true", help="仅预览将写入的文件，不实际落盘")
    parser.add_argument("--confirm-overwrite", default=None, help="确认覆盖现有文档所需的 token")
    args = parser.parse_args()

    result = run(args.project, args.dry_run, args.confirm_overwrite)
    out(result, args.json)

    if result.get("status") == STATUS_ERROR:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
