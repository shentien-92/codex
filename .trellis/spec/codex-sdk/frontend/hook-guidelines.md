# Hook 规范

## 概览

SDK 没有 React hooks。这里相关的异步模式是 `runStreamed()` 返回值中的
`AsyncGenerator<ThreadEvent>`。

## Streaming 模式

`Thread.runStreamed()` 返回 `{ events }`，其中 `events` 是 async generator。消费者代码
应使用：

```typescript
for await (const event of events) {
  // switch on event.type
}
```

Event stream 应通过 `event.type` 做 discriminated handling。新增 event 时，要同步更新
`events.ts`、tests，以及相关 README/sample handling。

## Turn 生命周期

`Thread.run()` 是基于同一条 internal stream 的 buffered convenience API。它收集
completed items、跟踪最终 agent message、在 `turn.completed` 时记录 `usage`，并在
`turn.failed` 时 reject。

不要创建绕过 `runStreamedInternal()` 的第二条执行路径。

## Cancellation

Cancellation 通过 `TurnOptions.signal` 传给 `CodexExec.run()`，再传给 `spawn()`。保持这条
abort 行为边界。

## 常见错误

- 向这个包导出 React-specific `useCodex`。
- Samples 中用 stringly typed conditionals 处理 streamed events；`switch
(event.type)` 更清晰。
- Streams abort 时忘记清理 temporary output schema files。
