---
name: moon-jar-source
description: 从 Maven 依赖的 jar 中获取 Java 类/方法源码，支持内部类和反编译
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

从 Maven 项目的依赖 jar 中获取指定 Java 类的源代码。支持提取整个类、指定方法、内部类，无 sources.jar 时自动反编译 class 文件。

## 前置要求

`@qunhe/moon-cli` 是一个基于 Node.js 的命令行工具，使用前请确保：
- Node.js 版本 >= 20
- 已配置公司内网 npm 仓库
- JDK 17+（用于运行 Vineflower 反编译），可在 `~/.moon/config.json` 中配置 `javaHome`
- 当前目录是一个 Maven 项目（包含 pom.xml）

---

## 基础命令

```bash
npx -y @qunhe/moon-cli@latest get jar-source <className> [methodName]
```

### 参数说明

**className**（必填）

Java 全限定类名，如 `com.fasterxml.jackson.databind.ObjectMapper`

支持内部类，使用 `.` 或 `$` 分隔：
- `com.fasterxml.jackson.databind.ObjectMapper.DefaultTyping`
- `com.fasterxml.jackson.databind.ObjectMapper$DefaultTyping`
- `com.google.common.collect.ImmutableMap.Builder`（多层嵌套）

**methodName**（可选）

方法名，指定后仅输出该方法的源代码。

特性：
- 支持重载方法，会输出所有同名方法
- 支持构造函数（使用类名作为方法名）
- 提取结果包含方法前的 Javadoc 注释和注解

---

## 可选参数

**--verbose**

输出详细日志，用于调试：

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper --verbose
```

**--rebuild-cache**

强制重建索引缓存（同时更新 SNAPSHOT 依赖）：

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper --rebuild-cache
```

适用于依赖版本变更后索引缓存过期的场景。

---

## 使用示例

### 获取完整类源码

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper
```

### 获取指定方法

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper readValue
```

### 获取内部类

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper.DefaultTyping
```

### 获取内部类的方法

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper.DefaultTyping values
```

### 获取构造函数

```bash
npx -y @qunhe/moon-cli@latest get jar-source com.fasterxml.jackson.databind.ObjectMapper ObjectMapper
```

---

## 工作原理

1. 解析项目所有 pom.xml，通过 Maven 获取编译期依赖的 jar 列表
2. 构建类名到 jar 的索引（会缓存到 `.moon/cache/`，pom 未变时直接命中）
3. 优先从 sources.jar 提取源码；无 sources.jar 时自动使用 Vineflower 反编译 class 文件
4. 如果指定了内部类，逐层从源码中提取对应的内部类/接口/枚举
5. 如果指定了方法名，从源码中提取所有同名方法（含注释和注解）

---

## 使用场景

1. **阅读依赖源码**：快速查看第三方库或二方包的实现
2. **调试问题排查**：查看依赖类的具体实现细节
3. **代码理解**：了解上游接口/抽象类的默认实现
4. **反编译**：当 sources.jar 不可用时，自动反编译获取可读源码

---

## JDK 配置

反编译功能需要 JDK 17 及以上版本。moon-cli 支持两种方式配置 JDK：

### 方式 1：自动检测

如果当前环境已配置 JDK 17+（可通过 `mvn -version` 检测），无需额外配置。

### 方式 2：配置文件指定

在 `~/.moon/config` 文件中指定 JDK 路径：

```json
{
  "javaHome": {
    "17": "/Path/to/home/of/jdk-17"
  }
}
```

如果未找到合适的 JDK，命令会报错并提示配置方法。

---

## 常见问题

### 未找到类的源码

**错误信息：**

```
Error: 未找到 com.fasterxml.jackson.databind.ObjectMapper 的源码。可能原因：
  - 该类不在项目的编译期依赖中
  - 类名拼写有误
提示：可尝试运行 mvn dependency:resolve -Dclassifier=sources 下载 sources.jar
```

**解决方案：**
- 检查类名拼写是否正确
- 确认该类在项目的编译期依赖中（而非 test/provided scope）
- 使用 `--rebuild-cache` 参数重建索引
- 运行 `mvn dependency:resolve -Dclassifier=sources` 下载 sources.jar

### 索引缓存过期

**场景：** 修改了 pom.xml 中的依赖版本后，搜索结果不正确。

**解决方案：** 添加 `--rebuild-cache` 参数重建索引。

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
