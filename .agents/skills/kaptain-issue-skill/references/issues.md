# 事项

## `list_issues`

- 标准筛选字段直接放进 `search`
- 自定义字段优先放进 `customData`
- 全局属性字段用 `globalPropertyKey字段名`
- 标签筛选先通过 `list_issue_tags` 确认标签 id，再传 `search.tagIdList`
- **全局下拉选项筛选（如"发现方式=工单"、"缺陷类型=功能缺陷"等）必须先调用 `list_select_options` 获取全局选项配置，`projectId` 传 0，从返回结果中匹配选项名称得到 `id`，再构造筛选条件；禁止猜测或硬编码选项 ID**
- **自定义字段筛选（如"业务分类=多边形建模"）必须先调用 `list_issue_custom_properties` 获取字段配置和选项列表，从 `options` 中匹配选项名称得到 `logoId`，再构造 `customData` 进行筛选；禁止猜测或硬编码选项 ID**
- 时间区间字段传长度为 2 的数组
- 宽泛查询先缩小范围，不要一次返回过多结果

### 常用筛选字段

这些字段来自 Kaptain 前端和 MCP 当前可透传的常用查询形态。除非用户明确要求全量查询，否则优先组合敏捷组、事项类型、状态或时间范围缩小结果集。

| 用户说法 | 推荐参数位置 | 示例 |
| --- | --- | --- |
| 敏捷组 / 项目 | `search.projectId` | `"projectId": 269` |
| 事项类型 / 需求 / 任务 / 缺陷 | `search.cardTypes` | `"cardTypes": [3]` |
| 迭代 | `search.iterationId` 或 `search.iterationIds` | `"iterationIds": [123, 456]` |
| 状态 | `search.statusIds` | `"statusIds": [1001, 1002]` |
| 负责人 / 指派人 | `search.assignee` 或 `search.assignees` | `"assignees": ["zhangsan"]` |
| 创建人 | `search.creator` 或 `search.creators` | `"creators": ["zhangsan"]` |
| 抄送人 | `search.cc` 或 `search.ccs` | `"ccs": ["zhangsan"]` |
| 标题 / 关键词 / 事项 Key | `search.name` | `"name": "SCHOOL-123"` |
| 标签 | `search.tagIdList` | `"tagIdList": [11, 12]` |
| 模块 | `search.moduleIdList` | `"moduleIdList": [21, 22]` |
| 版本 | `search.versionIdList` | `"versionIdList": [31, 32]` |
| 创建时间 | `search.createTimeSection` | `"createTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 更新时间 | `search.updateTimeSection` | `"updateTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 上线时间 | `search.deployTimeSection` | `"deployTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 提测时间 | `search.presentTestTimeSection` | `"presentTestTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 完成时间 | `search.finishTimeSection` | `"finishTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 计划开始时间 | `search.planStartTimeSection` | `"planStartTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |
| 计划结束时间 | `search.planEndTimeSection` | `"planEndTimeSection": ["2026-05-08 00:00:00", "2026-05-14 23:59:59"]` |

注意：

1. `cardTypes` 使用通用映射：需求 `3`，任务 `4`，缺陷 `5`。
2. 时间区间统一传 `[开始时间, 结束时间]`，时间字符串建议精确到秒。
3. 如果只知道"最近一周""本周"等自然语言时间，先换算成明确日期区间再传入。
4. 不确定枚举 ID 时，先查迭代、标签、状态或同敏捷组历史事项，不要臆造 ID。
5. 如果工具 schema 暂未显式列出某个筛选字段，只要 MCP 支持透传，仍可放进 `search`。

常见缩小范围维度：

- 敏捷组
- 迭代
- 事项类型
- 状态
- 时间范围
- 负责人
- 创建人

## `list_issue_tags`

- 用途：查询敏捷事项可用标签下拉
- 典型场景：
  - "按标签筛任务"
  - "标签下拉里有什么"
  - "某个标签对应哪个 id"
- 返回结果可用于构造 `list_issues.search.tagIdList`

## `list_select_options`

- 用途：批量查询下拉选项（枚举值）配置
- 典型场景：
  - **事项筛选**：按发现方式、缺陷类型、发现环境、发现版本、解决结果等全局字段构造 `list_issues.search` 条件
  - **创建/更新事项**：确认缺陷类型、发现方式等枚举的可选值及 `id`
  - **批量拉取**：一次获取多个字段的枚举列表；`selectKey` 不传则返回该 `projectId` 下全部选项
- 参数：
  - `projectId`（必填）：传 `0` 获取**全局**选项（用于 `list_issues` 筛选）；传具体敏捷组 ID 获取该组配置（用于创建/更新或组内枚举核对）
  - `selectKey`（可选）：选项查询条目列表，格式 `[{"name": "<展示名或分类名>", "key": "<选项 key>"}]`；不传则返回所有选项
