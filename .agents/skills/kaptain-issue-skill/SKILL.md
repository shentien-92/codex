---
name: kaptain-issue-skill
description: 使用 Kaptain MCP 查询敏捷组、迭代、事项、评论、动态、工作日志，或创建事项、流转状态、上传富文本附件时使用。适用于需要稳定调用 Kaptain MCP 工具完成敏捷事项相关操作的场景。
---

# Kaptain Issue Skill

> Trellis managed skill update smoke marker: 0.6.0-beta.28.

## 前置要求

使用本 skill 前，先准备好：

1. **获取 Kaptain Token**
   - 登录 [Kaptain 获取 Token](https://kaptain.qunhequnhe.com/workbench/preferences?open=access_token)
   - Token 格式类似：`xxxxxx`

2. **按你的使用环境完成安装**

   **Claude Code / Claude Desktop**

   安装 skill：

   ```bash
   claude plugin marketplace add https://gitlab.qunhequnhe.com/devops/claude-code/marketplace.git
   claude plugin marketplace update qunhe-devops-plugins
   claude plugin install kaptain-issue-skill@qunhe-devops-plugins
   ```

   接入 Kaptain MCP：

   ```
   claude mcp add qunhe-kaptain-mcp --transport stdio `
   --env KAPTAIN_TOKEN=<你的Kaptain Token> `
   --env npm_config_registry=http://npm-registry.qunhequnhe.com `
   --scope user `
   -- npx @qunhe/kaptain-mcp@latest
   ```

   **Windows CMD:**
   ```
   claude mcp add qunhe-kaptain-mcp --transport stdio ^
   --env "KAPTAIN_TOKEN=<你的Kaptain Token>" ^
   --env "npm_config_registry=http://npm-registry.qunhequnhe.com" ^
   --scope user ^
   -- npx @qunhe/kaptain-mcp@latest
   ```

   **MacOS / Linux:**
   ```
   claude mcp add qunhe-kaptain-mcp --transport stdio \
   --env KAPTAIN_TOKEN=<你的Kaptain Token> \
   --env npm_config_registry=http://npm-registry.qunhequnhe.com \
   --scope user \
   -- npx @qunhe/kaptain-mcp@latest
   ```

   **OpenCode**

   安装 skill：

   ```bash
   npx skills add https://gitlab.qunhequnhe.com/devops/claude-code/kaptain-issue-skill.git -a opencode
   ```

   如环境要求，接入 Kaptain MCP：`npx @qunhe/kaptain-mcp@latest`

   **OpenClaw**

   在 OpenClaw 中安装并启用 `kaptain-issue-skill`。

   如环境要求，接入下面这个 Kaptain server：

   ```json
   {
     "mcpServers": {
       "kaptain-mcp": {
         "command": "npx",
         "args": ["@qunhe/kaptain-mcp@latest"],
         "env": {
           "KAPTAIN_TOKEN": "<YOUR_TOKEN>",
           "npm_config_registry": "http://npm-registry.qunhequnhe.com"
         }
       }
     }
   }
   ```

3. **验证是否生效**
   - Claude 环境可通过 `/mcp` 检查 `qunhe-kaptain-mcp` 是否存在
   - 其他环境只要 skill 能正常调用 Kaptain 能力，就说明配置已生效

4. **更新 Skill**（如已安装过）
   - Claude 环境可使用：`claude plugin update kaptain-issue-skill@qunhe-devops-plugins`
   - OpenCode / 其他 Agent 请按各自的 skill 更新方式处理

## 何时使用

当用户要做这些事时使用本 skill：

- 查询当前用户、我的敏捷组、全量敏捷组、业务列表
- 查询、创建、更新迭代
- 查询我的事项、事项列表、事项详情
- 查询事项标签、自定义字段、全局属性配置、全局下拉选项
- 查询事项关联敏捷事项、关联变更、Confluence 文档、测试计划、提测单
- 创建事项、更新事项、流转事项状态
- 查询评论、编辑评论、查询动态记录
- 查询、新增、更新工作日志
- 在事项描述或评论里插入图片/视频
- 查看或分析事项内容里的内网图片/视频链接

## 快速规则

1. **时间戳展示前必须用 Bash 工具转换**（禁止心算或手动计算），规则见 [references/timestamp-conversion.md](./references/timestamp-conversion.md)
2. “我的敏捷组”只能用 `get_my_projects`
3. “全量敏捷组搜索”只能用 `search_projects`
4. “我的事项”只能用 `get_my_work_matters`
5. 查事项详情时，`issueId` 和 `issueKey` 只能二选一
6. 查询事项关联信息时，优先使用专用 tool，不要从详情字段里猜
7. 状态流转优先走 `list_issue_next_nodes` / `get_issue_required_properties` / `transition_issue_status`
8. 记录工时必须走工作日志接口，不要伪造成事项字段更新
9. 描述或评论里要插图/视频时，先 `upload_editor_attachment`，再把返回 `url` 写进 HTML
10. 回复里出现事项 `key` 且场景合适时，必须输出可点击事项链接
11. 对事项执行评论、动态、工作日志等依赖 `cardType` 的操作时，`cardType` 必须与事项详情保持一致；拿不准时先查 `get_issue_detail`，禁止猜值或硬编码
12. 创建事项时，除 `projectId`、`cardType`、`name` 外，凡是项目内存在业务必填风险的字段都必须先向用户确认或从明确上下文获得；禁止为了”先创建成功”而省略、猜测或硬编码字段
13. 创建事项时可参考”同敏捷组、同事项类型、近期正常事项”的字段分布，但参考不等于照抄；所有枚举值和必填字段都必须以当前敏捷组真实配置和用户输入为准
14. 创建需求、任务、缺陷时，skill 需要尽量复刻前端校验逻辑；前端会按 `cardType` 和字段联动规则动态校验必填项，skill 不得只按接口最小参数集创建
15. 如果当前环境拿不到与前端一致的运行时字段配置，就不能声称”已完成前端同款校验”；此时应先补问用户或暂停创建，而不是带着不完整参数继续提交
16. 所有新增、修改类型的操作，默认都要先参考”同敏捷组、同事项类型、近期正常事项”；禁止脱离历史样本去猜枚举值、标签、模块、关联字段或业务字段
17. 遇到标签筛选，先用 `list_issue_tags` 拿标签 id，再构造 `search.tagIdList`
18. 遇到事项筛选时，需区分字段类型：
   - **全局下拉选项**（发现方式、缺陷类型、发现环境、发现版本、解决结果等）：用 `list_select_options`，`projectId` 传 0 获取全局选项，从 `optionList` 中匹配 `value` 得到 `id`，构造 `search.bugFindMethod` 等筛选条件
   - **自定义字段**（业务分类、Release、是否已自动化等敏捷组自定义配置）：用 `list_issue_custom_properties`，从 `options` 中匹配选项名称得到 `logoId`，构造 `customData`
   - 禁止猜测或硬编码选项 ID
19. 遇到事项自定义字段更新或创建，先用 `list_issue_custom_properties` 确认字段 id、类型、选项，再决定放进 `customData`
20. 遇到全局属性必填或创建页里的”研发标识/全局属性”一类字段，先用 `list_issue_global_properties` 确认是否需要传 `saveGlobalPropertyValues`

## 调用顺序

### 查询敏捷组或迭代

1. 用户相关信息先看 [references/project-and-iteration.md](./references/project-and-iteration.md)
2. 如果是“某敏捷组按迭代维度的事项”，先查迭代，再查事项
   - 当前迭代：先 `list_iterations`，再按 `startTime <= now <= endTime` 选中当前迭代

### 查询事项

1. 先看 [references/issues.md](./references/issues.md)
2. 宽泛查询先缩小范围，不要直接倾倒大列表
3. 如果用户提到”按标签筛选””标签下拉””标签列表”，先 `list_issue_tags`
4. **事项筛选需区分字段类型：**
   - **全局下拉选项**（发现方式、缺陷类型、发现环境等）：调用 `list_select_options`，`projectId` 传 0，从 `optionList` 匹配 `value` 得到 `id`
   - **自定义字段**（业务分类、Release等敏捷组配置）：调用 `list_issue_custom_properties`，从 `options` 匹配得到 `logoId`
5. 如果用户要看事项关联信息，也走 [references/issues.md](./references/issues.md) 里的对应专用 tool
6. 涉及事项链接时，按 [references/common-rules.md](./references/common-rules.md) 输出

### 创建、更新、流转事项

1. 先看 [references/issues.md](./references/issues.md)
2. 如果涉及自定义字段，先 `list_issue_custom_properties`
3. 如果涉及全局属性、研发标识或创建时报“属性不能为空”，先 `list_issue_global_properties`
4. 如果用户要求“和前端尽量一致”或场景涉及动态必填项，再看 [references/frontend-config-sync.md](./references/frontend-config-sync.md)
5. 如果要修改状态，优先走状态流转，不要默认走通用更新
6. 如果描述里要插图/视频，再补看 [references/comments-and-media.md](./references/comments-and-media.md)

### 评论、动态、媒体

1. 评论、动态和媒体处理先看 [references/comments-and-media.md](./references/comments-and-media.md)
2. 内网媒体链接分析场景也走这个文件

### 工时和工作日志

1. 先看 [references/worklogs.md](./references/worklogs.md)
2. 流转状态时如果要顺带登记工时，也先看这个文件

## 参考文件导航

- 通用规则、事项链接、调用原则：
  [references/common-rules.md](./references/common-rules.md)
- 用户、敏捷组、业务、迭代：
  [references/project-and-iteration.md](./references/project-and-iteration.md)
- 事项查询、创建、更新、状态流转、字段映射：
  [references/issues.md](./references/issues.md)
- 前端同源配置、字段配置、扩展接口：
  [references/frontend-config-sync.md](./references/frontend-config-sync.md)
- 评论、动态、富文本插图、媒体链接下载分析：
  [references/comments-and-media.md](./references/comments-and-media.md)
- 工作日志与工时规则：
  [references/worklogs.md](./references/worklogs.md)
- 时间戳转换规则：
  [references/timestamp-conversion.md](./references/timestamp-conversion.md)

## 默认做法

1. 严格按工具语义调用，不混用工具
2. 未确认的字段优先透传，不在 skill 中臆造枚举
3. 如果用户表达的是“我的相关数据”，优先判断是否先查当前用户
4. 只有在当前场景需要时再读取对应 `references/` 文件，不要一次性加载全部细节
