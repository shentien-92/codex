---
name: moon-jar-deploy
description: 二方包发版全流程 - 部署发版（变更收集与变更日志生成使用 moon-jar-changelog 技能）
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

# 二方包发版工作流

本技能提供二方包发版的完整工作流，确保 **变更日志先于发版提交**，版本标签与发版保持一致。

## 整体流程

```
发版前准备
  ├── 确认发版分支 (master / release/*)
  ├── 确认目标版本号
  └── 确保本地代码已提交并推送到远程仓库

Step 1: 获取二方包信息
  ├── 调用 jar-info 获取命令信息
  └── 根据 command 判断流程类型

正式包发布流程：
Step 2: 收集变更（使用 moon-jar-changelog 技能）
Step 3: 生成并提交变更日志（使用 moon-jar-changelog 技能）
Step 4: 打标签
  ├── 仅当 command 不包含 release:perform / release:prepare 时执行
  ├── 创建版本标签
  └── 推送到远程

Step 5: 部署二方包
  ├── 执行 jar-deploy 命令
  ├── 等待流水线完成
  └── 确认部署成功

测试包发布流程：（跳过 Step 3）
Step 1: 获取二方包信息
Step 2: 收集变更（用于 description 描述）
Step 4: 打标签（如需要）
Step 5: 部署二方包
```

---

## 前置要求

`@qunhe/moon-cli` 是一个基于 Node.js 的命令行工具，使用前请确保：
- Node.js 版本 >= 20
- 已配置公司内网 npm 仓库

---

## Step 1：获取二方包信息

### 调用 jar-info

```bash
npx -y @qunhe/moon-cli@latest get jar-info
```

该命令返回当前仓库关联的二方包组信息，包含：
- `command` - 部署命令

### 根据 command 判断流程类型

| command 类型 | 应走流程 |
| :--- | :--- |
| 包含 `release:perform` 或 `release:prepare` | **Maven Release 模式**：打标签、改版本号由 Maven 自动完成 |
| 其他命令（如 `mvn deploy`、`mvn -DskipTests deploy` 等） | **标准模式**：需要手动打标签、改版本号 |

### Maven Release 模式 - 检验 SCM 配置

如果判断为 Maven Release 模式，必须检验 `pom.xml` 中的 `<scm>` 配置：

```bash
# 检查 pom.xml 中是否包含 <scm> 标签
grep -A5 '<scm>' pom.xml
```

**必须满足以下条件：**

1. **必须包含 `<scm>` 标签**
2. **`<url>` 必须使用 SSH 格式**，格式为：
   ```
   git@gitlab.qunhequnhe.com:<group>/<repo>.git
   ```
   例如：
   ```xml
   <scm>
       <url>git@gitlab.qunhequnhe.com:moon/moongroup/foobar-soa.git</url>
   </scm>
   ```

**如果不满足条件，需要修改 pom.xml：**

1. 如果缺少 `<scm>` 标签，在 `<project>` 下添加：
   ```xml
   <scm>
       <url>git@gitlab.qunhequnhe.com:GROUP/REPO.git</url>
   </scm>
   ```
   将 `GROUP` 和 `REPO` 替换为实际的项目组名和仓库名。

2. 如果 `<url>` 格式不正确（如使用 https 格式），修改为 git@ 格式：
   ```bash
   # 将 https://gitlab.qunhequnhe.com/xxx 改为 git@gitlab.qunhequnhe.com:xxx
   ```

3. 提交修改：
   ```bash
   git add pom.xml
   git commit -m "[scm] configure scm for maven release"
   git push
   ```

**警告：** 未配置正确 SCM 的情况下执行 `release:prepare` 会失败。

---

## Step 2-3：收集变更与生成变更日志

**使用 moon-jar-changelog 技能完成以下步骤：**
- 收集变更（确定基准版本、获取变更列表、按 Keep a Changelog 分类）
- 生成并提交变更日志

详见 moon-jar-changelog 技能文档。

---

## 测试包发布流程

如果用户明确说明是**发布测试包**，则跳过 Step 3（生成变更日志），直接进入后续步骤。

### 简化流程

```
发版前准备
  ├── 确认发版分支
  ├── 确保本地代码已提交并推送到远程仓库
  └── 确认是测试包发布

Step 1: 获取二方包信息
  ├── 调用 jar-info 获取命令信息
  └── 判断是否需要自定义 command

Step 2: 收集变更
  └── 使用 moon-jar-changelog 技能收集变更，用于 description 描述改动点

Step 4: 打标签（如需要）
  └── 参见 Step 4 说明

Step 5: 部署二方包
  ├── 特别注意自定义 command（见下方说明）
  ├── 执行 jar-deploy 命令
  ├── 等待流水线完成
  └── 确认部署成功
```

### 测试包 vs 正式包区别

| 场景 | 是否需要变更日志 | 是否需要打标签 | Command |
| :--- | :--- | :--- | :--- |
| 正式包发布 | ✅ 需要 | ✅ 需要 | 默认 command |
| 测试包发布 | ❌ 跳过 | ⚠️ 如需要 | 可能需要自定义 |

