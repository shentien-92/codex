---
name: knowledge-manager
description: "操作 Gaea/Librify 知识库的统一入口。当需要查询知识库节点/目录树/文档原文、排查 PostgreSQL 召回切片、维护节点和文档（增/改/删/移动/幂等同步），或上报检索反馈时使用。所有调用都通过 /know/skillApi/cli/exec 网关，禁止直连业务接口或数据库。"
---

# Gaea 知识库管理

本技能是 Gaea/Librify 知识库的统一操作手册，覆盖三类任务：

- **结构**：根节点、节点、路径、目录树（MySQL `nodes`）
- **内容**：文档元数据、文档原文、召回切片（MySQL `documents` / PostgreSQL `knowledge`）
- **维护**：节点与文档的增/改/移动/删除/幂等同步、检索反馈

所有操作都走统一网关。**不要**直接访问数据库，**不要**绕过网关调用业务内部接口。

```http
POST {GAEA_BASE_URL}/know/skillApi/cli/exec
Content-Type: application/json; charset=utf-8
librify-token: {token}

{ "command": "<command>", "args": { ... } }
```

返回结构统一为 `ApiResponse`：`{"code":0,"message":"成功","data":...}`。`**code == 0` 视为成功，其它值一律按失败处理**。

## 鉴权

`POST /know/skillApi/cli/exec` 与 `GET /know/skillApi/cli/commands` 都必须携带 HTTP 头 `librify-token`。

Token 解析顺序（脚本和示例都遵循）：

1. 环境变量 `LIBRIFY_TOKEN`（CI / 临时覆盖）
2. 技能根目录下的 `librify-token` 文件（本地常驻，单独一行，已被 `.gitignore` 忽略）

**鉴权失败时**（`code != 0` 且 `message` 提示无 token / token 失效），必须明确告知用户：