- 返回：数组，每个元素包含 `key`、`name`、`optionList`；`optionList` 中每项含 `id`、`value`、`langName` 等；筛选与写入时以 `id` 为准
- **全局下拉选项筛选前必须调用此接口**（`projectId` 传 0），从 `optionList` 匹配选项 `value` 得到 `id`，再构造 `search.bugFindMethod` 等条件；禁止猜测或硬编码选项 ID

### 常用 selectKey 参考

| name | key | 说明 |
| --- | --- | --- |
| `resolutionList` | `resolution` | 解决方案（Fixed / Won't Fix / Duplicate 等） |
| `bugTypeList` | `bug_type` | 缺陷类型（后端编码问题 / 前端编码问题 / 兼容性 等） |
| `bugFindMethodList` | `bug_find_method` | 缺陷发现方式（手工 / 自动化 / 监控 / 工单 等） |
| `bugFindEnvList` | `bug_find_env` | 缺陷发现环境（feature / sit / stable / beta / prod 等） |
| `bugVersionList` | `bug_version` | 缺陷版本（本次迭代 / 历史遗留 / 近期迭代） |
| `bugFindedProcessList` | `bug_finded_process` | 发现阶段（新功能测试 / 回归测试 / 预发验证 等） |
| `bugServiceTypeList` | `bug_service_type` | 服务端类型（前端 / 中间件 / 后端） |
| `reqTypeList` | `requirement_type` | 需求类型（产品功能 / 技术债优化 / 其它事务 等） |
| `taskTypeList` | `task_type` | 任务类型（同需求类型） |
| `affectUser` | `affectUser` | 是否影响用户（是 / 否） |
| `businessMonitor` | `businessMonitor` | 是否业务监控（是 / 否） |

`name` 可用上表分类名，也可用中文展示名（如 `"发现方式"`），`key` 必须与上表一致。

### 全局下拉选项筛选示例

用户要求筛选「发现方式=工单」的缺陷：

1. 调用 `list_select_options`，`projectId` 传 `0`，`selectKey` 传 `[{"name": "发现方式", "key": "bug_find_method"}]`
2. 在返回的 `optionList` 中找到 `value` 为「工单」的项，取其 `id`（如 `16634`）
3. 构造 `search.bugFindMethod = 16634`，再调用 `list_issues`

### 敏捷组枚举查询示例

```typescript
// 查询缺陷相关枚举（创建/更新前核对）
list_select_options({
  projectId: 37,
  selectKey: [
    { name: "bugTypeList", key: "bug_type" },
    { name: "bugFindMethodList", key: "bug_find_method" },
    { name: "bugFindEnvList", key: "bug_find_env" }
  ]
})

// 查询该敏捷组全部枚举
list_select_options({ projectId: 37 })
```

返回示例：

```json
[
  {
    "key": "bug_type",
    "name": "bugTypeList",
    "optionList": [
      { "id": 773, "value": "后端编码问题", "langName": "backendCoding" },
      { "id": 774, "value": "前端编码问题", "langName": "frontendCode" }
    ]
  }
]
```

**错误做法：**

- 直接猜测 `id`（如把「工单」当成 `1`）
- 硬编码选项映射
- 不调用 `list_select_options` 就把用户给的选项名称写进 `search` 或 `fields`

## `list_issue_custom_properties`

- 用途：查询敏捷组的事项自定义字段配置（如业务分类、Release、是否已自动化等）
- 先用它确认：
  - 字段 id
  - 字段名称
  - 字段类型
  - 可选项 logoId / name
- 自定义字段在 `create_issue` / `update_issue` 中优先放进 `customData`
- **自定义字段筛选前必须调用此接口，从 `options` 中匹配选项名称得到 `logoId`，再构造筛选条件**
- 如果用户给的是字段中文名，先从这里找到对应 id，再构造 `customData`

### 自定义字段筛选示例

用户要求筛选"业务分类=多边形建模"的任务，执行步骤：

1. 调用 `list_issue_custom_properties` 获取该敏捷组的自定义字段配置
2. 从返回结果中找到 `name` 为"业务分类"的字段（id=72）
3. 在该字段的 `options` 中找到 `name` 为"多边形建模"的选项，获取其 `logoId`（如 "1"）
4. 构造 `customData`：`{ "72": "1" }`
5. 调用 `list_issues` 时传入该 `customData`

**错误做法：**
- 直接猜测 `logoId` 值（如 `"多边形建模" -> "1"`）
- 硬编码选项映射关系
- 不调用 `list_issue_custom_properties` 直接使用用户提供的选项名称

## `list_issue_global_properties`

- 用途：查询事项全局属性配置
- 典型场景：
  - 创建事项时报"以下属性不能为空"
  - 用户提到研发标识、全局属性
  - 需要确认是否要传 `saveGlobalPropertyValues`
