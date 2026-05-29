# 日志规范

## 运行时日志

SDK 正常运行时不应打印日志。它是 library，应返回结构化数据或抛错，而不是写
stdout/stderr。

示例：

- `Thread.run()` 返回 `{ items, finalResponse, usage }`。
- `Thread.runStreamed()` 返回 `ThreadEvent` async generator。
- `CodexExec.run()` yield 原始 JSONL lines，并抛出 process errors。

## CLI 输出边界

SDK 启动 `codex exec --experimental-json`，并按行读取 stdout。不要在 SDK path 中加入
console output；这可能破坏只期望 structured events 或 errors 的消费者。

## 测试和 samples

Samples 可以像 `sdk/typescript/README.md` 一样用 `console.log()` 展示用法。Tests 应
断言 returned values、request bodies、spawn args 和 errors，而不是依赖 logs。

## 常见错误

- 在 async generators 内添加 debug logs。
- 打印 caught errors 后再重新 throw。
- 打印 request payloads 或 environment variables，导致 secrets 泄漏。
