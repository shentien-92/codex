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

## 常见风险

- 只改了 API 类型，忘了 SDK/event 类型。
- 只改了实现，忘了 schema fixture 或 generated TypeScript。
- 底层错误被吞掉，用户只看到 generic failure。
- UI 或 caller 自己猜默认值，和后端默认值不一致。

---

## 输出要求

跨层改动完成前，应能给出：

- 字段从输入到输出的完整路径；
- 每一层的类型和默认值；
- 错误矩阵；
- 覆盖关键边界的测试列表。
