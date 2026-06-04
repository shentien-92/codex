---
name: update-merge-request
description: 更新 GitLab Merge Request（简写为 MR）的标题和描述
allowed-tools: Bash(git branch --show-current), Bash(git fetch), Bash(git log *), Bash(git diff *), Bash(git push -u origin *), Bash(npx -y @qunhe/devops-skill-helper@latest *)
---

# 更新 Merge Request

## 工作流程

- [ ] 确定源分支
- [ ] 查询 opened 状态的 Merge Request
- [ ] 分析 Merge Request 变更内容
- [ ] 撰写 Merge Request 标题和描述
- [ ] 向用户二次确认生成的标题和描述
- [ ] 更新 Merge Request

## 确定源分支

除非用户指定，否则将当前分支视作源分支

```bash
git branch --show-current
```

将当前分支推送到远端仓库
```bash
git push -u origin <source_branch>
```

## 查询 opened 状态的 Merge Request

使用如下命令按源分支查询尚未合并的 MR

```bash
npx -y @qunhe/devops-skill-helper@latest git list merge-request --source-branch=<source_branch> --state=opened
```

## 分析变更内容

```bash
# 将远程内容拉取到本地
git fetch

# 比较 commit 差异
git log <diffRefs.baseSha>...<diffRefs.headSha> --no-merges

# 获取变更文件列表
git diff --name-only <diffRefs.baseSha>...<diffRefs.headSha>

# 获取变更内容（这个命令做过优化，会防止 diff 内容超长）
npx -y @qunhe/devops-skill-helper@latest git compact-diff <diffRefs.baseSha> <diffRefs.headSha>
```

## 撰写 Merge Request 标题和描述

基于变更内容，补充 Merge Request 标题和描述，严格遵守现有标题和描述的格式

将生成的 MR 描述保存到系统临时目录下的 `mr-description.txt` 文件中，后续更新 MR 时通过 `--description-file` 参数引用该文件。

## 向用户二次确认生成的标题和描述

然后向用户展示最终的标题、指派人、描述，然后使用 AskUserQuestion 工具询问用户对生成结果是否还需要补充

## 更新 Merge Request

然后使用如下命令更新 Merge Request

```bash
npx -y @qunhe/devops-skill-helper@latest git update merge-request --iid=<merge_request_iid> --title=<title> --description-file=</path/to/mr-description.txt>
```

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
