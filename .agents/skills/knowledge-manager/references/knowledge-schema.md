# 知识库查询模型

适用时机：

- 不确定该查 `nodes`、`documents` 还是 `knowledge`
- 用户的问题同时涉及结构、原文、召回
- 需要先判断应该走 MySQL 还是 PostgreSQL

> 如果你只是想判断"查哪张表"，看完本文件就可以停，不要再打开 `sql-playbook.md`。

目录：

1. MySQL `nodes`
2. MySQL `documents`
3. PostgreSQL `knowledge`
4. 三张表之间的关系
5. 选表口诀

这份参考文件只回答一件事：用户问一个知识库问题时，应该先查 MySQL 哪张表，还是查 PostgreSQL `knowledge`。

## MySQL `nodes`

`nodes` 是知识库目录树的事实来源。

典型字段：

- `id`：节点 ID
- `name`：节点名称
- `parentId`：父节点 ID
- `rootId`：所属根节点 ID
- `level`：层级
- `isLeaf`：是否叶子节点
- `status`：节点状态
- `isPublic`：是否公开
- `fullPath`：完整路径
- `isDeleted`：逻辑删除标记

适合解决的问题：

- 某个节点属于哪个根节点
- 某个目录下有哪些子节点
- 某个节点的完整路径是什么
- 某个查询应该限制在哪些根节点下

不适合解决的问题：

- 文档正文是什么
- 某篇文档有没有被切片入库

## MySQL `documents`

`documents` 是知识文档原文和元数据的事实来源。

典型字段：

- `id`：文档 ID
- `nodeId`：当前挂载的节点
- `title`：标题
- `content`：正文
- `authorName`：作者
- `resource`：文档来源类型
- `resourceId`：来源系统资源 ID
- `merchantAnswer` / `personalAnswer` / `internalAnswer`：不同视角答案
- `version`：版本
- `current`：当前版本标记
- `isDeleted`：逻辑删除标记

适合解决的问题：

- 找标题包含某关键词的文档
- 找正文提到某个主题的文档
- 查某篇文档当前挂在哪个节点
- 查某个根节点下有哪些文档
- 拿文档原文做展示、校验、二次处理

不适合解决的问题：

- 文档有没有被拆成召回切片
- 某个模型写了多少召回片段

## PostgreSQL `knowledge`

`knowledge` 是召回切片和向量索引层，不是文档原文的唯一事实来源。

典型字段：

- `id`：切片记录 ID
- `nodeid`：切片所属节点
- `rootnodeid`：切片所属根节点
- `docid`：来源文档 ID
- `model`：切片对应的向量模型
- `slice`：文档切片序号
- `content`：切片文本
- `inputtype`：输入类型
- `embedding_half`：向量

适合解决的问题：

- 某篇文档有没有进入召回索引
- 某个根节点下有哪些切片
- 某个模型覆盖了哪些文档
- 某个主题是否已经被切片内容覆盖
- 排查“文档有了但召回没生效”

不适合解决的问题：

- 直接把它当文档原文来源
- 依赖它判断目录树结构

## 三张表之间的关系

- `documents.nodeId = nodes.id`
- `knowledge.docid = documents.id`
- `knowledge.nodeid` 通常与 `documents.nodeId` 对齐
- `knowledge.rootnodeid` 通常与 `nodes.rootId` 对齐

最常见的两段式查询是：

1. 在 MySQL 里用 `nodes` / `documents` 找到目标 `docId`、`nodeId`、`rootId`
2. 在 PostgreSQL 里用这些 ID 去查 `knowledge`

## 选表口诀

- 查树，用 `nodes`
- 查原文，用 `documents`
- 查召回，用 `knowledge`
- 查全链路，先 MySQL，后 PostgreSQL