- 获取或刷新 Token：[https://librify.qunhequnhe.com/#/tool/knowledgeManagerSkill](https://librify.qunhequnhe.com/#/tool/knowledgeManagerSkill)
- 修复方式：写入技能根目录 `librify-token` 文件，或临时设置 `LIBRIFY_TOKEN`
- 这是**鉴权阻塞**，不是"没查到数据"，不要继续重试或自行降级

## 运行环境

- 唯一必需依赖：`curl`（macOS / Linux / WSL / Git Bash 均可）
- 平台地址环境变量：`GAEA_BASE_URL`，默认 `https://gaea-beta.qunhequnhe.com`
- 可选薄封装：`scripts/knowledge_api.sh <command> [json_args | @args.json | -]`
  - 脚本只负责拼 JSON、补 token 头；SQL 校验、命令校验、权限、审计都由后端负责。

## 决策树：先分类，再选命令

收到请求时，**先判断属于哪一类**，再选命令；这一节是优先级最高的工作流。

| 请求类型              | 事实来源                   | 首选命令                                |
| ----------------- | ---------------------- | ----------------------------------- |
| 结构查询（根/子/树/路径）    | MySQL `nodes`          | `roots`、`node`、`nodes`、`nodes-tree` |
| 原文查询（标题/正文/作者/来源） | MySQL `documents`      | `document`、`documents`              |
| 召回排查（切片/向量/覆盖）    | PostgreSQL `knowledge` | `sql-query` (`dbType:postgresql`)   |
| 维护操作（建/改/移/删/同步）  | 专用写命令                  | `create-node`、`upsert-doc` 等        |
| 反馈留痕              | 反馈命令                   | `report-feedback`                   |

默认路径：

1. **范围不明确 → 先 `roots`**，并使用其返回的实时 `rootId`，不要复用旧示例里的 ID。
2. **读操作优先用包装命令**（`node` / `nodes` / `nodes-tree` / `document` / `documents`）。
3. 包装命令表达不了，再退回 `sql-query`（须满足下文 SQL 硬约束）。
4. 排查"文档存在但搜不到"时，**先 MySQL 定位 `docId`，再 PostgreSQL 查切片覆盖**。
5. 写操作和反馈**必须**用专用命令，不要改写成 SQL。

### 典型工作流示例

**A. 找一篇关于"接口测试卡点"的文档并读取原文**

1. `roots` → 拿到可访问的 `rootId`
2. `documents` 或 `sql-query`（`documents` 按标题/正文模糊查）→ 拿到 `docId`
3. `document {"docId":...}` → 读权威原文

**B. 用户反馈"某接口测试文档已过期，联系人写错了"**

1. `documents` / `sql-query` 定位具体 `docId`（**必须定位到**，否则在回复中说明范围）
2. `report-feedback {"feedbackType":"WRONG_ANSWER","selectedDocIds":[<docId>],"comment":"..."}`
3. 输出 `feedbackId`、`feedbackType`、`selectedDocIds`

**C. 排查"知识库里有文档但用户搜不到"**

1. MySQL：按 `rootId` + 关键词在 `documents` 中确认源文档存在 → 取 `docId`
2. PostgreSQL：`SELECT ... FROM knowledge WHERE docid IN (<doc_id>) ...` 查切片
3. 若源文档存在但 `knowledge` 没有切片，按 `BAD_RECALL` 上报，并把应命中文档放入 `expectedDocIds`

**D. 把一篇文档幂等同步到指定节点**

- 直接 `upsert-doc {"nodeId":...,"title":"...","content":"..."}`（按"节点 + 标题"定位，存在则更新，不存在则新建）

## 命令地图

所有命令统一结构：

```json
{ "command": "<command>", "args": { ... } }
```

### 范围发现

| 命令         | 参数                      | 用途                   |
| ---------- | ----------------------- | -------------------- |
| `roots`    | `{}`                    | 列出当前 Token 可访问的内部根节点 |
| `commands` | — (`GET /cli/commands`) | 列出网关注册的全部命令；用于自检和探索  |

`roots` 的 `access` 字段：

- `read-write`：允许查询和维护操作
- `read-only`：仅允许查询

任何涉及 `rootId` / `rootnodeid` 的 SQL，都必须使用最新 `roots` 返回的 ID（用户已明确给出 ID 时除外）。

### 读包装命令（MySQL，自动过滤已删除）

| 命令           | 参数                                 | 用途                            |
| ------------ | ---------------------------------- | ----------------------------- |
| `node`       | `{"nodeId":123}`                   | 单个节点详情                        |
| `nodes`      | `{"parentId":123}`                 | 直接子节点列表                       |
| `nodes-tree` | `{"parentId":123}`                 | 递归子树                          |
| `document`   | `{"docId":123}`                    | 单篇文档（含正文）                     |
| `documents`  | `{"nodeId":123,"recursive":false}` | 节点下的文档；`recursive=true` 含子孙节点 |

### SQL 查询

| 命令          | 参数                                           | 用途                     |
| ----------- | -------------------------------------------- | ---------------------- |
| `sql-query` | `{"dbType":"mysql","sql":"SELECT ..."}`      | 只读 MySQL 查询（结构 / 原文）   |
| `sql-query` | `{"dbType":"postgresql","sql":"SELECT ..."}` | 只读 PostgreSQL 查询（召回切片） |

**硬约束**：

- 单条语句；只允许 `SELECT` 或 `WITH`
- 必须带 `LIMIT`（默认 `LIMIT 50`）
- 禁止 `INSERT` / `UPDATE` / `DELETE` / `REPLACE` / `ALTER` / `DROP` / `TRUNCATE` / `CREATE` / `FOR UPDATE`
- 禁止无 `WHERE` 的全表扫描
- MySQL 查 `nodes` / `documents` **每张表都必须** `isDeleted = 0`
- 涉及范围的查询必须使用 `roots` 实时返回的根节点

**实践约束**：

- 优先精确 ID 查询，再模糊搜索
- 读 `content` 等大文本前，先用 `rootId` / `rootnodeid` 缩小范围
- `knowledge.content` **不是**权威文档原文；权威原文看 `documents.content`
- 显式列字段，不要 `SELECT `*

不确定查哪张表 → 先读 [references/knowledge-schema.md](references/knowledge-schema.md)；要写自定义 SQL → 先读 [references/sql-playbook.md](references/sql-playbook.md)。

### 维护命令（写操作禁用 SQL，必须用专用命令）

| 命令                 | 参数                                                          | 用途                               |
| ------------------ | ----------------------------------------------------------- | -------------------------------- |
| `create-node`      | `{"parentId":123,"name":"新节点"}`                             | 在父节点下新建一个子节点                     |
| `create-nodes`     | `{"parentId":123,"names":["A","B"]}`                        | 批量新建同级子节点                        |
| `rename-node`      | `{"nodeId":123,"name":"新名称"}`                               | 仅改名；不能重命名可写白名单根节点                |
| `move-node`        | `{"nodeId":123,"targetParentId":456}`                       | 仅改父节点；拒绝循环移动；自动刷新派生字段与文档索引       |
| `delete-nodes`     | `{"ids":[123,456]}`                                         | 批量软删节点                           |
| `insert-doc`       | `{"nodeId":123,"title":"...","content":"..."}`              | 明确新增一篇文档（不做去重）                   |
| `rename-doc`       | `{"docId":123,"title":"新标题"}`                               | 仅改标题；仅 Repo Wiki 文档；拒绝同节点重名      |
| `update-doc`       | `{"docId":123,"title":"...","content":"...","nodeId"?:456}` | 按 `docId` 更新；提供 `nodeId` 时同时移动节点 |
| `upsert-doc`       | `{"nodeId":123,"title":"...","content":"..."}`              | **按"节点 + 标题"幂等同步**：存在则更新，不存在则新建  |
| `delete-documents` | `{"ids":[123,456]}`                                         | 批量软删文档                           |

**写命令选择规则**：

- 已知 `docId`、要改标题/正文/节点 → `update-doc`
- 知道目标"节点 + 标题"，希望"存在则更新、不存在则创建" → `upsert-doc`（**首选**用于幂等同步）
- 明确要新建一篇（即使同名也另建） → `insert-doc`
- 仅改标题且不动正文 → `rename-doc`

后端保证：

- 写操作受 Token 授权的可写根节点和节点边界限制
- 所有变更由服务端审计

### 检索辅助（仅在排查语义检索链路或准备反馈时使用）

| 命令                         | 参数                                                                | 用途          |
| -------------------------- | ----------------------------------------------------------------- | ----------- |
| `mcp-node-tree`            | `{"rootNodeId":123}`                                              | 拉取召回侧看到的节点树 |
| `mcp-know-search`          | `{"uuid":"<会话ID>","ask":"问题","minScore":0.5}`                     | 模拟一次语义检索    |
| `mcp-know-search-by-roots` | `{"uuid":"<会话ID>","ask":"问题","rootNodeIds":[123],"minScore":0.5}` | 限定根节点的语义检索  |

`uuid` 字段：当前会话/请求的标识字符串，用于服务端打点和限流。**没有真实业务 ID 时，传一个固定可识别的字符串**（例如 `skill-debug-<时间戳>`）即可，不要伪造成线上用户 ID。

### 反馈留痕

| 命令                | 参数                                                                                 |
| ----------------- | ---------------------------------------------------------------------------------- |
| `report-feedback` | `{"feedbackType":"...","selectedDocIds":[...],"comment":"...","source":"AI", ...}` |

**字段约定**：

- `feedbackType`：`NO_ANSWER` / `WRONG_ANSWER` / `LOW_QUALITY` / `MISSING_KNOWLEDGE` / `BAD_RECALL`
- `requestId`：有真实检索请求时传；AI 自主发现缺口时不传
- `comment`：简短说明原因
- `askText`：知识缺口场景推荐填写
- `rootNodeIds`：知识缺口场景推荐填写
- `selectedDocIds`：内容错误或质量较差时**必须**尽量填写，表示具体问题文档
- `expectedDocIds`：召回质量反馈时推荐填写，表示应该命中的文档
- `source`：固定 `AI`

**反馈治理规则**：

- 只有确认知识库**没有**相关文档时，才用 `MISSING_KNOWLEDGE`
- 已定位到相关文档但内容过期/错误/矛盾 → `WRONG_ANSWER` 或 `LOW_QUALITY`，并把问题文档放进 `selectedDocIds`
- 正确文档存在但召回未命中或排序很低 → `BAD_RECALL`，同时填错误召回的 `selectedDocIds` 和应命中的 `expectedDocIds`
- 同一文档最近 7 天内被 `WRONG_ANSWER` / `LOW_QUALITY` 反馈达到 3 次后，会自动**熔断**，不再参与检索召回

**执行反馈前的定位要求**：

- 用户指出"某篇文档/页面/联系人/流程/口径有问题"时，必须先用 `documents` / `document` / `mcp-know-search` 或必要的 `sql-query` 定位到具体 `docId`
- 找到问题文档后，`report-feedback` **必须**传 `selectedDocIds`；不要只在 `comment` 写文档标题
- 只能定位到节点/主题、暂时无法定位具体文档时，要在回复里**显式说明**"未定位到具体 docId"，并写清已查范围
- 只有确认没有相关文档时，才允许不传 `selectedDocIds` 并上报 `MISSING_KNOWLEDGE`

**类型分类速查**：

| 场景                   | 反馈类型                |
| -------------------- | ------------------- |
| 完全没有相关文档             | `MISSING_KNOWLEDGE` |
| 文档存在，但内容错误或过期        | `WRONG_ANSWER`      |
| 文档存在，但内容不完整、不清晰、容易误导 | `LOW_QUALITY`       |
| 正确文档存在，但没有召回或排序很低    | `BAD_RECALL`        |

## 调用示例

技能根目录下，三种等价方式：

**1. 直接 curl（读 Token 文件）**

```bash
curl -sS -X POST "${GAEA_BASE_URL:-https://gaea-beta.qunhequnhe.com}/know/skillApi/cli/exec" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "librify-token: $(head -n 1 librify-token | tr -d '\r')" \
  -d '{"command":"roots","args":{}}'
```

**2. 直接 curl（环境变量 Token）**

```bash
curl -sS -X POST "${GAEA_BASE_URL%/}/know/skillApi/cli/exec" \
  -H "Content-Type: application/json; charset=utf-8" \
  -H "librify-token: $LIBRIFY_TOKEN" \
  -d '{"command":"nodes","args":{"parentId":123}}'
```

**3. 薄封装脚本（推荐）**

```bash
scripts/knowledge_api.sh roots
scripts/knowledge_api.sh nodes '{"parentId":123}'
scripts/knowledge_api.sh documents '{"nodeId":123,"recursive":true}'
scripts/knowledge_api.sh rename-node '{"nodeId":123,"name":"新名称"}'
scripts/knowledge_api.sh move-node '{"nodeId":123,"targetParentId":456}'
scripts/knowledge_api.sh upsert-doc @/tmp/upsert.json
echo '{"dbType":"mysql","sql":"SELECT id, name FROM nodes WHERE isDeleted = 0 LIMIT 10"}' \
  | scripts/knowledge_api.sh sql-query -
scripts/knowledge_api.sh report-feedback '{"feedbackType":"LOW_QUALITY","selectedDocIds":[123],"comment":"联系人已离职但文档未更新","askText":"接口测试卡点找谁","source":"AI"}'
scripts/knowledge_api.sh commands
```

## 错误处理

| 现象                                        | 含义          | 行动                                                 |
| ----------------------------------------- | ----------- | -------------------------------------------------- |
| HTTP 200 + `code == 0`                    | 成功          | 按 `data` 解析                                        |
| HTTP 200 + `code != 0`                    | 业务失败        | **不要重试相同请求**；阅读 `message`，按下表对应处理                  |
| `message` 含 `librify-token` / 鉴权关键字       | Token 缺失或失效 | 走"鉴权失败"流程，让用户更新 Token                              |
| `message` 含 `权限` / `不在可写白名单`              | 权限不足        | 改用读命令，或提示用户该范围只读                                   |
| `message` 含 `SQL` / `LIMIT` / `isDeleted` | SQL 校验未通过   | 修正 SQL 直至满足硬约束；不要绕过                                |
| HTTP 4xx / 5xx 或网络超时                      | 网关或网络异常     | 最多重试 1 次；连续失败时停下来报告，**不要**自行切换到直连数据库或业务接口          |
| `code != 0` 但语义不明                         | 后端边界条件      | 把 `command`、`args` 摘要、`message` 完整回报给用户，请用户确认是否换路径 |

底线：**网关返回的所有失败都不是"没查到数据"**，必须用 `message` 而不是空结果向用户解释。

## 输出规范

每次执行后，至少说明：

- 实际调用的 `command`
- 实际范围：`rootId` / `nodeId` / `docId` / 关键词
- 来自 `roots` 的范围权限（如本次涉及）
- 返回数量或是否命中
- 关键结论
- 两阶段排查时，分别说明每一阶段查了什么
- 执行反馈时：`feedbackId`、`feedbackType`、是否为缺口上报、`selectedDocIds`、`expectedDocIds`

不要把示例或历史快照当作实时结果。命令失败时，说明 `message` 中的失败原因和下一步动作。