# 检索反馈手册

只有在以下场景才需要打开本文件：

- 不确定该上报哪种 `feedbackType`
- 不确定要不要 / 怎么定位 `selectedDocIds`
- 想确认熔断、阈值等治理细节
- 想看一组完整的端到端反馈样例

> 如果你只是想知道"有这条命令"和"该填哪些核心字段"，看 [`SKILL.md`](../SKILL.md) 的"反馈留痕"小节就够了，不用打开本文件。

目录：

1. 命令与完整字段表
2. 反馈类型选择决策树
3. 定位 `docId` 的标准流程
4. 治理规则（熔断、阈值、留痕口径）
5. 类型分类速查
6. 常见反例
7. 端到端样例

## 1. 命令与完整字段表

```json
{ "command": "report-feedback", "args": { ... } }
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `feedbackType` | enum | 是 | `NO_ANSWER` / `WRONG_ANSWER` / `LOW_QUALITY` / `MISSING_KNOWLEDGE` / `BAD_RECALL` |
| `source` | enum | 是 | 固定 `AI` |
| `comment` | string | 强烈推荐 | 简短说明问题原因 |
| `selectedDocIds` | int[] | 见决策树 | 命中并被判定有问题的具体文档；除 `MISSING_KNOWLEDGE` 外都应尽量填写 |
| `expectedDocIds` | int[] | 推荐（`BAD_RECALL`） | 应该命中但未命中的文档 |
| `requestId` | string | 视场景 | 有真实检索请求时传；AI 自主发现缺口时不传 |
| `askText` | string | 推荐（缺口/错召回） | 用户问题原文，便于后续重放和聚类 |
| `rootNodeIds` | int[] | 推荐（缺口） | 用户问题命中的根节点范围 |

## 2. 反馈类型选择决策树

按下面的顺序自顶向下判断，命中即停：

```
1. 知识库里完全没有相关文档？
   └── 是 → MISSING_KNOWLEDGE（不传 selectedDocIds，但建议传 askText、rootNodeIds）

2. 找到了相关文档，但内容过期、错误、与事实不符？
   └── 是 → WRONG_ANSWER（必须传 selectedDocIds = 问题文档）

3. 找到了相关文档，内容大致正确但不完整、不清晰、容易误导？
   └── 是 → LOW_QUALITY（必须传 selectedDocIds = 问题文档）

4. 正确文档存在，但本次检索没有命中，或排序很低？
   └── 是 → BAD_RECALL（推荐同时传 selectedDocIds = 错误召回的、expectedDocIds = 应命中的）

5. 用户的问题是"我问了 X，结果系统什么都没答出来"，且
   还没确认知识库内容是否齐全？
   └── 是 → NO_ANSWER（要尽量在 comment 里写清原始问题）
