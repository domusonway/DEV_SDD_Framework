#!/usr/bin/env python3
from __future__ import annotations

"""Aggregate review signals into a static Review Cockpit report."""

import argparse
import html
import importlib.util
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)


def _python_tool(*parts: str) -> list[str]:
    return [sys.executable, str(ROOT.joinpath(*parts))]


def _run_json(command: list[str]) -> dict[str, Any]:
    result = subprocess.run(command, cwd=str(ROOT), capture_output=True, text=True)
    if result.returncode not in (0, 1):
        return {"status": "error", "message": (result.stderr or result.stdout).strip(), "data": {}, "returncode": result.returncode}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"status": "error", "message": "invalid JSON output", "data": {"stdout": result.stdout[:500], "stderr": result.stderr[:500]}}


def collect(project: str | None = None, task: str = "") -> dict[str, Any]:
    project_args = ["--project", project] if project else []
    health_cmd = _python_tool(".claude", "tools", "framework-health", "run.py") + ["--json"] + project_args
    if task:
        health_cmd += ["--task", task]
    signals = {
        "framework_health": _run_json(health_cmd),
        "candidate_review": _run_json(_python_tool(".claude", "tools", "skill-tracker", "tracker.py") + ["review-summary", "--json"]),
        "memory_conflicts": _run_json(_python_tool(".claude", "tools", "memory-conflicts", "run.py") + ["--json"] + project_args),
        "model_behavior": _run_json(_python_tool(".claude", "tools", "model-behavior", "run.py") + ["readiness", "--json"]),
    }
    issues = []
    for name, signal in signals.items():
        if signal.get("status") == "error":
            issues.append({"level": "high", "source": name, "message": signal.get("message", "error")})
        elif signal.get("status") == "warning":
            issues.append({"level": "medium", "source": name, "message": signal.get("message", "warning")})
    status = "ok"
    if any(issue["level"] == "high" for issue in issues):
        status = "error"
    elif issues:
        status = "warning"
    return {"generated_at": datetime.now().isoformat(timespec="seconds"), "project": project, "task": task, "status": status, "issues": issues, "signals": signals}


def render_html(data: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    cards = []
    for name, signal in data["signals"].items():
        cards.append(
            "<section class='card'>"
            f"<h2>{esc(name.replace('_', ' ').title())}</h2>"
            f"<p class='status {esc(signal.get('status', 'unknown'))}'>{esc(signal.get('status', 'unknown'))}</p>"
            f"<p>{esc(signal.get('message', ''))}</p>"
            f"<pre>{esc(json.dumps(signal.get('data', {}), ensure_ascii=False, indent=2)[:6000])}</pre>"
            "</section>"
        )
    issues = "".join(f"<li><strong>{esc(i['level'])}</strong> {esc(i['source'])}: {esc(i['message'])}</li>" for i in data["issues"])
    if not issues:
        issues = "<li>No actionable issues.</li>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DEV SDD Review Cockpit</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, sans-serif; background: #0f172a; color: #e2e8f0; }}
    header {{ padding: 28px 36px; background: linear-gradient(135deg, #111827, #1e3a8a); }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    main {{ padding: 24px 36px; display: grid; gap: 18px; }}
    .summary, .card {{ border: 1px solid #334155; border-radius: 16px; padding: 18px; background: #111827; box-shadow: 0 12px 32px rgba(0,0,0,.25); }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 18px; }}
    .status {{ display: inline-block; padding: 3px 10px; border-radius: 999px; background: #475569; text-transform: uppercase; font-size: 12px; }}
    .status.ok {{ background: #166534; }} .status.warning {{ background: #a16207; }} .status.error {{ background: #991b1b; }}
    pre {{ max-height: 360px; overflow: auto; padding: 12px; border-radius: 10px; background: #020617; color: #bfdbfe; font-size: 12px; }}
  </style>
</head>
<body>
  <header>
    <h1>DEV SDD Review Cockpit</h1>
    <p>Generated {esc(data['generated_at'])} | status <span class="status {esc(data['status'])}">{esc(data['status'])}</span></p>
  </header>
  <main>
    <section class="summary"><h2>Action Items</h2><ul>{issues}</ul></section>
    <div class="grid">{''.join(cards)}</div>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD Review Cockpit")
    parser.add_argument("--project", default=None)
    parser.add_argument("--task", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--html", nargs="?", const="docs/review-cockpit.html", default=None, help="write static HTML report")
    args = parser.parse_args()

    data = collect(args.project, args.task)
    if args.html:
        output = (ROOT / args.html).resolve() if not Path(args.html).is_absolute() else Path(args.html)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_html(data), encoding="utf-8")
        data["html_path"] = workflow_cli_common.rel_path(output, ROOT)
    payload = {"status": data["status"], "message": f"review cockpit: {data['status']}", "data": data}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
        if args.html:
            print(f"html: {data['html_path']}")
        for issue in data["issues"]:
            print(f"- [{issue['level']}] {issue['source']}: {issue['message']}")
    return 1 if data["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
