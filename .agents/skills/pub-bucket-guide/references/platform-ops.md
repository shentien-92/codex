# 平台操作参考

## 目录

- 核心对象
- pub-mcp-server 分桶工具
- 创建分桶应用
- 创建试验
- 配置版本与流量
- 设置白名单与标签
- 注入 PUB 应用
- 查询结果

## 核心对象

PUB 分桶的核心对象有三层：

1. 应用：一个业务组内一系列试验的容器
2. 试验：一项待观察的功能或策略
3. 版本：试验下的多个候选实现

回答时优先先把用户的问题归到这三层之一。

## pub-mcp-server 分桶工具

当前 `pub-mcp-server` 已暴露一组分桶相关工具，主要覆盖“搜索、详情、启停、流转、流量、白名单、日志”等操作。

已确认可用的工具包括：

- `bucket_search_applications`
  搜索分桶应用列表，可用于定位 `appKey`、应用名称和应用 id。
- `bucket_search_experiments`
  搜索分桶试验列表，可按 `appKey`、`experimentKey`、负责人、状态、环境过滤。
- `bucket_get_experiment_detail`
  获取单个试验详情。
- `bucket_start_experiment`
  启动试验。
- `bucket_stop_experiment`
  停止试验。
- `bucket_finish_experiment`
  结束试验。
- `bucket_sync_experiment`
  跨环境流转试验；目标环境为 `beta` 或 `prod`，流转到 `prod` 时需要 `issueKey`。
- `bucket_update_flow`
  更新试验版本流量配置；要求所有版本流量总和为 `100`。
- `bucket_get_whitelist`
  查询试验白名单。
- `bucket_add_whitelist`
  添加试验白名单。
- `bucket_delete_whitelist`
  删除试验白名单。
- `bucket_get_action_log`
  获取试验操作日志。

白名单 `dataType` 约定：

- `0`：`USERID`
- `1`：`IP`
- `2`：`DEVICEID/QHDI`
- `3`：`ACCOUNTID`
- `4`：`TAG`

目前这批工具更偏“试验运维与管理”。

要特别提醒用户：

- 我们已经确认有分桶相关 MCP 工具，不要再默认认为“pub-mcp-server 没有分桶能力”。
- 但当前已暴露工具里，暂未看到“创建分桶应用”“创建试验”“配置标签”的完整建模能力。
- 也就是说，现阶段更适合用 MCP 做“查、改流量、改白名单、启停、流转、查日志”，而不是完全替代 Bucket 平台页面。

## 创建分桶应用

创建应用时至少要确认：

- 应用名称
- `appKey`
- 关联的 PUB 节点
- 分桶规则使用的维度：`userId`、`rootAccountId`、`qhdi`

注意：

- `appKey` 需要唯一
- 一般不要轻易挂到已有应用上，否则两个应用下的试验会同步
- 分桶维度选定后不可变更

## 创建试验

创建试验时至少要确认：

- 试验名称
- `expKey`
- 试验层级
- 预计到期时间

说明：

- 相同层的试验互斥
- 每层拥有 100% 的流量空间
- 到期时间用于提醒，不会自动删除或暂停试验

## 配置版本与流量

一个试验下可以有多个版本。

固定事实：

- 默认原始版本 key 为 `ORIGINAL`
- 可以新增多个优化版本
- 同一试验内所有版本流量之和不超过 100%
- 配好后需要开始试验才会生效

如果用户要通过 MCP 改流量，优先使用：

- `bucket_update_flow`

入参要点：

- `appKey`
- `experimentKey`
- `env`：`alpha` / `beta` / `prod`
- `versions`：每个版本都要带 `versionKey`、`versionName`、`versionFlow`

使用前先查详情，避免把旧版本列表覆盖掉：

1. 先 `bucket_get_experiment_detail`
2. 再基于当前版本列表组装完整 `versions` payload
3. 最后 `bucket_update_flow`

结果语义：

- 未分配流量时，试验结果可能为空
- 原始版本设为 100% 时，会返回完整结果结构

## 设置白名单与标签

白名单支持的常见维度：

- `userid`
- `ip`
- `qhdi`
- `rootaccountid`

标签支持的常见维度：

- 用户类型
- 用户注册时间
- 行业类型
- 会员用户
- 企业版本

使用要点：

- 白名单优先级最高，命中后直接返回指定版本
- 标签是准入条件，不命中标签时，用户不会进入试验
- 多个标签之间是“与”关系

如果用户要通过 MCP 操作白名单，优先使用：

- 查询：`bucket_get_whitelist`
- 新增：`bucket_add_whitelist`
- 删除：`bucket_delete_whitelist`

新增白名单时至少确认：

- `appKey`
- `experimentKey`
- `env`
- `dataType`
- `dataValue`
- `version`

说明：

- `version` 是命中白名单后直接返回的版本 key
- 白名单命中后不会再继续正常分桶逻辑
- 当前已暴露工具里，没有看到“试验标签配置”的 MCP 能力，这部分仍应以 Bucket 平台页面为主

## 注入 PUB 应用

如果是 PUB 应用，推荐走注入方式，而不是在浏览器端自己请求接口。

平台侧路径要点：

- 在应用管理或应用节点上勾选分桶配置
- 保存后，把分桶结果注入当前 PUB 应用

注入后的模板变量：

- `global_pubBucket`

前端通常在 `njk` 中继续写入浏览器全局变量，详见 `local-integration.md`。

## 查询结果

结果获取有两种常见方式：

1. 通过 PUB 注入结果
2. 通过试验页面提供的接口直接请求结果

优先建议：

- PUB 项目优先用注入方式
- 非 PUB 或调试特定试验时，再考虑接口查询

如果用户要分析试验访问情况，可引导其查看数据平台中的试验结果页面，或结合分桶埋点做分析。

如果用户要通过 MCP 查询对象或排查试验状态，优先按下面顺序：

1. 先 `bucket_search_applications` 定位应用
2. 再 `bucket_search_experiments` 定位试验
3. 再 `bucket_get_experiment_detail` 看详情
4. 需要补充操作历史时，查 `bucket_get_action_log`