- 这是配置查询工具，不直接写值；真正创建/更新时仍通过事项接口提交

## `get_issue_detail`

- 只允许 `issueId` / `issueKey` 二选一
- 返回结果中的 `cardType` 是该事项后续评论、动态、工作日志等写操作的权威值
- 只要后续调用依赖 `cardType`，就应复用这里的值，不能自行猜测或改写

## 事项关联信息

### `list_issue_links`

- 用途：查询事项详情页"其他信息"中的关联敏捷事项
- `issueId` / `issueKey` 只能二选一
- 如果用户问"这个事项关联了哪些事项""存在关联里有哪些""其他信息页签的关联敏捷事项是什么"，优先用这个 tool
- 返回空数组表示当前未关联敏捷事项，不算异常

### `get_issue_change_set`

- 用途：查询事项关联的代码变更、配置变更等变更集合
- `issueId` / `issueKey` 只能二选一
- 需要看真实变更信息时，优先用这个 tool，不要从动态记录里猜
- 如果需要包含子事项变更，可显式传 `subIssue`

### `list_issue_confluence_pages`

- 用途：查询事项关联的 Confluence 文档
- `issueId` / `issueKey` 只能二选一
- 返回空数组表示当前未关联文档，不算异常

### `list_issue_test_plans`

- 用途：查询事项关联的测试计划
- `issueId` / `issueKey` 只能二选一
- 如果用户问"这个事项挂了哪些测试计划"，优先用这个 tool

### `list_issue_test_orders`

- 用途：查询事项关联的提测单
- `issueId` / `issueKey` 只能二选一
- 返回空数组表示当前未关联提测单，不算异常

## `create_issue`

如果用户要求"与前端行为尽量一致"，或你需要读取 `REQ_FIELDV2 / TASK_FIELDV2 / BUG_FIELDV2 / ISSUE_CONFIG` 这类同源配置，请结合
[frontend-config-sync.md](./frontend-config-sync.md)
一起执行。

### 前端同源常用映射

以下映射来自前端常量，可直接作为通用默认认知使用：

#### IssueTypeMap

- `需求` -> `cardType=3`
- `任务` -> `cardType=4`
- `缺陷` -> `cardType=5`

#### PriorityId

- `P0` / `紧急` -> `priorityId=11`
- `P1` / `高` -> `priorityId=12`
- `P2` / `中` -> `priorityId=13`
- `P3` / `低` -> `priorityId=14`

使用约束：

1. 以上映射只适用于前端已固化的通用常量，不代表所有项目字段都能硬编码
2. `cardType` 和 `priorityId` 可直接按上表转换
3. 其他项目相关枚举值仍需优先查询真实配置或参考同敏捷组历史事项
4. `P0/P1/P2/P3` 转换后必须写入 `fields.priorityId`，不要写成 `fields.priority`、`fields.priorityid`，也不要放进 `customData`
5. 描述字段使用 `fields.desc`，不要写成 `fields.description`
6. `assignee`、`cc`、`tagIdList`、`moduleIdList`、`versionIdList` 等多值字段必须传数组；即使只有一个人，也要传 `["username"]`
7. `customData` 只允许放自定义字段，key 必须是数字字段 ID 或数字字符串；不要用中文展示名、英文别名或标准字段名作为 key

- 最少需要：
  - `projectId`
  - `cardType`
  - `name`
- 标准字段放进 `fields`
- 自定义字段放进 `customData`
- 如果字段是否自定义不明确，先 `list_issue_custom_properties`
- 如果怀疑有全局属性必填，先 `list_issue_global_properties`
- 描述富文本一律传 HTML
- 常用标准字段 key 必须使用后端真实 camelCase：`priorityId`、`iterationId`、`typeId`、`storyPoint`、`planWorkingHours`、`desc`
- 常见错误：`priority`、`priorityid`、`iterationid`、`sp`、`description` 都不是 `create_issue` 的标准字段 key
- `create_issue` 的"最少需要"只代表接口层最小参数，不代表业务上足够安全
- 同一个敏捷组里如果历史上存在额外必填字段、联动字段或前端渲染依赖字段，创建前必须先向用户确认这些值，或从用户明确给出的上下文中取得
- 禁止为了尽快创建事项而省略未知业务字段；拿不准时宁可先追问，也不要凭经验补默认值
- 如果用户只说"帮我提个 bug/任务"，但没有给出敏捷组必填信息，先收集必要字段后再创建
- 推荐顺序：
  1. 先确定 `projectId`、`cardType`、标题等基础信息
  2. 再查询同敏捷组、同事项类型、近期创建且状态正常的 `1-3` 个事项作为参考
  3. 从参考事项里只提取"有哪些字段经常出现、哪些枚举值在该组真实存在"，不要直接复制整个 payload
  4. 对缺失的业务必填项向用户补问，确认后再调用 `create_issue`
