# 类型安全

## JavaScript 约定

`@openai/codex` 是普通 JavaScript，不是 TypeScript。通过清晰的数据形状和控制流
收窄值：

- 用常量对象映射 target triple；
- 在检查前，用 `null` 表示不支持的平台；
- resolver helper 返回结构化对象，例如 `{ binaryPath, pathDir }`。

## 运行时校验

启动前要校验平台和 binary 解析：

- 无法推导 target triple 时抛错；
- target triple 没有 package mapping 时抛错；
- package-layout 和 legacy-layout binary 都不存在时抛错。

## 路径安全

路径使用 `path.join()`；ESM 中的 `__dirname` 等价写法使用
`fileURLToPath(import.meta.url)`。Windows 可执行文件后缀保持显式：
`process.platform === "win32" ? "codex.exe" : "codex"`。

## 常见错误

- 在检查前假设对象查找结果一定存在。
- 用字符串拼接构建路径。
- 在这个 JavaScript 包里添加 TypeScript-only 语法。
