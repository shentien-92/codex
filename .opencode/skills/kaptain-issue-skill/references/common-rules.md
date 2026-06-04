# 通用规则

## 核心规则

1. “我的敏捷组”必须调用 `get_my_projects`
2. “全量敏捷组搜索”必须调用 `search_projects`
3. “我的事项”必须调用 `get_my_work_matters`
4. 查询当前用户必须调用 `get_current_user`
5. 查询事项列表必须调用 `list_issues`
6. 按敏捷组查迭代必须调用 `list_iterations`
7. 查单个迭代详情必须调用 `get_iteration_detail`
8. 查当前迭代必须调用 `list_iterations`，并按 `startTime <= now <= endTime` 从结果里筛选
9. 查询事项详情时，`issueId` 和 `issueKey` 只能二选一
10. 查询事项下一步状态必须调用 `list_issue_next_nodes`
11. 查询目标状态必填项必须调用 `get_issue_required_properties`
12. 通用更新事项字段必须调用 `update_issue`
13. 上传事项描述或评论里的图片/视频必须调用 `upload_editor_attachment`
14. 查询事项评论必须调用 `list_issue_comments`
15. 新增事项评论必须调用 `add_issue_comment`
16. 编辑事项评论必须调用 `update_issue_comment`
17. 查询事项动态记录必须调用 `list_issue_records`
18. 记录工时必须走工作日志接口，不要伪造成事项字段更新
19. 状态流转如需附带工时，应优先调用 `transition_issue_status`
20. 任何需要传 `cardType` 的事项操作，参数值都必须与 `get_issue_detail` 返回的 `cardType` 保持一致
21. 如果当前上下文没有可靠的 `cardType`，先查事项详情；禁止按事项类型名称、经验值或历史示例猜测 `cardType`
22. 创建事项前，禁止假设“接口能创建成功”就等于“业务字段完整可用”；遇到敏捷组自定义必填字段不明确时必须先补齐信息
23. 对创建事项场景，禁止为了减少追问而省略字段、猜字段或使用硬编码默认值
24. 对需求、任务、缺陷的创建，默认目标是“复刻前端校验通过后再提交”，而不是“只要后端接口接受就提交”
25. 所有新增、修改类型的操作，都必须先参考同敏捷组、同事项类型、近期正常事项；没有历史样本支撑时，不得凭空想象字段值

## 事项链接规则

当回复里出现事项 `key` 时，在以下场景必须输出为可点击跳转链接：

1. 查询事项详情
2. 事项列表结果较少时，通常指 `1-30` 条

事项链接格式统一使用：

```markdown
[事项KEY](https://kaptain.qunhequnhe.com/project/detail/issue?projectId=敏捷组ID&key=事项KEY)
```

规则：

- 链接挂在事项 `key` 上，不挂在标题上
- 禁止在上述场景只返回纯文本 `key`
- 如果结果很多，不要求每条都带链接，优先先缩小筛选范围
- 如果缺少 `projectId` 或 `key`，先补全信息后再输出链接

## 调用原则

1. 严格按工具语义调用，不要混用工具
2. 未确认的字段优先透传，不要在 skill 中造枚举
3. 状态流转和工作日志是组合场景，但日志最终仍然走工作日志接口
4. 如果用户表达的是“查询我的相关数据”，优先先判断是否需要 `get_current_user`
