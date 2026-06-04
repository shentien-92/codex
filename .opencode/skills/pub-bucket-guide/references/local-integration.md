# 本地接入参考

## 目录

- 判断项目类型
- PUB 项目接入
- 运行时消费
- 调试与验证
- 非 PUB 场景

## 判断项目类型

先判断当前项目是否为 PUB 项目：

- 根目录是否存在 `def.config.js`
- 是否存在 `.pubrc.js`
- 是否存在与 `pubrc` 同级的 `njk` 入口
- 是否通常通过 `kjl dev` 启动

处理原则：

- PUB 项目：优先走“平台勾选注入 + `njk` 注入 + 业务代码消费”路径
- `@qunhe/bucket-sdk`：除了读取分桶数据，还内置了埋点，方便分桶维护方感知 SDK 的使用情况并制定治理计划；官方建议与 `njk` 注入模式配合使用，不建议只单独使用 SDK
- 非 PUB 项目：优先告知可通过试验页面提供的接口直接请求结果，或继续查询 `bucket-sdk`

## PUB 项目接入

推荐结论：

- 官方推荐方式是 `PUB 注入 global_pubBucket -> njk 注入 -> @qunhe/bucket-sdk / 业务代码配合消费`
- `@qunhe/bucket-sdk` 的价值除了读数据，更在于埋点可观测性和治理支撑
- 不建议只单独使用 SDK；应建立在已有注入链路之上配合使用

平台侧先做：

1. 在 PUB 应用中勾选注入对应的分桶包
2. 保存后确认模板上下文里有 `global_pubBucket`

模板侧推荐写法：

```njk
<script>
  window.__PUB_BUCKET__ = {{ global_pubBucket | dump }};
</script>
```

推荐在已有注入基础上结合 SDK 封装：

```ts
import BucketSDK from '@qunhe/bucket-sdk';

const bucketSDK = new BucketSDK({
  appKey: 'your_app_key',
  bucketVarName: '__PUB_BUCKET__',
});
```

建议：

- 优先在业务里统一约定一个变量名，例如 `window.__PUB_BUCKET__`
- 推荐业务层封装读取方法，不要在组件里到处直接读 `window`
- 推荐把 SDK 用于埋点、使用情况感知、治理支撑或统一能力封装
- 不要把 SDK 写成脱离注入链路的唯一接入路径

## 运行时消费

推荐数据链路：

```text
分桶应用 -> 试验/版本/白名单/标签 -> PUB 注入 global_pubBucket -> njk 写入 window.__PUB_BUCKET__ -> @qunhe/bucket-sdk / 业务代码消费 -> 页面行为/埋点消费
```

业务代码中建议封装：

- 当前试验是否存在
- 当前命中的版本 key
- 未命中时的默认行为
- SDK 的埋点、使用情况感知或能力封装

## 调试与验证

默认按这个顺序联调：

1. 先确认当前 PUB 应用已经勾选了分桶包
2. 选择一个容易观察的试验和版本
3. 如有需要，先把自己加入白名单，确保稳定命中
4. 启动 `kjl dev`
5. 在浏览器里检查 `window.__PUB_BUCKET__` 是否已注入
6. 检查业务代码读取到的试验数据和版本结果
7. 验证页面逻辑是否随版本切换而变化

至少做一种验证：

- 浏览器控制台看全局变量
- 页面行为验证
- 断点看版本判断逻辑
- 埋点或结果页验证

## 非 PUB 场景

如果不是 PUB 项目，不要硬套 `global_pubBucket`。

优先建议：

- 通过试验页面说明中的接口直接请求试验结果
- 如需统一 SDK 方案，优先查 `@qunhe/bucket-sdk` 文档

浏览器端不要在没有明确约定的情况下自己发散实现分桶协议。
