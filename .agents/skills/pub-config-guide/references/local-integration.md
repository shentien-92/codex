# 本地接入参考

## 目录

- 判断项目类型
- PUB 项目接入配置包
- 非 PUB 项目接入配置包
- 找接入点
- 梳理数据流转链路
- 本地联调闭环

## 判断项目类型

先判断当前项目是否为 PUB 项目：

- 根目录是否存在 `def.config.js`
- 是否存在 `.pubrc.js`
- 是否存在典型 PUB 应用结构
- 是否通常使用 `kjl dev` 启动

处理原则：

- PUB 项目：走“平台注入 + 模板注入”路径
- 非 PUB 项目：重点看 `@qunhe/config-client`

## PUB 项目接入配置包

PUB 项目分两层处理：

1. 先在 PUB 系统中把配置包注入到应用
2. 再在本地应用的 `njk` 中注入配置

平台侧注入：

- 默认直接使用 `config_inject_package_to_app` 发起注入。
- `config_inject_package_to_app` 的 `add` 已内置可挂载范围校验，以及“当前节点或父节点已生效包”的自动过滤。
- 只有在需要查看当前生效状态、解释继承关系或排查问题时，才额外使用 `config_injection_query`。

建议入参：

```json
{
  "action": "add",
  "appName": "应用名称",
  "issueKey": "优先从当前分支提取的敏捷事项ID",
  "packages": ["配置包名称"],
  "user": "当前用户"
}
```

模板侧读取：

```njk
{{ global_pubConfig.config_name.config_item }}
```

示例：

```njk
<div>{{ global_pubConfig.test_fc_config.title }}</div>
```

说明：

- `global_pubConfig` 由 PUB 注入到模板上下文
- `config_name` 是配置包名称
- `config_item` 是配置项名称

如果前端脚本也要使用配置：

```html
<script>
  window.__PUB_CONFIG__ = {{ global_pubConfig | dump }};
</script>
```

使用建议：

- `__PUB_CONFIG__` 只是示例变量名
- 如果页面上有多个应用，建议带业务标识避免覆盖
- 业务代码里最好封装读取方法，不要到处直接读 `window`

本地验证：

- 本地开发默认读取 `sit`
- 预发页面读取 `prod_test`
- 线上页面读取 `prod`
- 本地联调通常先改 `sit`，再执行 `kjl dev`

## 非 PUB 项目接入配置包

非 PUB 项目使用 `@qunhe/config-client`。默认先回答“如何读取”，不要一上来进入写操作。

初始化 client：

```ts
import { StaticServerLocator } from '@qunhe/toad-client'
import { ConfigStandardStage, DefaultConfigClient, ConfigDefaultSource } from '@qunhe/config-client'

this.client = new DefaultConfigClient()

this.client = new DefaultConfigClient({
  stage: ConfigStandardStage.PROD,
  source: ConfigDefaultSource,
  serverLocator: new StaticServerLocator(),
})
```

说明：

- `stage` 默认是 `ConfigStandardStage.PROD`
- `source` 默认是 `ConfigDefaultSource`
- `serverLocator` 默认是 `StaticServerLocator` 实例

### 本地读取配置

```ts
const config = await this.client.getConfig(configName, stage)

const configs = await this.client.getConfigs(names, stage)
```

回答读取场景时，优先补齐：

- 当前代码在哪里初始化 `DefaultConfigClient`
- 配置包名是什么
- 读的是单包还是批量
- 当前 stage 是什么

## 找接入点

优先找这些位置：

- `package.json` 中与 PUB config 相关的依赖
- `src/app.*`
- `src/bootstrap.*`
- `src/main.*`
- `config/`
- `settings/`
- `services/config*`
- 与配置包名、配置项名相关的 import、hook、service、context

额外检查：

- PUB 项目：检查 `njk` 模板中的配置注入位置
- 非 PUB 项目：检查 `DefaultConfigClient` 初始化位置和 `getConfig/getConfigs` 调用位置

如果项目里找不到统一入口，就按“谁第一次读取配置包，谁就是接入点”的原则往上追。

## 梳理数据流转链路

默认链路：

```text
PUB Config 配置包(sit/prod_test/prod) -> 应用注入或微应用聚合 -> 本地运行时读取 -> 归一化/默认值合并 -> 页面/组件消费 -> 页面表现验证
```

分项目类型描述时：

- PUB 项目：配置包 -> PUB 应用注入 -> `njk` 注入 -> 页面运行时读取 -> 页面消费
- 非 PUB 项目：配置包 -> `DefaultConfigClient` -> `getConfig/getConfigs` -> 业务代码消费

浏览器端不再建议直接通过 HTTP 请求获取 config 数据。

## 本地联调闭环

默认按这个顺序执行：

1. 判断当前项目是 PUB 还是非 PUB。
2. 确认配置包名、配置项名、消费应用和页面入口。
3. 在平台侧把 `sit` 环境数据改成可观察的值。
4. PUB 项目检查应用注入和 `njk` 注入；非 PUB 项目检查 `DefaultConfigClient` 初始化和调用。
5. 启动本地项目。
6. 通过日志、Network、断点、页面表现至少验证一种。
7. 若未生效，优先排查环境、旧字段、默认值覆盖、缓存和消费时机。
