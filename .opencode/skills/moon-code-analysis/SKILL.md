---
name: moon-code-analysis
description: Java 静态代码扫描，检测新增代码质量问题
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

运行 Java 静态代码扫描分析，检测新增代码中的质量问题。

**规则集与远端 CI 完全一致**：本地扫描使用的规则配置与 Moon 平台 CI 流水线保持同步，确保本地检查结果与 CI 结果一致。

## 前置要求

`@qunhe/moon-cli` 是一个基于 Node.js 的命令行工具，使用前请确保：
- Node.js 版本 >= 20
- 已配置公司内网 npm 仓库
- JDK 版本 >= 17（用于运行 Maven 静态扫描插件）

---

## 基础命令

### 运行静态代码扫描

对当前分支相对于默认分支（一般是 master）新增的 Java 代码进行静态扫描：

```bash
npx -y @qunhe/moon-cli@latest run code-analysis
```

该命令会：
1. 自动检测当前仓库的默认分支
2. 对比当前分支与默认分支的差异
3. 只扫描新增的 Java 代码行
4. 输出检测到的质量问题

### 可选参数

**--min-priority**

设置最小优先级阈值，只显示大于指定优先级的问题：

```bash
npx -y @qunhe/moon-cli@latest run code-analysis --min-priority high
```

可选值：
- `high` - 只显示高优先级问题
- `medium_high` - 显示高和中高优先级问题
- `medium` - 显示高、中高、中优先级问题（默认）
- `medium_low` - 显示高、中高、中、中低优先级问题
- `low` - 显示所有优先级问题

**--no-fetch**

不自动从远端仓库拉取默认分支：

```bash
npx -y @qunhe/moon-cli@latest run code-analysis --no-fetch
```

适用于网络受限或已确认本地分支信息足够新的场景。

**--no-staged**

不扫描已添加进暂存区的文件（已 git add 但尚未 commit 的文件）：

```bash
npx -y @qunhe/moon-cli@latest run code-analysis --no-staged
```

默认情况下会扫描暂存区的文件，使用此参数可只扫描已提交的变更。

**--verbose**

输出详细日志，用于调试：

```bash
npx -y @qunhe/moon-cli@latest run code-analysis --verbose
```

---

## 查询规则详情

当扫描结果中发现某个规则触发的问题，可以使用以下命令查询该规则的详细说明：

```bash
npx -y @qunhe/moon-cli@latest get code-analysis-rule <ruleKey>
```

**参数说明：**
- `<ruleKey>`: 规则的唯一标识符，如 `findbugs:VR_UNRESOLVABLE_REFERENCE`、`java:S1258`、`pmd:UselessParentheses` 等

该命令会输出：
- 规则名称、类型、优先级
- 规则详细描述
- 如何压制（suppress）该规则
- 规则属性配置（如有）

---

## 输出格式

扫描结果以 JSON 格式输出，结构如下：

```json
{
  "files": [
    {
      "name": "src/main/java/com/example/SomeClass.java",
      "issues": [
        {
          "ruleKey": "findbugs:NM_METHOD_NAMING_CONVENTION",
          "priority": "medium",
          "type": "code smell",
          "message": "方法命名不符合规范",
          "position": {
            "startLine": 10,
            "endLine": 10,
            "startColumn": 5,
            "endColumn": 20
          }
        }
      ]
    }
  ]
}
```

---

## JDK 配置

静态扫描需要 JDK 17 及以上版本。moon-cli 支持两种方式配置 JDK：

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

### JDK 版本不足

**错误信息：**

```
Error: 未找到 17 及以上的 JDK，请在 ~/.moon/config 中添加配置...
```

**解决方案：** 安装 JDK 17+ 或在 `~/.moon/config` 中配置 JDK 17 路径。

### 没有检测到变更文件

**错误信息：**

```
Error: 没有检测到有新增行的 .java 文件
```

**原因：** 当前分支相对于默认分支没有新增 Java 代码行。

**解决方案：** 确保当前分支有 Java 代码变更，或检查是否在正确的分支上。

### 找不到 JDK 8 的 tools.jar

**错误信息：**

```
[ERROR] Failed to execute goal on project xxx: Could not resolve dependencies for project xxx: Could not find artifact com.sun:tools:jar:1.8 at specified path C:\Program Files\Java\jdk-17.0.2/../lib/tools.jar
```

**原因：** 某些老项目依赖了 JDK 8 的 `com.sun:tools:jar:1.8`，该依赖通过 `${java.home}/../lib/tools.jar` 路径解析。当使用 JDK 17+ 运行 Maven 时，该路径下不存在 `tools.jar`，导致依赖解析失败。

**解决方案：** moon-cli 已支持自动处理此问题——会自动查找本地 JDK 8 并将其 `lib/tools.jar` 软链接到 JDK 17+ 对应目录。确保以下任一条件满足即可：

- 在 `~/.moon/config` 中配置了 JDK 8 路径：
  ```json
  {
    "javaHome": {
      "8": "/Path/to/home/of/jdk-1.8",
      "17": "/Path/to/home/of/jdk-17"
    }
  }
  ```
- 系统中 `mvn -version` 使用的默认 JDK 为 8（moon-cli 会自动从 Maven 输出中解析 JDK 8 路径）

如果自动软链接失败，可手动创建软链接：
```bash
ln -s /path/to/jdk8/lib/tools.jar /path/to/jdk17/../lib/tools.jar
```

### npx 命令沙箱权限问题

**错误信息：**

```
Error: Failed to get access token: Error: EPERM: operation not permitted, mkdir '/Users/someone/.moon'
```

**解决方案：** 请选择以下任一方式：
- 关闭命令沙箱功能
- 将 `npx -y @qunhe/moon-cli@latest` 添加到沙箱白名单

---

## 使用场景

1. **提交前检查**：在提交代码前运行静态扫描，确保新增代码质量
2. **MR 检查**：在发起 Merge Request 前检查变更代码是否有问题
3. **规则学习**：使用 `get code-analysis-rule` 命令了解具体规则的含义和修复方法
4. **问题定位**：结合 `--verbose` 参数排查扫描过程中的问题

---

## 重要说明

- **主动询问修复**：如果用户未主动要求，你可以主动询问用户是否需要帮助修复静态扫描发现的问题
- **禁止 SuppressWarnings**：除非经过用户明确允许，否则禁止使用 `@SuppressWarnings` 注解来抑制代码质量问题
