# 组件规范

## 概览

SDK 没有 UI components。与之对应的消费者可见单元是小型 classes 和 typed result
objects。

## Class 结构

保持 public class model 简单：

- `Codex` 拥有全局 SDK options，并创建或恢复 threads。
- `Thread` 拥有 per-conversation state 和 turn execution。
- `CodexExec` 作为 process adapter 留在 public API 后面。

除非存在无法放进现有单元的清晰 public abstraction，否则不要新增 manager classes。

## Method 形态

遵循现有方法约定：

- `startThread(options?: ThreadOptions): Thread`
- `resumeThread(id: string, options?: ThreadOptions): Thread`
- `run(input: Input, turnOptions?: TurnOptions): Promise<Turn>`
- `runStreamed(input: Input, turnOptions?: TurnOptions): Promise<StreamedTurn>`

优先扩展 option objects，不要新增 positional boolean 或 nullable parameters。

## 组合方式

组合通过 typed options 和 discriminated unions 表达，不使用 UI children 或 render
props。例如，`Input` 是 prompt string，或者由 `{ type: "text" | "local_image", ... }`
组成的数组。

## 可访问性和样式

SDK 没有样式或可访问性层。应用可访问性属于 consuming applications。

## 常见错误

- 从 SDK 导出 React component 或 hook。
- 引入 positional booleans，而不是扩展 option objects。
- 返回松散对象，而不是命名的 exported result types。
