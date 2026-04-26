# DEV SDD Dashboard BRIEF

- 目标：提供一条命令定期查看 DEV_SDD 当前状态，并生成清晰直观的静态 HTML 仪表盘。
- 命令：`python3 .claude/tools/dev-sdd-dashboard/run.py --html --json`。
- 双击入口：根目录 `tools/dev-sdd-dashboard.sh`，Linux 桌面可用 `tools/dev-sdd-dashboard.desktop`。
- 范围：聚合 framework-health、review-cockpit、candidate review、memory conflicts、model behavior、latest Layer1 report、config.yaml。
- 输出：JSON envelope、`docs/reports/dev-sdd-dashboard.html`、`.cache/dev_sdd/dashboard_history.jsonl`。
- 交互：`interactive` 子命令以编号菜单展示人工确认项，支持 `list`、`detail <n>`、`command <n>`、`quit`。
- 约束：默认只读，不自动修改 candidate/memory；`--open` 只打开本地 HTML；历史记录写入 `.cache/`。
- 双击脚本失败时只写 `.cache/dev_sdd/dashboard-launch.log` 并提示，不修改项目状态。
- 验收：Layer1 测试验证 JSON/HTML/交互 dry-run，不依赖真实模型 API。