### 测试包注意事项

**描述要求**：测试包虽然没有 CHANGELOG，但 `--description` 必须像 CHANGELOG 一样说明改动点，便于后续变更日志汇总。

示例：
```bash
npx -y @qunhe/moon-cli@latest create jar-deploy --command="mvn -B -DskipTests deploy" --description="新增 XX 功能；修复 XX 问题" --yes
```

如果 jar-info 返回的默认 command 包含 `release:perform` 或 `release:prepare`：
1. **不能使用默认 command**，否则会执行正式发版流程
2. 需要传入自定义的 `--command` 参数
3. 必须向用户确认 command 是否正确

**示例场景：**
- 用户说"发布测试包"
- jar-info 返回默认 command: `mvn -B -Darguments="-DskipTests" release:prepare release:perform`
- 需要询问用户："测试包请提供自定义部署命令，例如 `mvn -B -DskipTests deploy`，是否可行？"

**确认后再执行：**
```bash
npx -y @qunhe/moon-cli@latest create jar-deploy --command="用户确认的命令" --description="测试包发版" --yes
```

---

## Step 4：打标签

### 判断是否需要手动打标签

| 流程类型 | 是否需要手动打标签 |
| :--- | :--- |
| Maven Release 模式（command 包含 release:perform / release:prepare） | ❌ 不需要，Maven 自动打标签 |
| 标准模式（其他命令） | ✅ 需要，手动打标签 |

### 手动打标签（标准模式）

在部署前创建并推送标签，确保标签与发版版本对应：

```bash
git tag -a <版本> -m "Release <版本>"
git push origin <版本>
```

**注意：** 标签需在发版前推送到远程仓库，jar-deploy 会基于标签版本进行发布。

---

## Step 5：部署二方包

### 前置检查

**强制规则：部署前必须确认 CHANGELOG 已合并到目标分支**

在执行 jar-deploy 之前，必须验证 release 分支上的 CHANGELOG.md 是否已包含本次发版的变更：

```bash
# 检查 release 分支的 CHANGELOG.md 是否已更新
git fetch origin release/<分支名>
git log origin/release/<分支名> --oneline -3 -- CHANGELOG.md

# 对比本地 release 分支与远程 release 分支的 CHANGELOG.md 差异
git diff origin/release/<分支名> -- CHANGELOG.md
```

**如果 CHANGELOG 未合并到 release 分支：**
1. 提示用户必须先将 CHANGELOG 变更合并到目标分支
2. 使用 git 命令确认已经合并后再执行部署

**未通过检查禁止进行部署，否则打出的包里没有变更内容。**

### jar-deploy 命令

```bash
# 使用当前仓库（自动匹配关联的二方包组）
npx -y @qunhe/moon-cli@latest create jar-deploy --description="新增 XX 功能；修复 XX 问题" --yes

# 指定分支部署
npx -y @qunhe/moon-cli@latest create jar-deploy --branch=master --description="新增 XX 功能" --yes
```

### 常用参数

| 参数 | 说明                              | 示例 |
| :--- |:--------------------------------| :--- |
| `--branch` | 分支名称，不填使用当前分支                   | `--branch=master` |
| `--description` | 发版描述（变更摘要，传入流水线）                | `--description="新增 XX 功能"` |
| `--command` | 部署命令，不填使用二方包组默认命令，当发布测试包时需要特别注意 | `--command="mvn deploy -DskipTests"` |
| `--sub-module` | 模块名称，不填使用二方包组默认模块               | `--sub-module=module-name` |
| `--yes` | 自动确认                            | `--yes` |

### 核心特性

- **自动匹配**：通过当前 git 仓库地址自动匹配二方包组
- **智能分支**：不指定 `--branch` 时使用当前分支，并校验本地与远程一致
- **流水线状态**：默认等待流水线完成，SUCCESS 显示二方包组详情页，失败显示流水线详情页

---

## 常见错误处理

### 当前目录不是 git 仓库
```
Error: 当前目录不是一个 git 仓库，或没有配置 origin 地址
```
**解决：** 确保在 git 仓库目录下执行，并配置了 origin 远程仓库

### 本地分支与远程分支不一致
```
Error: 本地分支 xxx 与远程分支 xxx 不一致，请先将 xxx 分支推送到远端仓库
```
**解决：** 先执行 `git push` 推送本地分支

### 未找到匹配的二方包组
```
Error: 未找到与 "xxx" 匹配的二方包组，请前往 https://moon.qunhequnhe.com/v2/?t=jar 手动创建
```
**解决：** 前往 Moon 平台手动创建二方包组关联

---

## 获取帮助

```bash
npx -y @qunhe/moon-cli@latest create jar-deploy --help
```

---

## 参考

- Keep a Changelog 规范：[https://keepachangelog.com/zh-CN/1.1.0/](https://keepachangelog.com/zh-CN/1.1.0/)
