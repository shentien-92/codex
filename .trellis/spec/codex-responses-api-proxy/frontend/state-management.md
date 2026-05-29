# 状态管理

## 运行时状态

状态只在启动时计算一次：

- 从 `process.platform` 和 `process.arch` 得到的 `targetTriple`；
- `vendorRoot`、`archRoot` 和 `binaryPath`；
- 描述 child exit code 或 signal 的 `childResult`。

这些状态应保持在 executable module 内部。不要在 npm wrapper 中引入持久化配置或缓存。

## 参数状态

直接把 `process.argv.slice(2)` 转发给原生 proxy。包装层不应解析、重排或校验 proxy
CLI 参数。

## 错误状态

不支持的平台/架构组合应在 spawn 前用现有 `Unsupported platform: ...` 错误失败。
Spawn failures 应通过 `error` handler 暴露。

## 常见错误

- 添加与原生 binary 不一致的 wrapper-specific defaults。
- 修改会影响命令调用方的 process-global state。
- 吞掉 spawn errors，导致进程挂住。
