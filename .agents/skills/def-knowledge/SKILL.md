---
name: def-knowledge
description: DEF 是公司内统一的前端脚手架体系，PUB 项目、二方包项目、node 服务等均通过 `kjl` 进行管理。本 skill 提供 `kjl` 的基础用法、安装检测、任务机制、开发域/功能域概念，以及通过 `knowledge-manager` 查询各域最新知识库文档的方法。当项目根目录存在 `def.config.js` 时，应优先参考本 skill。
---

# def-knowledge

`@qunhe/def-next-cli` 是当前公司内的围绕前端生态打造的脚手架，其内部提供了`kjl`命令用来管理前端项目从生成到发布的全周期链路。

当前一个项目的根目录中存在 `def.config.js` 时，说明当前项目是由def脚手架管理的项目。

## 前置准备
- Node版本要求为大于 12 的偶数版本。
- 由于当前包为内网包，因此要修改一下npm源地址。

```bash
  npm config set registry https://npm-registry.qunhequnhe.com/
```

## 安装检测与初始化
在使用 kjl 相关命令前，可以先通过以下命令检查是否已安装：
```bash
kjl -V
```

如果未安装，应先执行以下命令进行全局安装：
```bash
npm i @qunhe/def-next-cli -g
```

## 基础概念介绍
### 1. 开发域 & 功能域（namespace）
Def 中将支持所有类型分为了开发域和功能域。
开发域：描述的是我们正在开发的项目或者功能类型。目前开发域包含：
  - PUB项目（pub）
  - NPM包项目（baozheng）
  - 小程序项目（miniprogram）
  - 云应用/云函数项目（serverless）
  - flutter项目（flutter）
  - Node服务项目（node）

功能域：描述的是我们开发项目的主体外做的额外的增强功能，例如文档管理、CI检测等相关能力。目前功能域包含：
  - 文档功能（manual）
  - 上传功能（uploader）
  - CI 功能（ci）

### 2. 任务（task）
在每个开发域下，我们都针对该域做了对应的命令开发。在使用域之前一般需要在当前工作空间中安装依赖命令。
任务安装命令:
```bash
kjl task install <namespace>
```
例如接入CI功能需要执行: `kjl task install ci`。命令执行完成之后， `def.config.js`文件中的`tasks`字段就会出现域下的所有命令。类似以下内容：
```js
{
  tasks: {
    "ci:lint":{},
    "ci:uni-test":{}
  }
}
```
命令执行格式为`kjl <任务名>`, 例如：`kjl ci:lint`, 也可以去掉域名使用简写`kjl lint`。
**注意**：当一个文件内安装了两个域相同名称的任务，必须使用完成任务名称执行。
例如，下面的代码片段中，同时安装了两个`build`命令，那么在该项目中，无法直接执行`kjl build`,必须明确使用`kjl baozheng:build`或者`kjl manual:build`来确保任务的正确运行：
```js
{
  tasks: {
    "baozheng:build":{},
    "manual:build":{}
  }
}
```
### 3. 构建器（code-builder）
对于`dev`和`build`这种需要构建的任务，任务下提供了构建器选项。目前内置的构建器有1-2个，具体内容查看各自域的文档。
```js
{
  tasks: {
    "baozheng:build":{
      "code-builder": "package-builder"
    }
  }
}
```

## 内置命令列表
内置命令指的是任意目录下都能执行的命令，没有任务的安装要求。
以下是 kjl 工具的内置命令及其使用场景：

| 命令        | 使用场景及说明                                                                                                    | 使用频率         |
| ----------- | -------------------------------------------------------------------------- | ---------------- |
| `kjl -h,--help`    | 查看当前工作空间可执行的命令                                                                                      | 中等             |
| `kjl -V,--version`    | 查看脚手架版本                                                                                      | 中等             |
| `kjl login` | 首次使用需要登录，输入 LDAP 账号和密码。当执行某些命令提示需要登录时使用此命令                                    | 较低，但可能必要 |
| `kjl migrate` | 用于把老项目迁移到新项目，适用于任何老的基于 DEF 的项目。老的def项目区别于新版的区别在于配置文件名称为`pub.config.js`                                    |较低 |
| `kjl init` | 用于初始化项目                                    | 较高 |
| `kjl ui` | 用于启动 DEF 工作台                                    | 低，一般不使用 |
| `kjl upload-log` | 用于主动上传本地日志，DEF 维护方可根据上传的日志排查问题。                                 |低 |
| `kjl clean` | 用于清理本地包缓存                                    | 低 |
| `kjl patch`  | 用于为注入一段脚本 | 低            |
| `kjl task`  | 用于查看和安装任务 | 高             |

