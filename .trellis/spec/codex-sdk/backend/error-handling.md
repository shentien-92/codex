# 错误处理

## 进程错误

`src/exec.ts` 在 CLI 边界捕获进程错误：

- 通过 `child.once("error", ...)` 保存 spawn error；
- 如果缺少 `stdin` 或 `stdout`，kill child 后失败；
- 流式读取 stdout JSONL 时收集 stderr chunks；
- stdout 关闭后等待 child exit，exit code 非零或存在 signal 时抛错；
- 在 `finally` 中关闭 `readline`、移除 listeners，并尝试 kill child。

错误信息应可执行。现有 process exit message 包含 `code <n>` 或 `signal <name>`，并
附带 stderr 内容。

## Stream parsing errors

`src/thread.ts` 会把每一行 JSONL 解析为 `ThreadEvent`。解析失败时，抛出包含 raw item
的 `Error`，并把 parse error 作为 `cause`。

当 stream 发出 `turn.failed` 时，先捕获 `ThreadError`，循环结束后再抛出，让 `run()`
调用方收到 rejected promise。

## Config serialization errors

`src/exec.ts` 在序列化时校验 config overrides：

- root config 必须是 plain object；
- keys 必须是非空字符串；
- `undefined` values 会跳过；
- `null` 会被拒绝；
- numbers 必须是 finite；
- arrays 和 nested objects 会序列化为 TOML literals。

不要静默 coercion 无效 config values。

## 常见错误

- 在 output-schema temp files 或 child processes cleanup 执行前提前抛错。
- 暴露非零 process exit 时丢失 stderr details。
- 把 `turn.failed` 转成 item，而不是让 `run()` reject。
