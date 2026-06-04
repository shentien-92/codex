---
name: create-merge-request
description: 创建/发起 GitLab Merge Request（简写为 MR）
allowed-tools: Bash(git branch --show-current), Bash(git fetch), Bash(git log *), Bash(git diff *), Bash(git push -u origin *), Bash(npx -y @qunhe/devops-skill-helper@latest *)
---

# 创建 Merge Request

## 工作流程

- [ ] 确定源分支
- [ ] 确定目标分支
- [ ] 分析变更内容
- [ ] 撰写 Merge Request 标题和描述
- [ ] 向用户二次确认生成的标题和描述
- [ ] 创建 Merge Request

## 确定源分支

除非用户指定，否则将当前分支视作源分支

```bash
git branch --show-current
```

## 确定目标分支

除非用户指定，否则运行如下命令获取仓库默认分支作为目标分支

```bash
npx -y @qunhe/devops-skill-helper@latest git get default-branch
```

## 分析变更内容

```bash
# 将远程内容拉取到本地
git fetch

# 比较 commit 差异
git log origin/<target_branch>...<source_branch> --no-merges

# 获取变更文件列表
git diff --name-only <target_branch>...<source_branch>

# 获取变更内容（这个命令做过优化，会防止 diff 内容超长）
npx -y @qunhe/devops-skill-helper@latest git compact-diff origin/<target_branch> <source_branch>
```

## 撰写 Merge Request 标题和描述

基于变更内容，撰写：

**Merge Request 标题**

- 查询分支名携带的任务号，例如 `feature/DEVOPS-1234/DO_SOMETHING` 中的 `DEVOPS-1234` 就是一个任务号
- 总结主要变更内容（20-80 个字）
- 示例：“LLZZ-3794: 解决 AI 接口异常时图片验证失败问题”
- 仅当用户明确指出 MR 为草稿状态（Draft）或存在尚未完成的待办事项（TODO）时，需在标题前添加 "Draft:" 前缀

**Merge Request 描述**

使用如下命令查询当前仓库配置的 Merge Request 描述模版

```bash
npx -y @qunhe/devops-skill-helper@latest git get merge-request-description-template --source-branch=<source_branch> --target-branch=<target_branch>
```

模版中可能存在以下部分，基于 commit message 和 diff，你需要

- 简要描述：简要描述变更内容（1 至 3 个 Markdown Bullet Lists）
- 影响范围：列出受影响的文件/模块
- 测试回归的建议：基于以下内容建议测试方法
  - 变更文件类型（UI、API、数据库等）
  - 变更范围
  - 常见的测试模式
- 抄送人：assignee、reviewer

```markdown
标题: LLZZ-3794: 解决 AI 接口异常时图片验证失败问题

# 简要描述:

- 修复 AI 图片生成接口异常时的验证失败问题
- 替换下线的 doubao-seedream-3.0-t2i 模型为 4.5 版本

# 影响范围:

- 图片生成模块 (ImageGeneratorController)
- AI 模型调用客户端 (LargeModelClient)

# 测试回归的建议:

- 测试图片生成接口在 AI 服务异常时的错误处理
- 验证新模型 doubao-seedream-4.5 的图片生成功能

# 抄送人

$cc @zhangsan @lisi
```

将生成的 MR 描述保存到系统临时目录下的 `mr-description.txt` 文件中，后续创建 MR 时通过 `--description-file` 参数引用该文件。

## 向用户二次确认生成的标题和描述

然后向用户展示最终的标题、指派人、描述，然后使用 AskUserQuestion 工具询问用户对生成结果是否还需要补充

## 创建 Merge Request

首先将分支推送到远端

```bash
git push -u origin <source_branch>
```

然后使用如下命令创建 Merge Request

```bash
npx -y @qunhe/devops-skill-helper@latest git create merge-request --source-branch=<source_branch> --target-branch=<target_branch> --title=<title> --description-file=</path/to/mr-description.txt> --assignee=<optional assignee>
```

注意：

- 关于 assignee：如果用户没有明确区分 assignee 和 reviewer，则将用户提及的首个用户作为 assignee

## 常见问题解决方案

**未配置内网 npm registry**

`@qunhe/devops-skill-helper@latest` 仅发布在我司内网 npm 仓库，如果执行时碰到如下报错

```
npm notice Access token expired or revoked. Please try logging in again.
npm notice Access token expired or revoked. Please try logging in again.
npm error code E404
npm error 404 Not Found - GET https://registry.npmjs.org/@qunhe%2fdevops-skill-helper - Not found
npm error 404
npm error 404  '@qunhe/devops-skill-helper@latest' is not in this registry.
npm error 404
npm error 404 Note that you can also install from a
npm error 404 tarball, folder, http url, or git url.
npm error A complete log of this run can be found in: /Users/vimsucks/.npm/_logs/2026-01-23T09_09_08_221Z-debug-0.log
```

说明用户并未配置内网 npm 仓库，可以通过如下命令解决

```bash
npm config set registry http://npm-registry.qunhequnhe.com
```

**npx 命令沙箱问题**

执行 `npx -y @qunhe/devops-skill-helper@latest` 命令时，如果碰到类似一下报错

```
Error: Failed to get access token: Error: EPERM: operation not permitted, mkdir '/Users/someone/.moon'
```

说明用户可能开启了命令沙箱，请提示用户关闭沙箱或将 `npx -y @qunhe/devops-skill-helper@latest` 命令加入沙箱白名单
