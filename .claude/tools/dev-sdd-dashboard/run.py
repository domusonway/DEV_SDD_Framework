#!/usr/bin/env python3
from __future__ import annotations

"""One-command DEV_SDD status dashboard with static HTML and simple interaction."""

import argparse
import html
import importlib.util
import json
import subprocess
import sys
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parents[1]
COMMON_SPEC = importlib.util.spec_from_file_location("workflow_cli_common", TOOLS_ROOT / "workflow_cli_common.py")
assert COMMON_SPEC and COMMON_SPEC.loader
workflow_cli_common = importlib.util.module_from_spec(COMMON_SPEC)
COMMON_SPEC.loader.exec_module(workflow_cli_common)

ROOT = workflow_cli_common.find_framework_root(__file__)
DEFAULT_HTML = ROOT / "docs" / "reports" / "dev-sdd-dashboard.html"
DEFAULT_HISTORY = ROOT / ".cache" / "dev_sdd" / "dashboard_history.jsonl"


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


def _latest_report() -> dict[str, Any]:
    reports = sorted((ROOT / "skill-tests" / "reports").glob("report_L1_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not reports:
        return {"path": None, "exists": False, "passed": None, "total": None, "pass_rate": None}
    path = reports[0]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {}
    return {
        "path": workflow_cli_common.rel_path(path, ROOT),
        "exists": True,
        "passed": payload.get("passed"),
        "total": payload.get("total"),
        "pass_rate": payload.get("pass_rate"),
        "timestamp": payload.get("timestamp"),
    }


def _issue_actions(signals: dict[str, Any], health_issues: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for issue in health_issues:
        source = issue.get("source", "health")
        command = "python3 .claude/tools/framework-health/run.py --json"
        if source == "candidate_review":
            command = "python3 .claude/tools/skill-tracker/tracker.py review-summary --json"
        elif source == "memory_conflicts":
            command = "python3 .claude/tools/memory-conflicts/run.py --json"
        elif source == "memory_prune":
            command = "python3 .claude/tools/memory-usage/run.py prune --json"
        elif source == "model_behavior":
            command = "python3 .claude/tools/model-behavior/run.py readiness --json"
        actions.append({
            "level": issue.get("level", "medium"),
            "source": source,
            "title": issue.get("message", "Review required"),
            "detail": issue,
            "recommended_command": command,
        })

    candidate_data = ((signals.get("candidate_review") or {}).get("data") or {})
    actionable = [item for item in candidate_data.get("items", []) if item.get("recommendation") not in (None, "none")]
    for item in actionable:
        actions.append({
            "level": "medium",
            "source": "candidate_review",
            "title": f"Review candidate {item.get('id')}",
            "detail": item,
            "recommended_command": "python3 .claude/tools/skill-tracker/tracker.py review-summary --json",
        })
    return actions


def _compact_counts(data: dict[str, Any]) -> dict[str, Any]:
    health = data.get("signals", {}).get("framework_health", {}).get("data", {})
    health_signals = health.get("signals", {}) if isinstance(health, dict) else {}
    candidate = (health_signals.get("candidate_review", {}).get("data") or {}) if isinstance(health_signals, dict) else {}
    memory_conflicts = (health_signals.get("memory_conflicts", {}).get("data") or {}) if isinstance(health_signals, dict) else {}
    model_behavior = (health_signals.get("model_behavior", {}).get("data") or {}) if isinstance(health_signals, dict) else {}
    latest_report = data.get("reports", {}).get("latest_layer1", {})
    return {
        "candidate_total": candidate.get("total", 0),
        "candidate_by_recommendation": candidate.get("by_recommendation", {}),
        "memory_conflicts": memory_conflicts.get("conflict_count", 0),
        "model_provider": (model_behavior.get("api") or {}).get("provider"),
        "model": (model_behavior.get("api") or {}).get("model"),
        "layer1": f"{latest_report.get('passed')}/{latest_report.get('total')}" if latest_report.get("exists") else "unknown",
    }


def collect(project: str | None = None, task: str = "") -> dict[str, Any]:
    project_args = ["--project", project] if project else []
    health_cmd = _python_tool(".claude", "tools", "framework-health", "run.py") + ["--json"] + project_args
    if task:
        health_cmd += ["--task", task]
    review_html = ROOT / "docs" / "reports" / "review-cockpit.html"
    signals = {
        "framework_health": _run_json(health_cmd),
        "review_cockpit": _run_json(_python_tool(".claude", "tools", "review-cockpit", "run.py") + ["--json", "--html", str(review_html)] + (["--project", project] if project else [])),
        "memory_conflicts": _run_json(_python_tool(".claude", "tools", "memory-conflicts", "run.py") + ["--json"] + project_args),
        "model_behavior": _run_json(_python_tool(".claude", "tools", "model-behavior", "run.py") + ["readiness", "--json"]),
        "candidate_review": _run_json(_python_tool(".claude", "tools", "skill-tracker", "tracker.py") + ["review-summary", "--json"]),
        "memory_prune": _run_json(_python_tool(".claude", "tools", "memory-usage", "run.py") + ["prune", "--json"] + project_args),
    }
    health_data = signals["framework_health"].get("data") or {}
    framework_status = health_data.get("status") or signals["framework_health"].get("status") or "unknown"
    health_issues = health_data.get("issues") or []
    reports = {
        "latest_layer1": _latest_report(),
        "review_cockpit_html": workflow_cli_common.rel_path(review_html, ROOT) if review_html.exists() else None,
    }
    data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "project": project or health_data.get("project"),
        "task": task,
        "overview": {
            "framework_status": framework_status,
            "project": project or health_data.get("project"),
            "issue_count": len(health_issues),
            "latest_layer1": reports["latest_layer1"],
        },
        "signals": signals,
        "reports": reports,
    }
    data["action_items"] = _issue_actions(signals, health_issues)
    data["counts"] = _compact_counts(data)
    status = "ok"
    if framework_status == "error" or any(item.get("level") == "high" for item in data["action_items"]):
        status = "error"
    elif framework_status == "warning" or data["action_items"]:
        status = "warning"
    data["status"] = status
    return data


def write_history(data: dict[str, Any], history_path: Path) -> dict[str, Any]:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "timestamp": data["generated_at"],
        "status": data["status"],
        "project": data.get("project"),
        "framework_status": data["overview"].get("framework_status"),
        "issue_count": len(data.get("action_items", [])),
        "counts": data.get("counts", {}),
    }
    with open(history_path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    return event


def _status_class(value: Any) -> str:
    text = str(value or "unknown").lower()
    if text in {"ok", "completed", "pass", "true"}:
        return "ok"
    if text in {"error", "fail", "false"}:
        return "error"
    return "warning"


def render_html(data: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    overview = data["overview"]
    counts = data.get("counts", {})
    layer1 = overview.get("latest_layer1") or {}
    actions = data.get("action_items", [])
    action_html = "".join(
        f"<li><b>{esc(item['level'])}</b> {esc(item['source'])}: {esc(item['title'])}<br><code>{esc(item['recommended_command'])}</code></li>"
        for item in actions
    ) or "<li>No action required.</li>"

    signal_cards = []
    for name, signal in data["signals"].items():
        signal_cards.append(
            "<section class='card'>"
            f"<h3>{esc(name.replace('_', ' ').title())}</h3>"
            f"<span class='pill {_status_class(signal.get('status'))}'>{esc(signal.get('status'))}</span>"
            f"<p>{esc(signal.get('message', ''))}</p>"
            f"<pre>{esc(json.dumps(signal.get('data', {}), ensure_ascii=False, indent=2)[:3500])}</pre>"
            "</section>"
        )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>DEV SDD Dashboard</title>
  <style>
    :root {{ color-scheme: dark; --bg:#08111f; --panel:#111827; --muted:#94a3b8; --line:#334155; --ok:#15803d; --warn:#a16207; --err:#b91c1c; --accent:#38bdf8; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: radial-gradient(circle at top left, #1e3a8a 0, transparent 35%), var(--bg); color:#e5e7eb; }}
    header {{ padding:34px 42px; border-bottom:1px solid var(--line); }}
    h1 {{ margin:0; font-size:34px; letter-spacing:-.04em; }}
    h2 {{ margin:0 0 14px; }}
    main {{ padding:26px 42px 44px; display:grid; gap:20px; }}
    .grid {{ display:grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap:16px; }}
    .card, .wide {{ background:rgba(17,24,39,.88); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 18px 55px rgba(0,0,0,.24); }}
    .metric {{ font-size:30px; font-weight:750; }}
    .label {{ color:var(--muted); font-size:13px; }}
    .pill {{ display:inline-block; padding:4px 11px; border-radius:999px; font-size:12px; text-transform:uppercase; background:#475569; }}
    .pill.ok {{ background:var(--ok); }} .pill.warning {{ background:var(--warn); }} .pill.error {{ background:var(--err); }}
    ul {{ margin:0; padding-left:20px; }} li {{ margin:9px 0; }} code {{ color:#bae6fd; }}
    pre {{ overflow:auto; max-height:260px; background:#020617; border-radius:12px; padding:12px; color:#bfdbfe; font-size:12px; }}
    a {{ color:var(--accent); }}
  </style>
</head>
<body>
  <header>
    <h1>DEV SDD Dashboard</h1>
    <p>Generated {esc(data['generated_at'])} | Project {esc(data.get('project'))} | <span class="pill {_status_class(data['status'])}">{esc(data['status'])}</span></p>
  </header>
  <main>
    <section class="grid">
      <div class="card"><div class="label">Framework Health</div><div class="metric">{esc(overview.get('framework_status'))}</div></div>
      <div class="card"><div class="label">Layer1 Tests</div><div class="metric">{esc(layer1.get('passed'))}/{esc(layer1.get('total'))}</div><div class="label">{esc(layer1.get('pass_rate'))}</div></div>
      <div class="card"><div class="label">Model</div><div class="metric">{esc(counts.get('model'))}</div><div class="label">{esc(counts.get('model_provider'))}</div></div>
      <div class="card"><div class="label">Memory Conflicts</div><div class="metric">{esc(counts.get('memory_conflicts'))}</div></div>
    </section>
    <section class="wide"><h2>Action Required</h2><ul>{action_html}</ul></section>
    <section class="grid">
      <div class="card"><h2>Memory System</h2><p>Conflicts: {esc(counts.get('memory_conflicts'))}</p><p>Candidate total: {esc(counts.get('candidate_total'))}</p><pre>{esc(json.dumps(counts.get('candidate_by_recommendation'), ensure_ascii=False, indent=2))}</pre></div>
      <div class="card"><h2>Reports</h2><p>Latest Layer1: {esc(layer1.get('path'))}</p><p>Review Cockpit: {esc(data.get('reports', {}).get('review_cockpit_html'))}</p></div>
    </section>
    <section class="grid">{''.join(signal_cards)}</section>
  </main>
</body>
</html>
"""


def write_html(data: dict[str, Any], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_html(data), encoding="utf-8")
    return workflow_cli_common.rel_path(path, ROOT)


def interactive_payload(project: str | None, task: str) -> dict[str, Any]:
    data = collect(project, task)
    commands = [item["recommended_command"] for item in data.get("action_items", [])]
    if not commands:
        commands = [
            "python3 .claude/tools/framework-health/run.py --json",
            "python3 .claude/tools/review-cockpit/run.py --html docs/reports/review-cockpit.html",
            "python3 .claude/tools/memory-conflicts/run.py --json",
        ]
    return {
        "mode": "interactive_dry_run",
        "status": data["status"],
        "menu": ["list", "detail <number>", "command <number>", "quit"],
        "action_items": data.get("action_items", []),
        "commands": commands,
    }


def run_interactive(project: str | None, task: str, dry_run: bool, emit_json: bool) -> int:
    payload = interactive_payload(project, task)
    if dry_run:
        envelope = {"status": payload["status"], "message": "dashboard interactive dry-run", "data": payload}
        if emit_json:
            print(json.dumps(envelope, ensure_ascii=False, indent=2))
        else:
            print(envelope["message"])
            for idx, item in enumerate(payload["action_items"], 1):
                print(f"{idx}. [{item['level']}] {item['source']}: {item['title']}")
        return 1 if payload["status"] == "error" else 0

    items = payload["action_items"]
    print("DEV SDD Dashboard Interactive")
    print("Commands: list | detail <n> | command <n> | quit")
    while True:
        choice = input("dashboard> ").strip()
        if choice in {"quit", "q", "exit"}:
            return 0
        if choice == "list":
            if not items:
                print("No action required.")
            for idx, item in enumerate(items, 1):
                print(f"{idx}. [{item['level']}] {item['source']}: {item['title']}")
            continue
        if choice.startswith("detail ") or choice.startswith("command "):
            _, raw_idx = choice.split(maxsplit=1)
            try:
                idx = int(raw_idx) - 1
                item = items[idx]
            except Exception:
                print("Invalid item number.")
                continue
            if choice.startswith("detail "):
                print(json.dumps(item, ensure_ascii=False, indent=2))
            else:
                print(item["recommended_command"])
            continue
        print("Unknown command. Use: list | detail <n> | command <n> | quit")


def main() -> int:
    parser = argparse.ArgumentParser(description="DEV_SDD one-command dashboard")
    subparsers = parser.add_subparsers(dest="command")

    parser.add_argument("--project", default=None)
    parser.add_argument("--task", default="")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--html", nargs="?", const=str(DEFAULT_HTML), default=None)
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    parser.add_argument("--open", action="store_true")

    interactive = subparsers.add_parser("interactive", help="simple human confirmation menu")
    interactive.add_argument("--project", default=None)
    interactive.add_argument("--task", default="")
    interactive.add_argument("--dry-run", action="store_true")
    interactive.add_argument("--json", action="store_true")

    args = parser.parse_args()
    if args.command == "interactive":
        return run_interactive(args.project, args.task, args.dry_run, args.json)

    data = collect(args.project, args.task)
    data["history_event"] = write_history(data, Path(args.history))
    if args.html:
        html_path = Path(args.html)
        if not html_path.is_absolute():
            html_path = (ROOT / html_path).resolve()
        data["html_path"] = write_html(data, html_path)
        if args.open:
            webbrowser.open(html_path.as_uri())

    payload = {"status": data["status"], "message": f"dev-sdd dashboard: {data['status']}", "data": data}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["message"])
        if data.get("html_path"):
            print(f"html: {data['html_path']}")
        for item in data.get("action_items", []):
            print(f"- [{item['level']}] {item['source']}: {item['title']}")
    return 1 if data["status"] == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
