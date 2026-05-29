# 类型安全

## JavaScript 约定

这个包是普通 JavaScript。通过简单数据形状和显式运行时检查保持类型安全：

- `determineTargetTriple(platform, arch)` 返回受支持的 triple 或 `null`；
- caller 在构建路径前对 unsupported target 抛错；
- Windows 和非 Windows 的 binary name 显式构造。

## 路径安全

使用 `fileURLToPath(import.meta.url)` 和 `path.dirname()` 做 ESM directory
resolution。所有文件路径都使用 `path.join()`。

## 边界安全

包装层不负责校验 proxy-specific CLI options。它只检查平台支持和进程启动成功。

## 常见错误

- 在这个 JavaScript executable 中添加 TypeScript 语法。
- 用字符串拼接构建 vendored paths。
- 在 unsupported-platform check 前把 `targetTriple` 当成非空值。
