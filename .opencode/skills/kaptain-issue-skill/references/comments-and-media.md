# 评论、动态与媒体

## 媒体链接处理（内网图片/视频）

当用户输入、事项描述、事项评论、事项动态记录里出现图片或视频 URL，且用户要求“查看/分析/识别”时：

1. 先检测媒体 URL
2. 若资源受保护，从当前环境可用的 MCP 配置 JSON 中读取认证信息
3. 优先查找当前 `kaptain-mcp` 对应 server 的 `env`
4. 下载到 `/tmp/` 临时目录后再分析
5. 下载失败时明确说明失败原因

## 富文本插图规则

1. 先调用 `upload_editor_attachment` 上传本地媒体文件
2. 从返回结果里读取 `url`
3. 把 `url` 写进富文本 HTML
4. 再调用 `create_issue`、`update_issue`、`add_issue_comment` 或 `update_issue_comment`

## 评论与动态

- `list_issue_comments`：查询事项评论树，不要扁平化
- `add_issue_comment`：新增事项评论，回复评论要传父评论 ID
  - `cardType` 必须与该事项详情里的 `cardType` 一致
  - 如果用户只给了事项链接、事项 key 或事项 id，但当前上下文没有可靠的 `cardType`，先调用 `get_issue_detail` 取值，再发评论
  - 禁止把 `cardType` 写死成常量，禁止按“需求/任务/缺陷”字面去猜
- `update_issue_comment`：编辑事项评论
- `list_issue_records`：查询事项动态记录，不要提前摘要化
