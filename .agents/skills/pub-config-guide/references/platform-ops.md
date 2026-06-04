# 平台侧操作参考

## 目录

- Tool 对照
- 创建配置包
- 创建和维护配置项
- 编辑配置数据
- 流转、发布和回滚

## Tool 对照

当前已确认可直接用于配置包链路的 `pub-mcp-server` tools：

- `config_search_by_keyword`
  - 用途：按关键词搜索配置包，先定位已有配置包
  - 入参：`keyword?: string`、`user?: string`
- `config_create_package`
  - 用途：创建配置包
  - 入参：`name: string`、`desc?: string`、`structureId?: string`、`user?: string`
- `config_update`
  - 用途：修改配置包元信息
  - 入参：`id: number | string`、`desc?: string`、`structureId?: string`、`configs?: string`、`version?: string`、`user?: string`
- `config_item_create`
  - 用途：创建配置项
  - 入参：`configId: number | string`、`name: string`、`type: number`、`desc?: string`、`user?: string`
  - 类型说明：`string -> 0`、`json -> 1`
- `config_data_update`
  - 用途：更新或恢复某环境的配置数据
  - 入参：`id: number | string`、`data?: string`、`stage?: "sit" | "prod_test" | "prod"`、`version?: string`、`user?: string`
- `config_data_pipe`
  - 用途：配置包数据环境流转
  - 入参：`configId: number | string`、`fromStage: "sit" | "prod_test" | "prod"`、`toStage: "sit" | "prod_test" | "prod"`、`issueKey?: string`、`user?: string`
  - 约束：目标环境是 `prod` 时，`issueKey` 必填
- `config_inject_package_to_app`
  - 用途：把配置包注入到应用，或从应用中移除
  - 入参：`action: "add" | "delete"`、`appName: string`、`issueKey: string`、`packages: string[]`、`user?: string`
  - 行为说明：`add` 时内置“可挂载范围校验”和“已在当前节点或父节点生效的包自动过滤”
- `config_injection_query`
  - 用途：查询应用当前已生效的配置包列表，主要用于查看现状和排查
  - 入参：`appName: string`、`user?: string`
  - 输出重点：`currentPackages`、`inheritedPackages`、`packages`
- `config_data_get_by_id`
  - 用途：按配置包 id / 名称和环境读取当前配置数据
  - 入参：`id: number | string`、`stage?: "sit" | "prod_test" | "prod"`、`version?: string`、`user?: string`
- `config_data_get_by_names`
  - 用途：按配置包名称批量读取某环境配置数据
  - 入参：`names: string[]`、`stage?: "sit" | "prod_test" | "prod"`、`user?: string`
- `config_delete`
  - 用途：删除配置包
  - 入参：`id: number | string`、`user?: string`

当前未发现独立的“删除配置项 / 修改配置项定义”专用 tool。遇到这些需求时：

- 先不要假设存在对应 tool。
- 先说明当前已知 MCP 能力边界。
- 再结合平台能力选择替代路径。

## 创建配置包

优先确认：

- 配置包类别：应用配置包 / 公共配置包
- 挂载节点或所属应用
- 配置包名称
- 配置包描述

执行规则：

- 使用 `config_create_package`。
- 配置包名称全局唯一，且创建后不可修改。
- 如果是应用配置包，传 `structureId`。
- 如果是公共配置包，不传 `structureId`。

建议入参：

```json
{
  "name": "配置包名称",
  "desc": "配置包描述",
  "structureId": "应用配置包时传，公共配置包不传",
  "user": "当前用户"
}
```

创建后至少输出：

- 配置包名称
- 配置包类型
- 所属节点 / 应用
- 创建结果
- 后续推荐创建的配置项列表

## 创建和维护配置项

每个配置项至少补齐：

- 名称
- 类型：`string` 或 `json`
- 用途说明
- 默认值策略
- 影响范围

执行规则：

- 创建配置项使用 `config_item_create`。
- 配置项名称在同一个配置包内唯一。
- 配置项名称和类型创建后不可修改。
- 若要保存数字、对象或数组，使用 `json` 类型。
- 目前只确认了“创建配置项”能力；未确认“修改配置项定义 / 删除配置项”能力时，不要编造调用方式。

建议入参：

```json
{
  "configId": "配置包 id 或名称",
  "name": "配置项名称",
  "type": 0,
  "desc": "配置项描述",
  "user": "当前用户"
}
```

类型映射：

- `string` -> `0`
- `json` -> `1`

推荐记录结构：

```md
- 名称：
- 类型：
- 用途：
- 默认值：
- 生效环境：
- 本地读取位置：
- 验证方式：
```

## 编辑配置数据

配置数据分 `sit`、`prod_test`、`prod` 三份独立数据。

执行规则：

- 使用 `config_data_update` 编辑配置数据。
- 最好先读取当前环境的完整配置数据，再基于原数据组装新的完整 payload。
- `json` 类型必须保证 JSON 合法。
- `string` 类型若输入空值并保存，该环境数据中将不存在该项。
- 保存后通常约 `1s` 生效，特殊情况约 `10s`；保存后应主动刷新确认。

建议入参：

```json
{
  "id": "配置包 id 或名称",
  "data": "{\"key\":\"value\"}",
  "stage": "sit",
  "user": "当前用户"
}
```

数据约束：

- `data` 是字符串化后的 JSON。
- JSON 第一层字段必须与配置项名称一致。
- 提交给 tool 的最好是该环境下完整的目标数据，而不是局部数据。

组装数据的推荐方式：

1. 先获取当前环境现有配置数据。
2. 基于现有数据合并本次改动。
3. 再把合并后的完整 JSON 传给 `config_data_update`。

当前能力说明：

- 已有 `config_data_get_by_id` 和 `config_data_get_by_names` 可用于“先读后写”。
- 优先先读当前环境完整数据，再合并变更后提交。
- 只有在读取 tool 暂时不可用或调用失败时，才退回到让用户提供当前配置数据或去平台页面确认。

每次修改数据时都要说明：

- 修改了哪个配置包
- 修改了哪个环境
- 修改了哪些配置项
- 预期影响哪个页面或微应用
- 如何验证生效

## 流转、发布和回滚

环境流转规则：

- 只能从上一个环境流转到下一个环境，不能跨环境流转。
- `sit -> prod_test`
- `prod_test -> prod`
- `prod` 不能直接编辑，必须从 `prod_test` 流转。

执行规则：

- 使用 `config_data_pipe` 执行配置包数据流转。
- 用户要求“发布到线上”时，本质上是把配置数据推进到 `prod`。
- 需要回滚时，优先通过平台历史记录选择版本回滚，并查看 diff 后再执行。
- 目标环境是 `prod` 时，`issueKey` 必填。
- 不要把应用资源流转 `app_pipe` 错用于配置包数据流转。

建议入参：

```json
{
  "configId": "配置包 id 或名称",
  "fromStage": "prod_test",
  "toStage": "prod",
  "issueKey": "目标环境是 prod 时必传，优先从当前分支提取",
  "user": "当前用户"
}
```

每次发布或流转后，至少输出：

- 流转前环境
- 流转后环境
- 涉及的配置包
- 是否需要额外审批或权限
- 验证入口
