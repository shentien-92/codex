# DEF CI 接入补充

来源：

- `skills/def-knowledge/SKILL.md` 中的 CI 域入口信息
- 知识库文档 `1.2.2.6 CI 功能接入`
- 文档 ID：`60760`
- Confluence 页面 ID：`80848406559`

## 什么时候读这份参考

当前项目只要准备使用 `kjl` 的 CI 域能力，就应该读这份参考；不要求项目本身先属于某个特定开发域。

## 作用范围

DEF 的 `ci` 功能域覆盖下面几类质量门禁：

- `lint`
- `uni-test`
- `copyright`
- `gpl`
- `mutation-test`
- 本地 CI 初始化与提交前卡点
- GitLab CI / Moon 接入

## 基础接入

在项目根目录执行：

```bash
kjl task install ci
```

接入后，`def.config.js` 的 `tasks` 中会出现相关 `ci:*` 任务。

这里的重点是：

- CI 域能力面向任意前端项目
- 是否能接入，不由项目类型决定
- 实际判断标准是能否在当前仓库完成 `kjl task install ci` 与后续任务执行

## 关键命令

### lint

```bash
kjl ci:lint
```

要点：

- 会注入 eslint 刚性规则
- 刚性规则不能被业务自定义规则覆盖
- 支持 `--all`、`--fix`、`--skipCustom`

相关 `def.config.js` 配置：

```js
{
  configs: {
    ci: {
      onlyCheckRigidRulesInCI: false,
      lintSerially: true,
      extendsLintRc: "./eslintrc",
      lintCheckChangedLinesOnly: true,
    },
  },
}
```

补充说明：

- 本地执行时，增量 lint 依赖“已暂存”的修改文件
- MR 触发时，检测范围是该 MR 的文件范围
- 分支触发时，会按流水线历史和 commit 边界推导检测范围

### uni-test

```bash
kjl ci:uni-test
```

相关 `def.config.js` 配置：

```js
{
  configs: {
    ci: {
      testType: "jest",
      testConfigFile: "jest.config.js",
      codeCoverage: "nyc",
    },
  },
}
```

要点：

- `testType` 支持 `jest` 或 `mocha`
- 目前只支持 `jest` 或 `mocha`，其他测试框架无法直接执行 `ci:uni-test`
- `testConfigFile` 指向测试配置文件
- mocha 覆盖率工具常用 `nyc` 或 `c8`
- 测试文件路径需要在测试配置中显式声明
- 如果执行时报缺少 `nyc`，需要安装对应依赖

### 覆盖率与核心模块

默认覆盖率口径依赖测试框架配置：

- 没有配置 `collectCoverageFrom` 时，分母通常是测试运行时实际导入到的文件
- 配置了 `collectCoverageFrom` 时，分母取该 pattern 范围

如果要统计核心模块覆盖率，可使用 `code-stage.json`。

生成方式：

```bash
kjl patch install generatorCodeStage
```

### 其他任务

```bash
kjl ci:copyright
kjl ci:gpl
kjl ci:mutation-test
```

### 本地 CI

初始化：

```bash
kjl ci:init
```

这个命令会做两件事：

1. 初始化 VSCode 里的刚性规则提示
2. 初始化 git hooks，为本地 CI 卡点做准备

## GitLab CI 接入模式

知识页强调两种模式：

- 远程公共托管
- 仓库本地 YAML 接入

默认更推荐远程托管；如果本地没有历史 `gitlab-ci.yml`，通常直接走远程托管更简单。

选择本地 YAML 时要注意：

- 默认插入片段运行在 `stage: test`
- 如果仓库没有声明 `test` 阶段，要先补 `stages`
- `rules` 需要覆盖 MR、分支、每日构建等真实触发场景
