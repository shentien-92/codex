# 用户、敏捷组与迭代

## `get_current_user`

- 用途：获取当前登录用户
- 当用户说“我是谁”“当前登录人是谁”时使用

## `get_my_projects`

- 用途：获取当前登录用户相关的敏捷组
- 不要用 `search_projects` 推导“我的敏捷组”

## `search_projects`

- 用途：搜索全量敏捷组
- 支持：
  - `name`
  - `businessId`

## `list_businesses`

- 用途：获取业务分类列表
- 当用户需要先查业务分类再查敏捷组时使用

## `get_my_work_matters`

- 用途：获取工作台事项
- 返回中重点关注：
  - `listAssignToMe`
  - `listCcToMe`
  - `listCreateByMe`

## `list_iterations`

- 用途：按敏捷组查询迭代列表
- 事项筛选如果以迭代为维度，优先先查这个工具
- 如果用户问“当前迭代”：
  - 先调用 `list_iterations`
  - 再按 `startTime <= now <= endTime` 从返回结果里筛选当前迭代

## `get_iteration_detail`

- 用途：查询单个迭代详情

## `get_last_iteration`

- 用途：查询某个敏捷组最近一个迭代
- 适合“最近迭代”“上一个迭代”这类问题

## `create_iteration`

- 用途：创建新迭代
- 最少需要：
  - `projectId`
  - `fields.name`
- 常见字段放进 `fields`：
  - `name`
  - `assignee`
  - `startTime`
  - `endTime`
  - `remarks`
- `startTime` / `endTime` 推荐直接传 ISO 时间
- 如果传 `"YYYY-MM-DD HH:mm:ss"` 或时间戳，MCP 会自动归一化为 ISO 时间再发请求
- 创建后优先再用 `list_iterations` 或 `get_iteration_detail` 回查结果

## `update_iteration`

- 用途：更新已有迭代
- 需要：
  - `projectId`
  - `fields.id` 或 `fields.iterationId`
- 其他可更新字段仍放进 `fields`
- `startTime` / `endTime` 规则与 `create_iteration` 一致
- 如果只是改备注、名称、负责人，优先最小字段更新

## 迭代场景推荐顺序

1. 先用 `list_iterations` 查敏捷组的迭代列表
2. 如果是“当前迭代”，按 `startTime <= now <= endTime` 找到目标迭代
3. 把 `iterationId` 或 `iterationIds` 放进 `list_issues.search`

## 迭代写操作推荐顺序

1. 创建前先确认目标 `projectId`
2. 时间字段优先传 ISO 时间，或让 MCP 自动做归一化
3. 创建或更新后，优先立即回查，避免只看写接口返回