```

**关键边界**：

- "知识库里没有" vs "知识库里有但没召回" → 前者 `MISSING_KNOWLEDGE`，后者 `BAD_RECALL`，**两者绝不可混用**。判断方式：先用 MySQL `documents` 在合适的根节点下按关键词查；找得到 → 不是 `MISSING_KNOWLEDGE`。
- "内容错误" vs "内容质量差" → 前者是事实/口径错（联系人离职、流程过时、数字不对），后者是表达问题（不完整、容易误读、缺关键步骤）。
- 若同一篇文档**既错又召回不出来**，按"内容错误"上报 `WRONG_ANSWER`，召回问题用 `comment` 补充说明，不要拆成两条反馈。

## 3. 定位 `docId` 的标准流程

用户指出某文档/页面/联系人/流程/口径有问题时，**先定位、再上报**：

1. 看用户线索粗细：
   - 给了文档 ID / 完整标题 / 唯一关键词 → 直接 `documents` 或 `sql-query` 命中
   - 只给了主题（"接口测试卡点"）→ 先 `roots` 锁范围，再用 `documents` 模糊查标题，必要时再查 `content`
   - 只给了页面截图 / 路径碎片 → 用 `mcp-know-search` 模拟一次检索，对照召回里的 `docId`
2. 确认正确：用 `document {"docId":...}` 拉权威原文，看是否真的对应用户描述的问题。
3. 上报：`report-feedback` 必须带 `selectedDocIds`，**不要只在 `comment` 里写文档标题**。

定位失败时的回退：

- **暂时**没法精确定位 → 在回复里**显式写出**"未定位到具体 docId"，并交代已查询的 `rootId` / 关键词 / 已命中候选文档；再问用户"是否就是这几篇之一"，**不要**为了凑反馈直接传 `MISSING_KNOWLEDGE`。
- 已确认知识库中没有任何相关文档（按主题在所有可访问 `rootId` 下都查过且无果）→ 这才允许不传 `selectedDocIds` 并上报 `MISSING_KNOWLEDGE`。

## 4. 治理规则

- **熔断**：同一 `docId` 最近 7 天内被 `WRONG_ANSWER` / `LOW_QUALITY` 累计 ≥ 3 次反馈后，会自动进入熔断状态，**不再参与后续召回**，直至文档被更新或运营手动恢复。
- **熔断后的反馈**：仍然可以继续上报（用于统计），但不会进一步影响召回；上报时仍按真实 `feedbackType` 处理。
- **`requestId` 留痕**：如果是基于一次真实检索请求触发的反馈（用户在搜索结果页点了"答非所问"），传 `requestId` 以便回溯当次检索上下文；AI 自主发现缺口（例如读完文档后判断内容过期）时不要传，避免污染请求侧统计。
- **`source` 固定 `AI`**：人工反馈走的是另一条入口；本技能下的反馈一律 `source: "AI"`。
- **不要重复上报**：同一篇文档、同一类问题、同一会话内不要重复 `report-feedback`；如果发现内容随后又出现新错误，应在 `comment` 中累计描述，而不是再发一条相同 `feedbackType` 的反馈。

## 5. 类型分类速查

| 场景 | 反馈类型 | 必填的 IDs |
|---|---|---|
| 完全没有相关文档 | `MISSING_KNOWLEDGE` | — |
| 文档存在，内容错误或过期 | `WRONG_ANSWER` | `selectedDocIds` |
| 文档存在，内容不完整、不清晰、容易误导 | `LOW_QUALITY` | `selectedDocIds` |
| 正确文档存在，但没召回或排序很低 | `BAD_RECALL` | `selectedDocIds`（错误召回的） + `expectedDocIds` |
| 系统对一次提问完全没出答案，知识完整性未知 | `NO_ANSWER` | 尽量在 `comment` 里给出原始问题 |

## 6. 常见反例

下面这几种写法都是**错误的**，不要复刻：

- **只在 `comment` 写标题，不传 `selectedDocIds`**
  ```json
  { "feedbackType": "WRONG_ANSWER", "comment": "《接口测试卡点找谁》联系人过期", "source": "AI" }
  ```
  应该先定位到 `docId`，再传 `selectedDocIds: [<docId>]`。

- **找到了文档却上报 `MISSING_KNOWLEDGE`**
  `MISSING_KNOWLEDGE` 仅用于"知识库里压根没有"，文档存在但内容旧/错应该用 `WRONG_ANSWER` 或 `LOW_QUALITY`。

- **只发现召回不命中就上报 `MISSING_KNOWLEDGE`**
  正确文档其实在 MySQL `documents` 里能查到，只是 PostgreSQL `knowledge` 没切片或排序低 → 这是 `BAD_RECALL`，不是知识缺失。

- **同一问题拆成多条反馈**
  比如把"内容错"和"召回也不命中"拆成 `WRONG_ANSWER` + `BAD_RECALL` 两条 → 主问题以 `WRONG_ANSWER` 上报，召回情况写进 `comment`。

- **复用旧 `requestId` 或随手编造**
  `requestId` 必须是当次真实检索的 ID，不要为了字段齐全瞎填。

## 7. 端到端样例

**A. 用户："`接口测试卡点找谁` 这篇文档里联系人写的还是离职的同事。"**

```bash
scripts/knowledge_api.sh roots
scripts/knowledge_api.sh sql-query '{"dbType":"mysql","sql":"SELECT d.id, d.title, d.nodeId, n.rootId, n.fullPath FROM documents d JOIN nodes n ON n.id=d.nodeId WHERE d.isDeleted=0 AND n.isDeleted=0 AND n.rootId IN (<root_id>) AND d.title LIKE \\'%接口测试卡点%\\' ORDER BY d.id DESC LIMIT 5"}'
scripts/knowledge_api.sh document '{"docId":<doc_id>}'
scripts/knowledge_api.sh report-feedback '{
  "feedbackType":"WRONG_ANSWER",
  "selectedDocIds":[<doc_id>],
  "comment":"联系人 张三 已于 2025-12 离职，当前实际联系人为 李四；正文需更新。",
  "askText":"接口测试卡点找谁",
  "source":"AI"
}'
```

**B. 用户："我搜 `灰度发布回滚`，结果给我返了个完全不相关的运维通知。"**

```bash
scripts/knowledge_api.sh mcp-know-search '{"uuid":"skill-debug-1714983400","ask":"灰度发布回滚","minScore":0.3}'
scripts/knowledge_api.sh sql-query '{"dbType":"mysql","sql":"SELECT d.id, d.title FROM documents d JOIN nodes n ON n.id=d.nodeId WHERE d.isDeleted=0 AND n.isDeleted=0 AND n.rootId IN (<root_id>) AND (d.title LIKE \\'%灰度%\\' OR d.title LIKE \\'%回滚%\\') ORDER BY d.id DESC LIMIT 10"}'
scripts/knowledge_api.sh report-feedback '{
  "feedbackType":"BAD_RECALL",
  "selectedDocIds":[<错误召回的docId>],
  "expectedDocIds":[<应命中的docId>],
  "comment":"语义检索把无关运维通知排在了《灰度发布回滚 SOP》之前。",
  "askText":"灰度发布回滚",
  "rootNodeIds":[<root_id>],
  "source":"AI"
}'
```

**C. AI 自主发现："文档里完全没有 `埋点字段对齐流程` 的内容。"**

先**穷尽**所有可访问根节点的检索：

```bash
scripts/knowledge_api.sh roots
scripts/knowledge_api.sh sql-query '{"dbType":"mysql","sql":"SELECT d.id, d.title FROM documents d JOIN nodes n ON n.id=d.nodeId WHERE d.isDeleted=0 AND n.isDeleted=0 AND n.rootId IN (<roots>) AND (d.title LIKE \\'%埋点%\\' OR d.content LIKE \\'%埋点字段对齐%\\') LIMIT 20"}'
```

确认无果后再上报：

```bash
scripts/knowledge_api.sh report-feedback '{
  "feedbackType":"MISSING_KNOWLEDGE",
  "comment":"在所有可访问根节点下未发现埋点字段对齐流程相关文档。",
  "askText":"埋点字段对齐流程",
  "rootNodeIds":[<root_ids>],
  "source":"AI"
}'
```
