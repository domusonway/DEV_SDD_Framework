# /project:switch — 切换激活项目

## 用法
```
/project:switch <project-name>
```

## 执行步骤
1. 确认 `projects/<project-name>/` 目录存在
2. 更新 CLAUDE.md 中的 PROJECT 和 PROJECT_PATH 字段：
   ```
   PROJECT: <project-name>
   PROJECT_PATH: projects/<project-name>
   ```
3. 读取 `projects/<project-name>/CLAUDE.md`
4. 读取 `projects/<project-name>/memory/INDEX.md`
5. 输出确认：
   ```
   [项目切换] → <project-name>
   项目摘要：<3行摘要内容>
   激活完成，等待任务
   ```

## 注意
- 切换后框架 memory/ 仍然有效（框架规则不变）
- 项目 memory 仅在激活期间加载
- 若目录不存在：提示使用 /project:new 创建