## 各领域知识查询
各个开发域和功能域的最新说明，以内部知识库为准。查询时优先使用 `knowledge-manager` skill，而不是依赖本文件中的静态描述。

### 1. 检测 `knowledge-manager` skill 是否已安装
优先按下面两个层次判断：

1. 当前会话检测：
如果当前会话的 `Available skills` 列表中包含 `knowledge-manager`，说明 skill 已经安装并且可直接使用。

### 2. 如果未安装，如何安装
如果当前环境没有安装 `knowledge-manager`，优先引导用户通过知识库工具页完成安装：

1. 打开：
`https://librify.qunhequnhe.com/#/tool/knowledgeManagerSkill`
2. 在页面右上角找到“复制安装提示词”按钮。
3. 复制安装提示词，并粘贴到当前 Agent 会话中执行安装。
4. 安装完成后，重启 Agent，确保新 skill 被重新加载。

如果 skill 已安装但调用时报鉴权错误，还需要补充 Librify token。可以任选一种方式：

1. 在 `knowledge-manager` skill 根目录下创建 `librify-token` 文件，并写入一行 token。
2. 或者在当前终端中设置 `LIBRIFY_TOKEN` 环境变量。

token 获取地址：
`https://librify.qunhequnhe.com/#/tool/knowledgeManagerSkill`

### 3. 知识库入口与推荐检索词
下面优先列出已经确认过的知识库入口页。若入口页失效或内容不全，请继续通过 `knowledge-manager` skill 按“推荐检索词”查询最新文档。

#### 知识库总入口

- `【内部】研发业务知识库 / 基础设施 / 前端基础设施 / 脚手架 / 1 教程`

入口中包含了 Def 脚手架相关的所有开发域和功能域的文档链接，建议优先从这里进入对应领域的主文档。

#### 开发域

| 开发域 | 知识库入口 | 链接 | 推荐检索词 |
| --- | --- | --- | --- |
| `pub` | 1.2.1.1 pub 开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305366884` | `pub 页面应用`, `微应用 初始化`, `创建内部服务的页面应用` |
| `baozheng` | 1.2.1.2 baozheng（npm二方包） 开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305366923` | `baozheng`, `二方包`, `创建一个二方包` |
| `miniprogram` | 1.2.1.4 miniprogram 开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305366966` | `miniprogram`, `接入指南`, `小程序` |
| `serverless` | 1.2.1.3 serverless 开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305366946` | `serverless`, `云函数`, `部署手册` |
| `flutter` | 1.2.1.5 Flutter web 开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80505582850` | `flutter`, `flutter脚手架`, `flutter 开发` |
| `node` | 1.2.1.6 Node 服务端应用（NestJS）开发手册 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=81245711160` | `node 服务`, `node脚手架`, `后端node服务上路指南` |

#### 功能域

| 功能域 | 知识库入口 | 链接 | 推荐检索词 |
| --- | --- | --- | --- |
| `manual` | 1.2.2.1 文档功能接入 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305367023` | `manual`, `Pub 体系`, `依赖包 调试` |
| `uploader` | 1.2.2.2 上传功能接入 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80403150223` | `uploader`, `上传`, `ous-upload` |
| `ci` | 1.2.2.6 CI 功能接入 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80848406559` | `ci`, `lint`, `uni-test`, `CI lint接入` |

#### 构建器
| 构建器 | 知识库入口 | 链接 | 推荐检索词 |
| --- | --- | --- | --- |
| `构建器接入说明` | 1.2.2.3 构建功能接入 | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80305367060` | `构建器`, `code-builder`, `构建配置`|
| `webpack5-builder` | 1.2.2.3.1 webpack5-builder | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80371855568` | `webpack5`, `构建器`, `webpack`, `pub项目` |
| `package-builder` | 1.2.2.3.2 package-builder | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80412869583` | `package`, `构建器`, `包管理`, `二方包`, `baozheng项目`|
| `webpack4-builder` | 1.2.2.3.3 webpack4-builder | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=80367347892` | `webpack4`, `构建器`, `webpack`, `pub项目` |
| `rspack-builder` | 1.2.2.3.4 rspack-builder | `https://cf.qunhequnhe.com/pages/viewpage.action?pageId=81116410987` | `rspack`, `构建器`, `pub项目` |

### 4. 推荐查询方式
当用户询问某个开发域或功能域的用法时，建议优先按下面顺序处理:

1. 先确认 `knowledge-manager` 已安装且可用。
2. 先用上面的“知识库入口”定位主文档。
3. 如果主文档不完整，再用“推荐检索词”在知识库中继续检索补充内容。
4. 最终回答时，以知识库中的最新页面内容为准。
