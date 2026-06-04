# 前端 CI 域排查手册

## 先看什么

质量把关问题优先检查：

1. `package.json`
2. `def.config.js`
3. `gitlab-ci.yml`
4. `eslint` / 测试配置
5. `code-stage.json`

## 接入审查清单

- 是否已执行 `kjl task install ci`
- `def.config.js` 的 `tasks` 中是否已有 `ci:*`
- 是否明确至少接入 `ci:lint` 与 `ci:uni-test`
- 如果要接 `ci:uni-test`，测试框架是否为 `jest` 或 `mocha`
- 是否决定了远程托管还是本地 YAML
- 是否初始化过 `kjl ci:init`
- 是否把本地卡点接到实际提交流程

## lint 问题排查

优先检查：

- 运行的是不是 `kjl ci:lint`
- 文件是否已经暂存
- `extendsLintRc` 是否存在且路径正确
- 是否错误尝试覆盖刚性规则
- 是否需要 `lintSerially` 以缓解内存问题
- 是否错误理解了“只检查修改行”和“全量扫描”的关系

## 单测与覆盖率排查

优先检查：

- `testType` 是 `jest` 还是 `mocha`
- 如果不是 `jest` 或 `mocha`，先明确当前框架不在 `ci:uni-test` 支持范围内
- `testConfigFile` 是否存在
- 测试文件匹配规则是否正确
- 是否缺少 `nyc` / `c8`
- 是否配置了 `collectCoverageFrom`
- 是否需要 `code-stage.json` 来表达核心模块覆盖率

## 流水线排查

优先检查：

- 当前流水线是 MR、分支还是每日构建
- YAML 是否包含 `test` stage
- `rules` 是否覆盖当前触发场景
- 项目到底使用远程托管还是本地文件
- 现有仓库是否已经有自定义 stage，导致模板片段不能直接落下

## 输出建议

对用户反馈时尽量固定成这四段：

- 已确认配置
- 缺失或异常配置
- 最可能导致卡点的原因
- 最小修复动作