- 对新增和修改类型的操作都适用同一原则：
  - 先看同敏捷组、同事项类型、近期正常事项
  - 再决定本次允许填写哪些字段、哪些枚举值是可信的
  - 禁止脱离历史样本直接臆造值
- 结论：模板只适合沉淀"流程"和"要检查哪些字段"，不适合直接承载不同敏捷组的枚举值
- 结论：历史事项适合做"参考样本"，但不能直接当模板照抄，否则很容易带入无效枚举、脏标签或跨组字段
- 要尽量复刻前端创建校验，至少覆盖这些规则：
  - 标题必填，且长度不能超过 `128`
  - 前端按 `cardType` 使用不同字段配置；缺陷通常比需求/任务多出缺陷类型、发现方式、发现环境等必填项
  - 如果同敏捷组配置了某字段 `require=true`，skill 也必须把它当必填，不能跳过
  - 对缺陷创建，若前端要求关联事项，则 skill 也必须先让用户确认关联事项，不能默认留空
  - 对存在联动逻辑的字段，必须按当前用户输入实时判断是否转为必填，不能只看静态字段表

### 复刻前端创建校验的执行顺序

按前端 `IssueAdd.js` / `issueConfig.js` 的思路，创建需求、任务、缺陷时应尽量执行下面的顺序：

1. 先确定基础入参
   - `projectId`
   - `cardType`
   - `name`
   - 可能的上下文默认值，如 `iterationId`、`leader`、`parentId`

2. 读取当前敏捷组 + 当前 `cardType` 的字段配置
   - 前端实际使用的是该敏捷组的 `selectFieldV2` 配置，再经过 `parseIssueField` 处理
   - 如果当前环境拿不到这份运行时配置，不要假装自己已经完成前端同款校验；应先补问用户或暂停创建

3. 执行标题校验
   - `name` 不能为空
   - `name.length <= 128`

4. 执行事项类型特有校验
   - `cardType = 5`（缺陷）时：
     - 默认要按该组缺陷字段配置检查缺陷专属字段
     - 如果前端场景要求关联事项，则 `issueSelectIds` 不能为空
   - 非缺陷且存在关联创建语义时：
     - 若 `isRalt = true`，则 `relateType` 必填

5. 执行字段配置驱动的必填校验
   - 遍历当前 `selectField[cardType]`
   - 对每个 `require = true` 的字段：
     - 先取字段映射后的真实 key
     - 若当前值为空，则视为前端校验不通过
   - 字段名、展示名、真实 key 尽量与前端配置保持一致

6. 执行联动必填校验
   - 前端不是只看静态 `require=true`
   - 例如某些字段会因其他字段取值变化而临时变成必填
   - skill 也必须根据当前输入重新判断，不能只拿历史样本里的固定字段列表

7. 全部校验通过后，才允许调用 `create_issue`
   - 如果只能确认一部分字段，宁可先追问，也不要提交"可能能创建但不保证前端可用"的 payload

### 当前已知前端校验细节

- 默认字段配置：
  - 需求 / 任务：通常至少包含 `priorityId`
  - 缺陷：在需求 / 任务基础上，通常还要求 `typeId`、`bugFindMethod`、`bugFindEnv`
- 配置来源：
  - 前端会按敏捷组读取 `REQ_FIELDV2` / `TASK_FIELDV2` / `BUG_FIELDV2`
  - 若敏捷组有自定义配置，应以该配置覆盖默认字段表
- 继承型字段：
  - 前端会对 `priorityId`、`iterationId`、`subPriority`、`leader`、`tagIdList`、`moduleIdList` 等字段做继承/默认值处理
  - 继承逻辑只适用于用户明确处于"从父事项/上下文创建"的场景，不能在普通新建时擅自套用

## `update_issue`

- 标准字段放进 `fields`
- 自定义字段放进 `customData`
- 如果字段是否自定义不明确，先 `list_issue_custom_properties`
- 如果只是做状态流转，优先用 `transition_issue_status`

## 状态流转

### `list_issue_next_nodes`

- 查询当前状态可流转到哪些目标状态

### `get_issue_required_properties`

- 查询流转到目标状态时的附加字段要求

### `transition_issue_status`

- 流转事项状态
- 如果用户明确要在流转时登记工时，优先直接用这个工具

## 事项关联信息推荐顺序

1. 用户给了 `issueId` 或 `issueKey` 时，直接走对应专用 tool
2. 如果用户只给了事项标题或模糊描述，先 `list_issues` 缩小到具体事项
3. 关联敏捷事项、关联变更、Confluence、测试计划、提测单彼此独立，不要混用返回结构
4. 查询关联敏捷事项优先用 `list_issue_links`