# 目录结构

## 包形态

`@openai/codex-responses-api-proxy` 位于
`codex-rs/responses-api-proxy/npm/`。

重要文件：

- `package.json` 声明 npm package 和 `codex-responses-api-proxy` bin。
- `bin/codex-responses-api-proxy.js` 解析并启动原生 binary。
- `README.md` 说明 npm 安装方式，并指向原生 proxy 文档。
- `vendor/` 包含在发布包中，保存按平台划分的预构建 binary。

## Binary 布局

包装层期望运行时路径形态为：

```text
vendor/<target-triple>/codex-responses-api-proxy/codex-responses-api-proxy[.exe]
```

支持的 target triple 与 `determineTargetTriple()` 中对 Linux、macOS、Windows
x64/arm64 的映射一致。

## 真实示例

- Target-triple 映射：
  `codex-rs/responses-api-proxy/npm/bin/codex-responses-api-proxy.js`
- Package `files` 列表：`codex-rs/responses-api-proxy/npm/package.json`
- Workspace 成员关系：`pnpm-workspace.yaml`

## 常见错误

- 原生 build 改了 vendor 布局，却没有同步更新 npm wrapper 的路径构造。
- 新增运行时文件，却忘了这个包只发布 `bin` 和 `vendor`。
- 把这个包当成 proxy 实现本身；实现位于 `codex-rs/responses-api-proxy/`。
