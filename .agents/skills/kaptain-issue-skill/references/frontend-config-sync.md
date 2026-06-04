# 前端同源配置与扩展接口

这份文件专门放“为了尽量与前端行为一致，需要额外读取的前端同源配置或接口”。

设计目标：

- 不把这类内容散落在 `issues.md`、`common-rules.md` 各处
- 后续新增接口时有统一归档位置
- 区分“基础 MCP 工具流”和“为了贴近前端而补充的同源配置读取”

## 适用场景

当用户要求：

- 创建需求 / 任务 / 缺陷时尽量与前端校验一致
- 复刻前端的动态必填逻辑
- 复刻前端的默认值、模板值、字段联动
- 排查“前端能过，skill 不能过”或“skill 能创建，前端白屏/报错”这类问题

优先看这份文件。

## 使用原则

1. 先走 MCP 的标准事项工具流
   - 查询事项详情、评论、状态流转、工作日志等，优先用现有 MCP tool

2. 只有在“需要与前端同源配置保持一致”时，才额外读取这些配置接口
   - 例如创建事项前校验必填字段
   - 例如确认某个敏捷组下当前 `cardType` 的字段配置

3. 同源配置优先级高于经验规则
   - 如果同源配置和历史样本冲突，以同源配置为准
   - 如果同源配置和模板冲突，以同源配置为准

4. 如果拿不到同源配置
   - 明确告知“无法完成前端同款校验”
   - 先向用户补问，再决定是否继续
   - 不要把“经验上大概这样”说成“与前端一致”

## 当前已知可对齐的配置来源

这些信息来自前端代码，不一定已经全部通过 MCP 暴露。

前端实际访问的 Kaptain 域名是：

- `https://kaptain.qunhequnhe.com`

在 skill / 终端直调场景里，推荐统一使用：

- Header：`kaptain-token: <KAPTAIN_TOKEN>`

也就是：

- 域名用 Kaptain 线上域名
- 认证统一带 `kaptain-token`
- `curl`、MCP、自定义脚本都尽量走同一种认证方式

推荐不要在这份文档里继续强调浏览器 Cookie 链路，避免使用者误以为只能从浏览器里复制 Cookie。

## 实际接口

这些接口默认使用线上域名：

- `https://kaptain.qunhequnhe.com`

推荐认证 Header：

```http
kaptain-token: <KAPTAIN_TOKEN>
```

推荐做法：

- 先用 `kaptain-token` 调前端同源配置接口
- 再用返回配置做校验
- 最后再调用 MCP 的写操作工具

### 单个配置读取

- 接口：
  - `GET https://kaptain.qunhequnhe.com/api/custom/getConfig?projectId=<projectId>&name=<配置名>`
- 前端来源：
  - [custom.js](/Users/taole/gitlab/kaptain-frontend-layout/src/services/custom.js)
  - [issueConfig.js](/Users/taole/gitlab/kaptain-frontend-layout/src/models/issueConfig.js)
- 用途：
  - 读取单个敏捷组配置，例如 `ISSUE_CONFIG`

示例：

```bash
curl 'https://kaptain.qunhequnhe.com/api/custom/getConfig?projectId=37&name=ISSUE_CONFIG' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>'
```

### 批量配置读取

- 接口：
  - `POST https://kaptain.qunhequnhe.com/api/custom/config-list`
- 前端来源：
  - [custom.js](/Users/taole/gitlab/kaptain-frontend-layout/src/services/custom.js)
  - [issueConfig.js](/Users/taole/gitlab/kaptain-frontend-layout/src/models/issueConfig.js)
- 用途：
  - 一次性读取 `ISSUE_CONFIG`、`REQ_FIELDV2`、`TASK_FIELDV2`、`BUG_FIELDV2`

示例：

```bash
curl 'https://kaptain.qunhequnhe.com/api/custom/config-list' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>' \
  --data '{
    "projectId": 37,
    "selectKey": [
      { "name": "issueConfig", "key": "ISSUE_CONFIG" },
      { "name": 3, "key": "REQ_FIELDV2" },
      { "name": 4, "key": "TASK_FIELDV2" },
      { "name": 5, "key": "BUG_FIELDV2" }
    ]
  }'
```

