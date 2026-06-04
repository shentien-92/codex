# SQL 查询手册

只有当包装命令无法表达用户诉求时，才打开本文件。

写 SQL 前先做三件事：

1. 通过 [knowledge-schema.md](knowledge-schema.md) 确认应该查哪张表。
2. 如果查询需要根节点范围，先执行 `roots`，只使用实时返回的 root ID。
3. 保持 SQL 只读、带范围、带 `LIMIT`。

本文占位符：

- `<root_id>`：来自最新 `roots`，或用户明确提供的 root ID
- `<node_id>`：来自 `node`、`nodes` 或用户明确提供的 node ID
- `<doc_id>`：来自 `document`、`documents` 或用户明确提供的 doc ID
- `<keyword>`：用户提供的关键词；发送到网关时由 JSON 字符串转义

## 规则

硬约束：

- 只允许单条语句。
- 只允许 `SELECT` 或 `WITH`。
- 必须带 `LIMIT`；默认 `LIMIT 50`。
- MySQL `nodes` 和 `documents` 查询必须过滤 `isDeleted = 0`。
- MySQL 联表时，每张表都要独立过滤删除标记。
- 创建、更新、移动、删除、重命名、幂等同步、反馈都不能写 SQL，必须走专用命令。
- 禁止不带根节点或 ID 范围的大文本搜索。

推荐习惯：

- 优先用精确 ID，再使用模糊匹配。
- 读取 `content` 前先用 `rootId` 或 `rootnodeid` 缩小范围。
- 只选择需要的字段。
- 跨 MySQL 和 PostgreSQL 时，优先拆成两条清晰查询。

## 查询路径

| 用户诉求         | 第一阶段                         | 可选第二阶段                             |
| ------------ | ---------------------------- | ---------------------------------- |
| 查目录、节点、路径    | MySQL `nodes`                | 无                                  |
| 查标题、正文、作者、来源 | MySQL `documents` 联 `nodes`  | PostgreSQL `knowledge` 查召回覆盖       |
| 查某文档是否进入召回   | MySQL `documents` 定位 `docId` | PostgreSQL `knowledge` 按 `docid` 查 |
| 查某主题召回覆盖     | PostgreSQL `knowledge` 按根节点查 | MySQL `documents` 查权威原文            |
| 排查“搜不到”      | MySQL 查源文档是否存在               | PostgreSQL 查切片和模型覆盖                |

## MySQL `nodes`

按根节点列出节点：

```sql
SELECT id, name, parentId, rootId, level, isLeaf, fullPath
FROM nodes
WHERE isDeleted = 0
  AND rootId = <root_id>
ORDER BY level, id
LIMIT 50
```

查单个节点：

```sql
SELECT id, name, parentId, rootId, level, isLeaf, status, isPublic, fullPath
FROM nodes
WHERE isDeleted = 0
  AND id = <node_id>
LIMIT 1
```

在已知根节点下按名称搜节点：

```sql
SELECT id, name, parentId, rootId, level, isLeaf, fullPath
FROM nodes
WHERE isDeleted = 0
  AND rootId IN (<root_id>)
  AND name LIKE '%<keyword>%'
ORDER BY level, id
LIMIT 20
```

## MySQL `documents`

按标题搜索：

```sql
SELECT d.id, d.title, d.nodeId, d.authorName, d.resource, d.resourceId, n.rootId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND n.rootId = <root_id>
  AND d.title LIKE '%<keyword>%'
ORDER BY d.id DESC
LIMIT 20
```

缩小根节点后搜索正文：

```sql
SELECT d.id, d.title, d.nodeId, n.rootId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND n.rootId IN (<root_id>)
  AND d.content LIKE '%<keyword>%'
ORDER BY d.id DESC
LIMIT 20
```

查权威文档原文：

```sql
SELECT d.id, d.title, d.content, d.authorName, d.resource, d.resourceId,
       d.version, d.current, d.nodeId, n.rootId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND d.id = <doc_id>
LIMIT 1
```

查某根节点下最近文档：

```sql
SELECT d.id, d.title, d.authorName, d.resource, d.resourceId, d.nodeId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND n.rootId = <root_id>
ORDER BY d.id DESC
LIMIT 20
```

## PostgreSQL `knowledge`

按文档查切片：

```sql
SELECT docid, nodeid, rootnodeid, model, slice, content
FROM knowledge
WHERE docid = <doc_id>
ORDER BY slice
LIMIT 50
```

按根节点搜索索引内容：

```sql
SELECT docid, nodeid, rootnodeid, model, slice, content
FROM knowledge
WHERE rootnodeid = <root_id>
  AND content ILIKE '%<keyword>%'
ORDER BY docid, slice
LIMIT 20
```

查看模型覆盖：

```sql
SELECT model, COUNT(*) AS sliceCount, COUNT(DISTINCT docid) AS docCount
FROM knowledge
WHERE rootnodeid = <root_id>
GROUP BY model
ORDER BY sliceCount DESC
LIMIT 20
```

查看根节点是否有索引：

```sql
SELECT rootnodeid, COUNT(*) AS sliceCount, COUNT(DISTINCT docid) AS docCount
FROM knowledge
WHERE rootnodeid IN (<root_id>)
GROUP BY rootnodeid
ORDER BY sliceCount DESC
LIMIT 50
```

## 两阶段模板

文档存在，但检索疑似缺失：

```sql
SELECT d.id, d.title, d.nodeId, n.rootId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND n.rootId = <root_id>
  AND d.title LIKE '%<keyword>%'
ORDER BY d.id DESC
LIMIT 10
```

然后查：

```sql
SELECT docid, nodeid, rootnodeid, model, slice, content
FROM knowledge
WHERE docid IN (<doc_id>)
ORDER BY docid, slice
LIMIT 50
```

源文档里有某主题，但召回疑似缺失：

```sql
SELECT d.id, d.title, d.nodeId, n.rootId, n.fullPath
FROM documents d
JOIN nodes n ON n.id = d.nodeId
WHERE d.isDeleted = 0
  AND n.isDeleted = 0
  AND n.rootId = <root_id>
  AND d.content LIKE '%<keyword>%'
ORDER BY d.id DESC
LIMIT 20
```

再对照：

```sql
SELECT docid, nodeid, rootnodeid, model, slice, content
FROM knowledge
WHERE rootnodeid = <root_id>
  AND content ILIKE '%<keyword>%'
ORDER BY docid, slice
LIMIT 20
```

如果 MySQL 有源文档，而 PostgreSQL 没有相关切片，说明知识存在但召回链路缺失，应优先上报 `BAD_RECALL`，并把应命中的文档放入 `expectedDocIds`；不要按知识缺失处理。

## 避免

- `SELECT *`
- 不带范围搜索 `documents.content`
- 不带范围搜索 `knowledge.content`
- 把 `knowledge.content` 当作最终文档原文
- 用 SQL 做写操作或反馈
- 复用旧示例里的 root ID，而不是执行 `roots`

