# /project:switch — 切换激活项目

## 用法
```
/project:switch <project-name>
```

## 执行步骤
1. 确认目标项目目录存在；workspace 类型项目应选择具体子项目目录，而不是 workspace 根
2. 更新 CLAUDE.md/AGENTS.md 中的 PROJECT 和 PROJECT_PATH 字段：
   ```
   PROJECT: <logical-project-name>
   PROJECT_PATH: <真实项目根路径，默认 projects/<project-name>；workspace 子项目写 projects/<workspace>/<child>>
   ```
3. 读取 `<PROJECT_PATH>/CLAUDE.md`
4. 读取 `<PROJECT_PATH>/memory/INDEX.md`
5. 输出确认：
   ```
   [项目切换] → <project-name>
   项目摘要：<3行摘要内容>
   激活完成，等待任务
   ```

## 注意
- 切换后框架 memory/ 仍然有效（框架规则不变）
- 项目 memory 仅在激活期间加载
- workspace 下的 sibling 子项目必须分别配置自己的 `PROJECT_PATH`，避免 session/memory/docs/challenges 混写
- 若目录不存在：提示使用 /project:new 创建
