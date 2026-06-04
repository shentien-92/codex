---
name: moon-deploy
description: 部署应用到 Moon 测试/预发环境
allowed-tools: Bash(npx -y @qunhe/moon-cli@latest *)
---

部署 Moon 应用的测试/预发环境。

## 前置要求

`@qunhe/moon-cli` 是一个基于 Node.js 的命令行工具，使用前请确保：
- Node.js 版本 >= 20
- 已配置公司内网 npm 仓库

---

## 工作流程

使用以下命令部署到测试环境：

```bash
npx -y @qunhe/moon-cli@latest create deploy-pipeline --env=<env> --yes
```

### 必填参数

**--env**

要部署的环境列表，支持多个环境按 "," 分割，例如 `--env=env1,env2`

如果用户未指定部署环境，则中断循环并要求用户输入环境名称（一般是由小写英文、数字、- 和 \_ 组成，必须以小写英文开头）

### 可选参数

**--app**

要部署的应用名称 / UUID / CMDB Tag，例如 `--app=some-service`

如果不设置该参数，会默认部署到当前 git 仓库对应的应用

除非用户指定了要部署的应用，否则不要设置该参数

**--branch**

要部署的分支，例如 `--branch=feature/add-something`

如果不设置该参数，默认为当前分支

支持多个分支，按 "," 分割，例如 `--branch=branch1,branch2`

除非用户指定了要部署的分支，否则不要设置该参数

**--cc**

抄送人，在部署成功后会发推送给抄送人

例如 `--cc=zhuyang` 或 `--cc="@zhuyang 可以测试了"`

支持中文用户名，例如 `--cc="朱羊"`，注意此时不需要将"朱羊"转成英文"zhuyang"，直接将"朱羊"作为 `--cc` 参数值即可（`--cc="@朱羊"`）

注意除非用户要求部署完后给某某人发推送，否则不要设置该参数

当用户提出类似以下要求时，你可以设置该参数：

- "部署 xxx 环境，然后通知谁谁谁可以测试了"
- "部署 xxx 环境，部署完成后通知谁谁谁"

**--ignore-deployed-branches**

忽略已部署过的分支，例如 `--ignore-deployed-branches`

默认情况下会将环境已部署的分支和目标分支一起部署

如果设置了该参数，则会忽略已部署的分支，只部署目标分支

当用户提出类似以下要求时，你可以设置该参数：

- "我只想部署当前分支，忽略已部署的分支"
- "用当前分支覆盖部署"
- "忽略环境已部署的分支"

如果用户未主动要求这一行为，不要设置该参数

### 异常处理

如果碰到类似 `环境 xxx 不存在` 的报错，提示用户该环境不存在，需要先创建环境后再进行部署

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
