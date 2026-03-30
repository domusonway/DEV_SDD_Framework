# HOOK: permission-auditor
> 触发时机：每个项目交付后（memory-keeper 完成时）执行一次

---

## 为什么需要 Permission-Auditor

`settings.local.json` 的 deny 规则是框架中最静态的部分，但随着工具增加和使用模式
演变，会出现两类问题：

1. **deny 过宽**：某个合理操作被 deny 规则误阻止，导致 Claude 卡住或绕道
2. **allow 范围过宽**：`Write(projects/${PROJECT}/**)` 这类规则允许的范围
   超出实际使用需要，增加了误操作风险

---

## 执行步骤

### Step 1: 运行审计脚本
```bash
python3 .claude/hooks/permission-auditor/audit.py ${PROJECT}
```

### Step 2: 审阅输出候选

候选写入 `memory/candidates/PERM_CAND_*.yaml`，标注 `permission_relax` 或
`permission_tighten` 类型。

### Step 3: 权限调整原则

**放宽（relax）门槛**：需要 ≥2 个项目出现相同阻塞才提议放宽，且放宽幅度最小化
（例：从 deny 移到 ask，而非直接 allow）。

**收紧（tighten）门槛**：只要发现 allow 规则的范围明显超出实际使用，立即提议收紧。

---

## 绝对不提议放宽的操作（M2修复 — 已扩展）

以下操作永远保持 deny，permission-auditor **不生成**对应的 relax 候选：

```
git commit / git push / git reset / git checkout / git merge / git rebase
Write(.claude/skills/**)
Write(.claude/hooks/**)
Write(CLAUDE.md)
Write(memory/INDEX.md)
Write(memory/critical/**)
sudo *
pip install * / npm install *
rm -rf * / rm -f * / rm -r * / rmdir *   ← M2修复：覆盖所有删除变体
```

> 注意：`rm -f *.pyc` 属于 `rm -f *` 模式，同样永久 deny。
> 若项目确实需要清理编译缓存，应在 post-green/run.sh 中用
> `find . -name "*.pyc" -delete` 代替。

---

## 自动执行脚本
```bash
python3 .claude/hooks/permission-auditor/audit.py <PROJECT_NAME>
```
