---
name: pub-app-deploy
description: 部署PUB应用的流程。当用户请求部署PUB应用时，请执行以下步骤。
---

# Pub 应用部署

当前流程阐述了如何将一个PUB应用发布到线上环境。

## 流程步骤
- [] 步骤1：推送代码到GitLab
- [] 步骤2：部署 sit 环境
- [] 步骤3：部署 prod_test 环境
- [] 步骤4：部署 prod 环境

### 步骤1：推送代码到GitLab
由于pub系统中构建是需要从仓库中拉取代码并构建的，因此首先要保证本地的代码已经推送到GitLab中。

通过脚手架创建出来的项目首次推送可能出现推送代码错误的情况，请你根据错误进行相应的处理，并确保代码已经推送到GitLab中。

常见问题：
1. 报错：Updates were rejected because the tip of your current branch is behind
   1. 执行命令：`git pull origin master --allow-unrelated-histories --no-rebase --no-edit`
2. error: unknown option `trailer`
   1. git 2.32 版本中引入`trailer` 参数，旧版本git版本不支持该参数，可以尝试使用多个 `-m` 选项进行提交。

### 步骤2：部署 sit 环境
使用`pub-mcp-server.app_build`触发部署应用`sit`环境`default`版本。
- 参数：
    - appName: 页面名称。从当前修改页面目录下的.pubrc.js中获取 appNames 字段。
    - stage: sit
    - version: default
    - branch: 推送代码的分支
    - user: 当前用户
    - nodeVersion: 默认使用20
  
如果需要部署其他版本，则需要使用`pub-mcp-server.app_create_tag`创建一个新版版本，然后触发该版本的构建任务。

注意：当前版本需要等待构建成功方可执行后续步骤，可以通过`pub-mcp-server.app_get_latest_build_detail`查看构建任务状态。注意：返回为空时，代表已成功构建。

### 步骤3：部署 prod_test 环境
1. 使用`pub-mcp-server.app_pipe`将`sit`环境`default`版本资源流转到`prod_test`环境`default`版本。
2. 通过`pub-mcp-server.app_get_stage_config`查询 prod_test环境的配置，如果prod_test环境还没有路径，使用`pub-mcp-server.app_pipe_stage_config`流转一下路径配置。此处会创建一个变更集，请你给出变集链接，提醒用户前往审核并执行变更集，不然会导致页面无法访问。
  - app_pipe_stage_config 参数：
    - issueKey：如果前置输入中没有获取到该字段，默认使用 FEWF-4807。
    - appName: 步骤 1 中获得的页面名称
    - fromStage: sit
    - toStage: prod
    - user: 当前用户

### 步骤4：部署 prod 环境
prod 环境发布需要前往 Pub 系统进行流转。
操作页面链接：`https://pub.qunhequnhe.com/app#/<应用fcId>/config`
应用fcId可以通过`pub-mcp-server.app_get_detail`获取。

返回页面链接供用户访问，格式：`<业务域Domain>/<应用路径>`。例如：`https://www.kujiale.com/pub/page/demo`。注意：返回链接时使用可点击格式返回。

如果上下文中没有业务域的信息，可以根据`def.config.js`中的，defaultTargetServer字段获取域名，并推理出业务域信息。

再次提醒用户，请前往审核并执行变更集，不然会导致页面无法访问。
