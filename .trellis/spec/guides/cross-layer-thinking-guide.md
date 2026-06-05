# 跨层思考指南

> 用于在功能跨多个层时梳理数据、错误和类型边界。

---

## 何时打开

- 功能触达 API、service、client、UI、storage 等 3 层以上
- 新增或修改 request/response payload
- 同一个字段需要穿过多个层
- 错误需要从底层传到用户可见层
- 不确定逻辑应该放在哪一层

---

## 数据流检查

写路径：

```text
UI / caller -> API / command -> service / domain -> storage / external system
```

读路径：

```text
storage / external system -> service / domain -> API / command -> UI / caller
```

逐层确认：

- 字段名是否一致？
- 类型是否一致？
- optional/null/undefined 语义是否一致？
- 默认值在哪一层设置？
- 校验失败在哪一层发生？
- 错误如何映射给调用方？

---

## 边界归属

把逻辑放在最拥有该知识的层：

- Wire format 属于 API/protocol 边界。
- 业务规则属于 domain/service。
- 存储细节属于 storage/repository。
- 展示和交互状态属于 UI/caller。
- CLI 参数序列化属于 process adapter 或 command layer。

如果一个判断需要多个层的信息，先考虑是否缺少中间类型或 adapter。

---

## Contract 更新

跨层 contract 改动必须同步：

- Rust/TypeScript 类型
- schema 或 generated fixtures
- README/API docs
- integration tests
- snapshots（如果用户可见输出变化）

---

## 错误传播

为每类错误明确：

- 原始错误在哪里产生；
- 是否保留 cause/detail；
- 哪一层负责转换成用户可见消息；
- 测试断言哪个边界的错误形态。

---

## 多入口共享前置动作

当多个 UI 命令、快捷入口或事件最终调用同一个跨层动作时，先列入口矩阵，不要只修当前报错的入口。

逐项确认：

- 每个入口是否有相同的前置动作，例如重载 config、刷新权限、切换 cwd、重建 client、读取持久化状态。
- 同名或同义入口是否存在于不止一层，例如 TUI slash command、app-server RPC、CLI/picker adapter。
- 前置动作是否可能失败、阻塞、递归、消耗大量栈或触发外部 IO。
- 前置动作失败时，是用户可见错误、非 fatal warning，还是会让主循环退出。
- 修复时是否删掉或收敛了共享前置动作，而不是只跳过某一个命令。

复发信号：

- 同类崩溃先在 `/new` 出现，之后又在 `/fork`、`/side`、`/btw` 出现。
- 日志显示业务 RPC 还没发出，进程已经退出。
- 单入口测试通过，但真实 TUI/主循环仍然崩溃。
- TUI 入口修复后，app-server 同名 RPC 仍然重走旧的 config reload 或 session rebuild 路径。

这类问题优先按“共享前置动作的归属错误”处理。只有在证明前置动作本身必须存在后，才考虑给它单独扩栈、后台化或降级错误。

---

## 常见风险

- 只改了 API 类型，忘了 SDK/event 类型。
- 只改了实现，忘了 schema fixture 或 generated TypeScript。
- 底层错误被吞掉，用户只看到 generic failure。
- UI 或 caller 自己猜默认值，和后端默认值不一致。
- 只修一个入口的表现层错误，遗漏同一前置动作上的其他入口。

---

## 输出要求

跨层改动完成前，应能给出：

- 字段从输入到输出的完整路径；
- 每一层的类型和默认值；
- 错误矩阵；
- 覆盖关键边界的测试列表。
