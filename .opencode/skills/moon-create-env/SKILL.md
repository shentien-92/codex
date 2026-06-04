---
name: moon-create-env
description: 创建 Moon 测试环境，支持配置环境变量和 Java Options
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

创建 Moon 测试环境，支持配置环境变量和 Java Options。

## 前置要求

`@qunhe/moon-cli` 是一个基于 Node.js 的命令行工具，使用前请确保：
- Node.js 版本 >= 20
- 已配置公司内网 npm 仓库

---

## 基础创建

当用户仅需创建环境，无需自定义环境变量或 Java Options 时，使用以下命令：

```bash
npx -y @qunhe/moon-cli@latest create env <name> --yes
```

**参数说明：**
- `<name>`: 环境名称（必填）
- `--yes`: 跳过交互式确认，自动确认创建

**注意：** 如果仓库包含多个应用，会触发多应用错误，此时需要使用 `--app` 参数指定应用：

```bash
npx -y @qunhe/moon-cli@latest create env <name> --app <app-name> --yes
```

## 创建环境并配置环境变量

当用户需要自定义环境变量时，**必须**按以下流程操作：

### 步骤 1：预览默认环境变量（必须）

**重要：在配置任何环境变量之前，必须先执行预览操作，以了解当前环境的默认配置。**

```bash
npx -y @qunhe/moon-cli@latest create env <name> --dry-run
```

`--dry-run` 参数会输出即将创建的环境配置预览，包括所有环境变量，但不会实际执行创建操作。

#### 多应用场景处理

如果预览时遇到如下错误：

```
Error: 仓库 git@gitlab.qunhequnhe.com:moon/moongroup/foobar-soa.git 存在多个应用，请通过 --app 参数指定具体应用

┌───────────────┬──────────────────────────────────────┬─────────────────────────────────────────────────────┐
│ Name          │ UUID                                 │ Tag                                                 │
├───────────────┼──────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ foobar-soa    │ 4f337ba9-f703-11ea-85d0-ca37583a01ba │ cop.kujiale|owt.ep|pdl.devops|service.foobar-soa    │
├───────────────┼──────────────────────────────────────┼─────────────────────────────────────────────────────┤
│ env-list-demo │ 6b1defe8-e2e0-11eb-ab1b-ba30863141c9 │ cop.kujiale|owt.ep|pdl.devops|service.env-list-demo │
└───────────────┴──────────────────────────────────────┴─────────────────────────────────────────────────────┘
```

**处理流程：**

1. **询问用户**：向用户展示错误信息中的应用列表，询问需要部署哪个应用
2. **重新预览**：根据用户选择，使用 `--app` 参数指定应用名称重新执行预览

```bash
npx -y @qunhe/moon-cli@latest create env <name> --app <app-name> --dry-run
```

**参数说明：**
- `--app`: 指定应用名称（从错误信息表格的 `Name` 列中选择）

**重要：** 如果在预览阶段使用了 `--app` 参数，后续真正执行创建环境命令时，**必须同样携带 `--app` 参数**，否则会再次遇到多应用错误。

### 步骤 2：配置自定义环境变量

根据预览结果和用户需求，使用 `--env-var` 参数传递环境变量：

```bash
npx -y @qunhe/moon-cli@latest create env <name> \
  --env-var JAVA_OPTIONS="-Doption1=value1 -Doption2=value2" \
  --env-var ANOTHER_ENV="value" \
  --yes
```

**如果预览时使用了 `--app` 参数，创建命令也需要携带该参数：**

```bash
npx -y @qunhe/moon-cli@latest create env <name> \
  --app <app-name> \
  --env-var JAVA_OPTIONS="-Doption1=value1 -Doption2=value2" \
  --env-var ANOTHER_ENV="value" \
  --yes
```

**参数说明：**
- `--app`: 指定应用名称（如果在预览阶段使用了此参数，创建时必须携带）
- `--env-var`: 可多次使用，每次指定一个环境变量，格式为 `KEY="VALUE"`
- `--yes`: 确认执行创建操作

## 常用环境变量配置

### JAVA_OPTIONS

公司主要技术栈为 Java，大部分应用通过 `JAVA_OPTIONS` 配置运行时参数。以下为常见配置场景：

#### 设置 SOA 版本

当用户需要指定服务版本时：

```bash
npx -y @qunhe/moon-cli@latest create env <name> \
  --env-var JAVA_OPTIONS="-Dqunhe.service.version=<version>" \
  --yes
```

**示例：** 创建 `abc` 环境并将 SOA 版本设置为 `abc`

```bash
npx -y @qunhe/moon-cli@latest create env abc \
  --env-var JAVA_OPTIONS="-Dqunhe.service.version=abc" \
  --yes
```

#### 设置 Toad 环境阶段

```bash
--env-var JAVA_OPTIONS="-Dqunhe.toad.stage=sit"
```

可选值：`dev`、`sit` 等

#### 设置 Stage

```bash
--env-var JAVA_OPTIONS="-Dstage=dev"
```

#### 设置 Spring Profile

```bash
--env-var JAVA_OPTIONS="-Dspring.profiles.active=test"
```

#### 组合多个参数

多个 JVM 参数可在同一 `JAVA_OPTIONS` 中以空格分隔组合：

```bash
npx -y @qunhe/moon-cli@latest create env <name> \
  --env-var JAVA_OPTIONS="-Dqunhe.toad.stage=sit -Dstage=dev -Dspring.profiles.active=test" \
  --env-var CUSTOM_ENV="custom_value" \
  --yes
```

## 注意事项

1. **必须先预览**：在创建带环境变量的环境时，必须先执行 `--dry-run` 预览默认配置，确保了解当前环境的配置状态
2. **多应用场景**：当仓库包含多个应用时，必须通过 `--app` 参数明确指定目标应用。如果预览阶段使用了 `--app` 参数，后续真正创建环境时也必须携带该参数，否则会再次遇到多应用错误
3. **参数优先级**：通过 `--env-var` 显式指定的环境变量会覆盖默认配置
4. **参数合并**：如需保留预览中的部分默认环境变量并同时添加新参数，需手动合并到 `JAVA_OPTIONS` 中
5. **环境名称规范**：建议使用有意义的环境名称，如功能分支名或任务 ID，便于识别和管理

---

## 常见问题

### 未配置内网 npm 仓库

**错误信息：**

```
npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/@qunhe%2moon-cli - Not found
```

**解决方案：** 执行以下命令切换到公司内网 npm 仓库：

```bash
npm config set registry http://npm-registry.qunhequnhe.com
```

### npx 命令沙箱权限问题

**错误信息：**

```
Error: Failed to get access token: Error: EPERM: operation not permitted, mkdir '/Users/someone/.moon'
```

**解决方案：** 请选择以下任一方式：
- 关闭命令沙箱功能
- 将 `npx -y @qunhe/moon-cli@latest` 添加到沙箱白名单
