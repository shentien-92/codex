# 同步 Codex repo 到内部 GitLab 并发布内部 npm - Design

## Boundary

本任务分两条链路：

- Git 同步链路：建立外网 GitHub 工作区和内网 GitLab 工作区的长期隔离，只同步 release 版本源码，并保证两边提交身份正确。
- npm 发布链路：确认 Codex npm tarball 的生成、内部 registry 发布顺序和验证方法。

## Git Strategy

使用两个工作区，而不是一个 repo 挂两个 remote：

- 外网工作区：`/Users/ralph/Coding/shenty/codex`
  - remote: GitHub fork
  - effective identity: `shentien-92 / shenty107@gmail.com`
  - 用于外网提交和 GitHub 同步

- 内网工作区：`/Users/ralph/Coding/qunhe/clau-codex`
  - remote: `git@gitlab.qunhequnhe.com:tool-backend/space/clau-codex.git`
  - effective identity: `xiuran / xiuran@qunhemail.com`
  - 用于内网提交和 GitLab 同步

首次同步不强推，并且只导入指定 release ref：

1. clone GitLab 初始化仓库到内网工作区。
2. 从外网工作区用 `git archive <release-ref>` 生成 release 源码快照。
3. 清理内网工作区中除 `.git/` 以外的旧文件。
4. 解包 release 源码快照到内网工作区。
5. 在内网工作区验证 `git config user.name/user.email`。
6. 用内网身份提交“sync Codex <release-ref>”。
7. 普通 push 到 GitLab `master`。

这样 GitLab 保留初始化 README 提交作为父提交，新增同步提交使用内网身份。代价是内外网 commit hash 不同，但这是“两边都要提交、两个身份”的必要结果。

Release-only 规则：

- 内部 GitLab 不同步当前开发态 HEAD。
- 内部 GitLab 不同步 dirty worktree、未跟踪文件、Trellis planning 文件或构建产物。
- 同步输入必须是明确的 release tag/branch，例如 `rust-v0.135.0` 或后续指定的内部 custom release ref。
- `git archive` 只导出被该 ref 跟踪的文件，比 `rsync` 当前工作区更适合 release-only 同步。

## npm Strategy

默认继续使用内部 registry 已存在的 `@openai/codex` 包名，不在本任务内改名到 `@qunhe/codex`。

内部发布命令必须显式指定 registry：

```bash
npm publish <tarball> --registry=https://npm-registry.qunhequnhe.com/
```

Codex CLI 的 npm 包包含 root wrapper 和多个 platform package。发布顺序必须是：

1. platform packages: `codex-npm-linux-*`, `codex-npm-darwin-*`, `codex-npm-win32-*`
2. `codex-responses-api-proxy`
3. `codex-sdk`
4. root wrapper: `codex-npm-<version>.tgz`

root wrapper 最后发布，因为它的 optional dependencies 指向平台包；先发布 root 会让安装解析到尚不存在的平台包版本。

## Compatibility

- 内部 registry 当前已有 `@openai/codex@0.136.0`，不能重复发布同版本。
- 若选择 `@qunhe/codex`，需要修改 package metadata 和 runtime optional dependency alias，影响面更大，本任务默认不做。
- GitLab 普通 push 失败时，先检查是否有新提交进入 `master`，不直接 force。
- release ref 未指定时不能执行同步。

## Rollback

- Git 同步 rollback：如果普通 push 后需要撤销，内网仓库用内网身份提交 revert。
- npm rollback：npm registry 通常不应依赖 unpublish；更稳妥做法是发布修正版本并调整 dist-tag。
