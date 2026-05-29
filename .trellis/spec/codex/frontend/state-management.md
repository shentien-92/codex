# 状态管理

## 运行时状态

这个包里的状态都是普通的进程内 JavaScript 状态：

- 从 platform 和 architecture 推导出的 `targetTriple`；
- 从 optional package metadata 或本地 `vendor/` 解析出的 `nativePackage`；
- 用于构造 child environment 的 `additionalDirs` 和 `updatedPath`；
- 描述原生进程按 exit code 还是 signal 退出的 `childResult`。

这些状态应在启动时短生命周期计算完成。不要引入超出包装进程设置范围的全局可变状态。

## 环境状态

从 `process.env` 构造 child process environment，然后添加 package-managed 变量和
`PATH` 更新。除非有充分理由，不要直接修改 `process.env`；现有代码会为 `spawn()`
构造单独的 `env` 对象。

## 错误状态

不支持的平台或缺失 binary 解析应快速失败，并给出可执行的错误，例如
`Unsupported platform: ...` 和 `Missing optional dependency ... Reinstall Codex:
...`。

## 常见错误

- 跨调用缓存 target resolution；每个 Node 进程都是一次新的包装层调用。
- 全局修改 `process.env.PATH`，而不是把显式 `env` 传给 child process。
- 吞掉 missing-binary 错误，导致 `spawn()` 报出更难理解的信息。
