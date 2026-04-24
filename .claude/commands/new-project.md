# /project:new — 从模板创建新项目

## 用法
```
/project:new <project-name>
```

## 执行步骤
1. 检查 `projects/<project-name>/` 是否已存在（存在则报错）
2. 复制模板：
   ```bash
   cp -r projects/_template/ projects/<project-name>/
   ```
3. 替换模板占位符：
   - `{{PROJECT_NAME}}` → `<project-name>`
   - `{{DATE}}` → 当前日期（YYYY-MM-DD）
   - `{{COMPLEXITY}}` → 待填写（运行 complexity-assess 后填入）
4. 运行 complexity-assess skill 评估项目复杂度
5. 将复杂度结果填入 `projects/<project-name>/CLAUDE.md`
6. 保留模板中的项目级执行文档语义：
   - `projects/<project-name>/docs/plan.json` = 项目执行状态源
   - `projects/<project-name>/docs/PLAN.md` = 从 `plan.json` 派生的只读视图
   - `projects/<project-name>/docs/sub_docs/` = 任务级分析/实现/验证文档（按领域分层）
7. 调用 /project:switch 激活新项目
8. 输出确认：
    ```
    [新项目创建] <project-name>
    模板已复制，占位符已替换
    复杂度评估：[L/M/H 模式]
    项目已激活，等待任务
    ```

## 模板位置
`projects/_template/` — 框架 repo 自带，随框架版本管理
