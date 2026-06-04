---
name: confluence
description: 使用 @qunhe/confluence CLI 管理 Confluence (cf.qunhequnhe.com) 页面、评论、附件和 drawio 图表。当需要创建/更新/查询 Confluence 页面、评论、上传附件、嵌入 drawio 图表、撰写 Dev Design 技术方案文档，或处理 cf.qunhequnhe.com 链接时使用。
allowed-tools: Bash(npx -y @qunhe/confluence@latest *), Bash(confluence *), Bash(mkdir -p .confluence-mcp-temp), Read, Write(.confluence-mcp-temp/*)
---

# Confluence CLI

使用 `@qunhe/confluence` CLI 工具管理酷家乐内部 Confluence (cf.qunhequnhe.com) 的页面和附件。

支持两种使用方式：

1. **npx（推荐）**：`npx -y @qunhe/confluence@latest <command>` — 始终使用最新版本，无需安装
2. **全局安装**：`npm install -g @qunhe/confluence` 后直接使用 `confluence <command>`

优先尝试直接执行 `confluence`（全局安装方式），如果命令不存在则回退到 `npx -y @qunhe/confluence@latest`。

以下文档中 `confluence` 指代上述任一方式。

---

# 第一部分：CLI 命令参考

## 认证

CLI 按以下优先级查找凭据：

1. **配置文件** (`~/.confluence/config.json`) — 通过 `confluence auth config` 设置
2. **环境变量** `CONFLUENCE_ACCESS_TOKEN`
3. **环境变量** `MOON_TOKEN`（Moon 平台 Token）
4. **设备授权流程**（自动打开浏览器，仅适用于交互式终端）

未配置个人 Token 时，CLI 使用公共机器人身份，页面归属为机器人而非个人。

```bash
# 配置 Access Token（保存到 ~/.confluence/config.json）
confluence auth config --token=<your-access-token>

# 查看认证状态
confluence auth status
```

## 页面命令

### pages list — 查询子页面

```bash
confluence pages list <spaceOrPage>
```

- `<spaceOrPage>`：空间 KEY（如 `EP`、`~zhuyang`）、页面 ID 或页面 URL
- 如果传入的是空间 KEY，列出该空间首页的子页面；否则列出指定页面的子页面

### pages get — 查询页面详情

```bash
confluence pages get <pageIdOrUrl> [options]
```

| 选项 | 说明 |
|------|------|
| `--metadata-only` | 仅输出元信息（ID、标题、空间、URL、版本等） |
| `--format <format>` | 输出格式：`storage`（默认）、`view`、`markdown` |
| `--body-only` | 仅输出正文内容 |
| `--output <path>` | 将正文写入指定文件（需配合 `--body-only` 使用） |

### pages search — 搜索页面

```bash
confluence pages search <query> [options]
```

| 选项 | 说明 |
|------|------|
| `--cql` | 启用 CQL 模式（默认为标题关键词搜索） |
| `--start <n>` | 分页起始位置，默认 0 |
| `--limit <n>` | 返回数量，默认 10 |
| `--format json` | 输出原始 JSON |

不加 `--cql` 时，输入自动转为 `title ~ "query"`。自动补充 `type = page` 和 `order by created desc`。

CQL 语法参考：https://developer.atlassian.com/server/confluence/advanced-searching-using-cql/

### pages create — 创建页面

```bash
confluence pages create --title <title> --file <file> [options]
```

| 参数/选项 | 说明 |
|-----------|------|
| `--title` | **必填**，页面标题 |
| `--file` | **必填**，正文文件路径 |
| `--parent <parent>` | 父页面的空间 KEY、页面 ID 或 URL。省略时创建到当前用户个人空间 |
| `--format <format>` | 正文格式：`storage`（默认）或 `markdown`。详见下方「何时使用 --format markdown」 |

### pages update — 更新页面

```bash
confluence pages update <page> --file <file> --version-number <number> --message <message> [options]
```

| 参数/选项 | 说明 |
|-----------|------|
| `<page>` | **必填**，页面 ID 或 URL |
| `--file` | **必填**，更新后的正文文件路径 |
| `--version-number` | **必填**，目标版本号（必须比当前版本大 1） |
| `--message` | **必填**，版本变更说明 |
| `--title` | 可选，修改页面标题 |
| `--format <format>` | 正文格式：`storage`（默认）或 `markdown`。详见下方「何时使用 --format markdown」 |

### pages label — 添加标签

```bash
confluence pages label <page> <label>
```

| 参数 | 说明 |
|------|------|
| `<page>` | **必填**，页面 ID 或 URL |
| `<label>` | **必填**，标签名称 |

## 用户命令

### users current — 查询当前用户

```bash
confluence users current
```

输出当前认证用户的显示名称、用户名和用户 Key。

### users search — 搜索用户

```bash
confluence users search <user>
```

- `<user>`：花名拼音或中文，不区分大小写
- 输入中文时会自动转拼音匹配 username，容错同音不同字（如"猪羊"也能匹配到 `zhuyang`）
- 精确匹配（displayName 或 username 完全一致）时直接展示用户信息
- 无精确匹配时，按 includes 模糊搜索并列出候选用户列表

> **提示**：搜索结果中的 `用户 Key` 可用于页面正文中的 user mention 宏（`<ri:user ri:userkey="..."/>`），详见宏参考中的 [mention](#mention) 部分。

## 评论命令

### comments list — 查询评论列表

```bash
confluence comments list <page> [options]
```

- `<page>`：页面 ID 或 URL
- 树形展示评论及回复，行内评论会标注被评论的原文和 markerRef

| 选项 | 说明 |
|------|------|
| `--format <format>` | 输出格式：`storage`（默认）、`view`、`markdown` |

### comments create — 创建评论

```bash
confluence comments create <page> [body...] [options]
```

| 参数/选项 | 说明 |
|-----------|------|
| `<page>` | **必填**，页面 ID 或 URL |
| `[body...]` | 评论内容，多个参数用空格拼接（与 `--file` 二选一） |
| `--file <file>` | 评论内容文件路径（Confluence Storage Format） |
| `--parent-comment-id <id>` | 父评论 ID（用于回复已有评论） |

## 附件命令

### attachments list — 查询附件列表

```bash
confluence attachments list <page> [--format json]
```

- `<page>`：页面 ID 或 URL

### attachments download — 下载附件

```bash
confluence attachments download <page> <attachment> [options]
```

| 参数/选项 | 说明 |
|-----------|------|
| `<page>` | 页面 ID 或 URL |
| `<attachment>` | 附件名称或 ID |
| `--version <n>` | 指定附件版本 |
| `--output <path>` | 输出路径，支持文件路径或已存在的目录（自动拼接附件名）。默认为当前目录下的附件同名文件 |
| `--decompress-drawio` | 解压并格式化 drawio XML（drawio 附件默认是压缩的） |

> **提示**：形如 `https://cf.qunhequnhe.com/download/attachments/<pageId>/<filename>?version=1&modificationDate=...&api=v2` 的链接是 Confluence 附件下载链接，可以从中提取 `pageId` 和 `filename`，然后使用 `confluence attachments download <pageId> <filename>` 下载。

### attachments upload — 上传附件

```bash
confluence attachments upload <page> <file> [options]
```

| 参数/选项 | 说明 |
|-----------|------|
| `<page>` | 页面 ID 或 URL |
| `<file>` | 本地文件路径 |
| `--attachment-id <id>` | 指定附件 ID（用于更新已有附件） |
| `-y, --yes` | 跳过覆盖确认 |

文件大小限制：10 MiB。如果页面上已存在同名附件，会提示确认覆盖（除非加 `-y`）。

---

# 第二部分：工作流

## 何时使用 --format markdown

### 阅读场景（pages get）

`pages get` 时可以自由使用 `--format markdown`，适合仅阅读、不需要编辑的场景：

- **只需了解页面内容** — `--format markdown` 输出更简洁易读，且节省 token
- **需要编辑页面** — 必须使用 `--format storage`，否则回写时会丢失 Confluence 宏和格式信息

### 写入场景（pages create / pages update）

<IMPORTANT>
`--format markdown` 仅允许在以下写入场景使用：

1. **从零创建新页面** — 页面内容完全由 AI 用 Markdown 编写，且不基于任何模版
2. **更新全程由 AI 用 Markdown 编写的页面** — 整个页面生命周期都使用 Markdown 管理

**禁止在以下场景使用 `--format markdown`：**

- 基于页面模版创建页面（如 Dev Design 等）— 模版本身是 Storage Format HTML，必须使用 `--format storage`
- 编辑用户提供的已有页面 — 必须使用 `--format storage` 获取并更新，否则会丢失 Confluence 宏和格式信息
- 对已有页面做局部修改 — 必须按「编辑已有页面」工作流操作

简单判断：如果你需要先 `pages get` 获取页面内容再修改，或者基于模版创建页面，就不能用 `--format markdown`。
</IMPORTANT>

## 编辑已有页面

<IMPORTANT>
编辑已有页面时，必须严格按照以下流程操作。禁止跳过任何步骤。禁止不经本地文件直接更新页面。
</IMPORTANT>

```bash
# 1. 获取页面元信息（记下版本号）和正文内容，保存到本地文件
confluence pages get <page> --metadata-only
confluence pages get <page> --format storage --body-only --output .confluence-mcp-temp/<page-id>.html

# 2. 使用 Read/Edit 工具修改本地文件
#    ...

# 3. 更新页面（版本号 = 当前版本 + 1）
confluence pages update <page> --file .confluence-mcp-temp/<page-id>.html --version-number <N+1> --message "变更说明"
```

- 步骤 1 的 `--format storage` 保留完整的 Confluence 宏和格式信息，确保编辑后回传不丢失结构
- 步骤 1 的 `--body-only` 仅输出正文，避免元信息混入文件内容
- 步骤 3 的 `--version-number` 和 `--message` 必填

<IMPORTANT>
**版本号冲突处理**：如果版本号冲突（报错 "Version must be incremented"），说明有其他人在此期间编辑了页面。此时必须：
1. 重新获取最新页面内容和版本号
2. 基于最新内容重新应用修改
3. 使用新的版本号重试
</IMPORTANT>

## 创建带 drawio 图表的新页面

### 步骤 1：创建 drawio 文件

将 drawio XML 写入本地文件（如 `.confluence-mcp-temp/architecture.drawio`）。

drawio XML 示例：

```xml
<mxfile>
  <diagram name="Page-1" id="page1">
    <mxGraphModel>
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>
        <mxCell id="2" value="Service A" style="rounded=1;whiteSpace=wrap;" vertex="1" parent="1">
          <mxGeometry x="120" y="80" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="3" value="Service B" style="rounded=1;whiteSpace=wrap;" vertex="1" parent="1">
          <mxGeometry x="360" y="80" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="4" style="edgeStyle=orthogonalEdgeStyle;" edge="1" source="2" target="3" parent="1">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### 步骤 2：在页面正文中嵌入 drawio 宏

在 Confluence Storage Format 正文中使用 drawio 宏引用图表：

```xml
<ac:structured-macro ac:name="drawio" ac:schema-version="1">
  <ac:parameter ac:name="border">true</ac:parameter>
  <ac:parameter ac:name="diagramName">architecture.drawio</ac:parameter>
  <ac:parameter ac:name="simpleViewer">false</ac:parameter>
  <ac:parameter ac:name="links">auto</ac:parameter>
  <ac:parameter ac:name="tbstyle">top</ac:parameter>
  <ac:parameter ac:name="lbox">true</ac:parameter>
  <ac:parameter ac:name="diagramWidth">auto</ac:parameter>
  <ac:parameter ac:name="revision">1</ac:parameter>
</ac:structured-macro>
```

`diagramName` 必须与上传的附件文件名一致，`revision` 固定为 `1`（首次上传）。

### 步骤 3：创建页面并上传附件

由于上传附件需要 pageId，因此必须先创建页面、再上传 drawio 文件：

```bash
# 1. 创建页面
confluence pages create --parent <parentPage> --title "我的页面" --file .confluence-mcp-temp/page.html

# 2. 上传 drawio 附件（使用创建页面返回的 pageId）
confluence attachments upload <pageId> .confluence-mcp-temp/architecture.drawio -y
```

## 更新已有页面的 drawio 图表

1. 查询附件列表获取 attachmentId：`confluence attachments list <page>`
2. 下载现有 drawio 附件并解压：`confluence attachments download <page> <name>.drawio --decompress-drawio --output .confluence-mcp-temp/`
3. 使用 Read/Edit 工具修改本地 drawio 文件
4. 上传新版本：`confluence attachments upload <page> .confluence-mcp-temp/<name>.drawio --attachment-id <id> -y`
5. 更新页面正文中 drawio 宏的 `revision` 参数为新的附件版本号

---

# 第三部分：参考信息

## Confluence Storage Format 宏

撰写页面正文时可使用丰富的 Confluence 宏提升可读性，完整的宏列表和示例代码见 [references/macros.md](references/macros.md)。

常用宏速查：

| 宏 | 用途 |
|----|------|
| `code` | 代码块（支持语法高亮） |
| `drawio` | 嵌入 draw.io 图表 |
| `mermaid-macro` | 使用 Mermaid 语法画图 |
| `info` / `note` / `tip` / `warning` | 彩色提示框 |
| `expand` | 可折叠文本块 |
| `status` | 状态标签（Blue/Grey/Green/Red/Yellow） |
| `toc` | 自动生成目录 |
| `table` | HTML 表格 |
| `task-list` | 带复选框的任务列表 |
| `kaptain-issue` | 显示 Kaptain 事项状态 |
| `image` | 显示图片（附件或 URL） |
| `mention` | @提及用户（需要 userKey，可通过 `users search` 获取） |
| `emoticon` | 表情符号 |

## 注意事项

- 页面正文必须是 [Confluence Storage Format](https://confluence.atlassian.com/doc/confluence-storage-format-790796544.html)（基于 XHTML），不要包含 `<html>`、`<head>`、`<body>` 等外层标签
- 正文内容禁止使用 emoji 字符（Confluence 不支持）
- 建议将正文文件存放在 `.confluence-mcp-temp/` 目录下

## 常见报错与解决方法

| 报错 | 原因 | 解决方法 |
|------|------|----------|
| `权限不足，无法访问该页面` (403) | 当前认证身份没有访问权限 | `confluence auth status` 确认身份；配置个人 Token 或联系管理员授权 |
| `Version must be incremented` | 版本号不等于当前版本 +1，通常是有人同时编辑 | 重新获取最新版本号和内容，重新应用修改后重试 |
| `文件大小超过 10 MiB 限制` | 单个附件超限 | 压缩文件或拆分为多个附件 |
| `页面不存在` (404) | 页面 ID/URL 无效或已删除 | 确认 ID/URL 是否正确；使用 `pages search` 搜索 |
| `认证失败，请检查 Token 是否有效` | Token 过期或无效 | 重新配置：`confluence auth config --token=<new-token>` |
| `认证失败：无效的 it-confluence-micro-token` | 个人 Access Token 尚未通过审批，或审批流程未完成 | 参照 [Access Token 配置与审批指南](https://cf.qunhequnhe.com/pages/viewpage.action?pageId=81446652672) 发起审批流程；审批通过后 Token 即可正常使用 |
| `npm error 404 @qunhe/confluence` | 未配置内网 npm 仓库 | `npm config set registry http://npm-registry.qunhequnhe.com` |
| `EPERM: operation not permitted, mkdir` | Claude Code 沙箱限制了写入权限 | 关闭沙箱功能或将 `npx -y @qunhe/confluence@latest` 添加到白名单 |
| `error: unknown command '<command>'` | CLI 版本过旧，不支持该子命令 | 全局安装用户执行 `npm install -g @qunhe/confluence@latest` 更新；npx 用户确认使用了 `@latest` 标签 |

---

# 第四部分：文档模版

当需要撰写特定类型的 Confluence 文档时，参考以下模版和工作流。

## Dev Design（技术方案文档）

结合代码库，参照标准 Dev Design 模版撰写技术方案文档并发布到 Confluence。

完整工作流见 [references/dev-design.md](references/dev-design.md)，包含 9 个步骤：需求理解、代码探索、方案对比、模版选择、drawio 画图、撰写正文、内容自检、创建页面、用户审批。

模版文件：

- [后端 Dev Design 模版](references/templates/backend-dev-design.html)
- [前端 Dev Design 模版](references/templates/frontend-dev-design.html)
