# SDD Framework v2.1 补丁包
# 个体开发效果增强：会话快照 + 智能记忆加载

## 此包包含的文件

### 新增文件（6个）
- `.claude/hooks/session-snapshot/HOOK.md`     会话快照机制说明
- `.claude/hooks/session-snapshot/write.py`    会话快照写入脚本
- `.claude/hooks/verify-rules/check.sh`        每日验证脚本
- `.claude/skills/context-probe/SKILL.md`      自动记忆匹配技能
- `docs/PROJECT_RULES.md`                      Claude.ai Rules 配置文档
- `projects/_template/memory/sessions/.gitkeep` sessions 目录占位

### 修改文件（5个）
- `CLAUDE.md`                                  加入 Step 2.5 + context-probe
- `memory/INDEX.md`                            加入 context-probe 加载说明
- `projects/_template/CLAUDE.md`               加入 sessions 加载地图
- `projects/_template/memory/INDEX.md`         加入会话历史区块
- `.claude/settings.local.json`                加入新脚本执行权限

---

## 安装步骤

### Step 1：复制文件到框架目录
将此包中所有文件按原路径覆盖到你的 SDD Framework 仓库根目录。

```bash
# 解压后在框架根目录执行
cp -r sdd-patch/.claude .
cp -r sdd-patch/docs .
cp -r sdd-patch/memory .
cp -r sdd-patch/projects/_template/memory projects/_template/
cp -r sdd-patch/projects/_template/CLAUDE.md projects/_template/
cp sdd-patch/CLAUDE.md .
```

### Step 2：给脚本添加执行权限
```bash
chmod +x .claude/hooks/verify-rules/check.sh
chmod +x .claude/hooks/session-snapshot/write.py
```

### Step 3：为现有项目创建 sessions 目录
```bash
# 替换 your-project 为你的实际项目名
mkdir -p projects/your-project/memory/sessions
```

### Step 4：配置 Claude.ai Project Rules
1. 打开 docs/PROJECT_RULES.md
2. 复制"Rules 正文"部分（两条虚线之间的内容）
3. 粘贴到 Claude.ai 项目设置 → Project Instructions

### Step 5：验证安装
```bash
# 开启新的 Claude 对话，发送任意消息
# 确认看到 [NEW SESSION] 或 [RESUME] 标记

# 工作结束后运行验证脚本
bash .claude/hooks/verify-rules/check.sh
```

---

## 核心变化

**之前**：记忆沉淀依赖完整走完 TDD 流程，对话中断 = 经验丢失

**之后**：
- 每个决策节点自动写入 `memory/sessions/` 快照
- 下次打开对话自动续接上次进度
- 记忆按任务关键词自动匹配，不需要手动查加载地图
- 每日验证脚本确认系统是否正常运行

---

## 常见问题

**Q: 原有的 sessions 历史会丢吗？**
A: 不会，sessions/ 是新增目录，不影响现有文件。

**Q: 修改 CLAUDE.md 会影响现有项目吗？**
A: 只加了 Step 2.5，其他步骤不变。现有项目无缝兼容。

**Q: verify-rules 脚本报告 ❌ 怎么办？**
A: 大概率是 sessions/ 目录不存在，或 Rules 未在 Claude.ai 配置。
   按 Step 3 和 Step 4 重新检查。
