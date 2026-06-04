---
name: doc-autogen
description: 自动分析二方包代码变更，增量更新 README 文档并生成 CHANGELOG。当用户提到“更新文档”、“同步变更”或“写日志”时触发。
---

# 文档智能同步技能 (Ultra-Adaptive)

作为文档专家，请通过以下两阶段自动化流程处理用户请求。

## 第一阶段：感知与自适应寻址 (Perception)

1. **多模式寻径 (Crucial)**：
   - 优先执行跨平台指令：`node -e "console.log(require('fs').readdirSync('.', {recursive: true}).find(p => p.endsWith('doc-autogen')) || '.')" `
   - 若失败，根据 Shell 类型重试：
     - Windows PowerShell/CMD: `dir /s /b /ad | findstr "doc-autogen"`
     - Unix Bash: `find . -maxdepth 4 -name "doc-autogen" -type d`
   - 将确定的有效路径记为 `<SKILL_PATH>`。

2. **状态探测与 Diff 提取**：
   - 运行 `node <SKILL_PATH>/scripts/detector.js` 获取 README 现状。
   - 运行 `node <SKILL_PATH>/scripts/parser.js` 提取 Git 变更。

3. **智能重构策略 (Brain)**：
   - **语义审计**：对比代码 Diff 与 README 现有示例。若函数签名、配置项或调用流程发生变化，必须**全量重构**相关 Markdown 章节。
   - **风格对齐**：保持原有的标题层级（#）、缩进风格及语气。
   - **决策分流**：
     - **全量重构**：代码影响使用逻辑时，重构 `fullReadme`。
     - **仅日志**：若仅为内部优化，仅生成 `changelogEntry`，不触动 README

## 第二阶段：精准写入 (Action)

1. **中转文件构建**：将以下字段写入当前目录下的 `temp_data.json`（使用 `>` 重定向或文件操作工具）：
   - `projectName`, `description`, `usageExample`, `version`
   - `fullReadme`: 包含所有重构逻辑后的**全量内容**。
   - `changelogEntry`: 简洁的变更摘要。

2. **顺序执行写入**：
   - **更新 README**：仅在策略决策需要更新时执行 `node <SKILL_PATH>/scripts/writer.js --type readme --file temp_data.json`。
   - **同步日志**：始终执行 `node <SKILL_PATH>/scripts/writer.js --type changelog --file temp_data.json`。

4. **收尾工作**：
   - 执行 `rm temp_data.json` (Unix) 或 `del temp_data.json` (Windows) 删除中转文件，确保环境整洁。

## 关键约束 (Guardrails)
- **避开引号地狱**：**严禁**通过 `--data` 传递 JSON 字符串，必须全程依赖 `temp_data.json` 文件中转。
- **路径引用规范**：所有 `node` 指令必须使用 `<SKILL_PATH>` 动态前缀。
- **无损更新**：重构时确保不丢失用户手动编写的非代码相关文档（如：项目背景、致谢等）。
- **交互告知**：在执行写入前，简要告知用户：“识别到 API 变更，正在重构 README 示例并同步日志...”。