### 事项模板读取

- 接口：
  - `GET https://kaptain.qunhequnhe.com/api/issue/template?cardType=<cardType>&projectId=<projectId>`
- 前端来源：
  - [issue.js](/Users/taole/gitlab/kaptain-frontend-layout/src/services/issue.js)
- 用途：
  - 读取个人模板 / 事项模板，补默认值
- 注意：
  - 模板不能替代必填校验

示例：

```bash
curl 'https://kaptain.qunhequnhe.com/api/issue/template?cardType=5&projectId=37' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>'
```

## 已验证示例

下面这些调用方式已在当前环境验证通过：

```bash
curl 'https://kaptain.qunhequnhe.com/api/custom/getConfig?projectId=37&name=ISSUE_CONFIG' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>'
```

```bash
curl 'https://kaptain.qunhequnhe.com/api/custom/config-list' \
  -X POST \
  -H 'Content-Type: application/json' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>' \
  --data '{
    "projectId": 37,
    "selectKey": [
      { "name": "issueConfig", "key": "ISSUE_CONFIG" },
      { "name": 3, "key": "REQ_FIELDV2" },
      { "name": 4, "key": "TASK_FIELDV2" },
      { "name": 5, "key": "BUG_FIELDV2" }
    ]
  }'
```

```bash
curl 'https://kaptain.qunhequnhe.com/api/issue/template?cardType=5&projectId=37' \
  -H 'kaptain-token: <KAPTAIN_TOKEN>'
```

## 当前已知配置 key

- `ISSUE_CONFIG`
  - 敏捷组级事项配置
  - 前端会读取后合并默认配置

- `REQ_FIELDV2`
  - 当前敏捷组的需求创建字段配置

- `TASK_FIELDV2`
  - 当前敏捷组的任务创建字段配置

- `BUG_FIELDV2`
  - 当前敏捷组的缺陷创建字段配置

- 个人模板 / 事项模板
  - 前端有 `getIssueTemplate(cardType, projectId)` 这类模板读取能力
  - 只适合作为默认值来源，不应覆盖真实必填校验

## 推荐调用方式

当你需要“尽量和前端一模一样”时，建议按这个顺序调：

1. 先调批量配置接口
   - 拿 `ISSUE_CONFIG`
   - 拿 `REQ_FIELDV2 / TASK_FIELDV2 / BUG_FIELDV2`

2. 如果用户明确要求带模板默认值，再调模板接口

3. 用返回的字段配置做校验后，再调用 MCP 的事项创建 / 更新工具

也就是说：

- 同源配置读取：可以直调 `curl`
- 事项写操作：仍优先走 MCP tool

这样最容易同时兼顾“和前端一致”与“写操作稳定”。

## 推荐接入顺序

当未来要继续增强“与前端几乎一模一样”的能力时，建议按下面顺序扩展：

1. 先补“读取当前敏捷组字段配置”
   - 目标：拿到 `REQ_FIELDV2 / TASK_FIELDV2 / BUG_FIELDV2`
   - 用于替代经验化的必填判断

2. 再补“读取事项全局配置”
   - 目标：拿到 `ISSUE_CONFIG`
   - 用于复刻字段联动、特殊必填、开关项

3. 最后再补“模板类接口”
   - 模板适合补默认值，不适合决定必填项

## 未来新增接口时怎么放

后续如果你要加更多前端同源接口，建议统一按下面格式追加到本文件，而不是散写到别的规则文件里：

### `<接口或配置名>`

- 用途：
- 来源：
  - 前端代码位置
  - 接口或配置 key
- 什么时候读取：
- 可以替代哪些经验规则：
- 失败时如何降级：

## 当前结论

- `issues.md` 负责“事项领域规则”
- `common-rules.md` 负责“全局底线规则”
- 本文件负责“前端同源配置 / 扩展接口”

以后如果继续补 `curl` 直调配置、模板接口、枚举接口，都优先放到这里维护。
