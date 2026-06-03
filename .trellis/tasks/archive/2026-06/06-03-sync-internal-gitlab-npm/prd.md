# 同步 Codex repo 到内部 GitLab 并发布内部 npm

## Goal

把 Codex release 版本源码同步到群核 GitLab 项目
`git@gitlab.qunhequnhe.com:tool-backend/space/clau-codex.git`，并明确后续在群核内部 npm registry 发布 CLI 包的可执行流程。

本任务先解决“同步到内部 GitLab”和“内部 npm 发布路径确认”。真正发布 npm 包前需要明确包名、版本号和是否覆盖内部 `@openai/codex` 发布通道。

GitHub 和 GitLab 两边都需要能独立提交，并且分别使用对应身份。
内部 GitLab 只同步 release 版本代码，不同步当前开发态工作区。

## What I Already Know

- 当前工作区：`/Users/ralph/Coding/shenty/codex`。
- 当前分支：`ralph/rust-v0.135.0-custom`，当前 HEAD 为 `373a5bdfd chore: record journal`。
- 当前 HEAD 距离 `rust-v0.135.0` tag 有 32 个提交：`rust-v0.135.0-32-g373a5bdfddc9`。
- `rust-v0.135.0` tag 指向 `4daceea869704f9f35e0a3949fc34711ef978a4e`。
- 本次内部 custom release ref 确定为 `clau-codex-v0.135.0`，标记当前 HEAD `373a5bdfddc9156134dce7125060e1c952b5575d`；该提交已完成 release build。
- 当前工作区有既有未提交改动，主要集中在 Trellis / Codex hooks；这些改动不是本任务产生的，不能回滚。
- 由于内部源只同步 release 版本，当前 HEAD 和未提交改动都不应进入 GitLab 内网 release 源码同步。
- 当前目录命中 `/Users/ralph/.gitconfig` 的 `includeIf.gitdir:/Users/ralph/Coding/shenty/`，有效 Git 身份是 `shentien-92 / shenty107@gmail.com`。
- 内网项目目录（例如 `/Users/ralph/Coding/qunhe/maas-data-service`）使用全局内网身份 `xiuran / xiuran@qunhemail.com`。
- Git commit 的 author/committer 是提交对象的一部分；同一个 commit 推到两个 remote 时身份不会随 remote 改变。若两边都要显示各自身份，就需要两个工作区分别提交，或维护两套等价历史。
- GitLab 目标仓库 SSH 可访问；HTTPS 探测因无交互式凭证失败。
- GitLab 目标仓库当前只有 `master` 分支，HEAD 为 `07f6a966e init README.md`。
- 本地 HEAD 与 GitLab `master` 没有共同提交历史。
- root `package.json` 是 monorepo 维护脚本包，真实 CLI npm 包在 `codex-cli/package.json`，包名为 `@openai/codex`。
- npm release staging 入口是 `./scripts/stage_npm_packages.py`，会生成 `dist/npm/*.tgz`。
- 内部 npm registry 为 `https://npm-registry.qunhequnhe.com/`；本机 token 可用，`npm whoami --registry=https://npm-registry.qunhequnhe.com/` 返回 `xiuran`。
- 内部 registry 已存在 `@openai/codex@0.136.0`；`@qunhe/codex` 当前不存在。

## Requirements

- 使用 SSH remote 同步到 GitLab：`git@gitlab.qunhequnhe.com:tool-backend/space/clau-codex.git`。
- GitHub 外网工作区继续使用 `shentien-92 / shenty107@gmail.com` 提交。
- GitLab 内网工作区必须使用 `xiuran / xiuran@qunhemail.com` 提交。
- 两边需要独立提交能力，不能只把同一批 commit 推到两个 remote 后期待身份自动变化。
- 内网 Git 操作不能让当前 shenty 目录的外网身份污染内网提交。
- 内部 GitLab 只同步明确 release ref 的源码快照，例如 `rust-v0.135.0` tag 或内部 release tag/branch；不能同步普通开发 HEAD、dirty worktree、Trellis 任务草稿或未发布改动。
- 不回滚或覆盖当前工作区已有未提交改动。
- 如果需要覆盖 GitLab `master`，必须使用可审计的方式，并在执行前明确它会替换当前只有 README 的初始化历史。
- 内部 npm 发布流程必须说明 registry、包名、版本、tarball 生成、发布顺序和验证命令。
- 内部 npm 包不能与已存在版本冲突；如果继续使用 `@openai/codex`，版本必须高于或不同于内部 registry 已有版本。

## Assumptions

- “同步推送”目标是让内部 GitLab 仓库承载 Codex release 源码快照，而不是当前开发态仓库快照。
- 推荐维护两个长期工作区：
  - 外网：`/Users/ralph/Coding/shenty/codex` -> GitHub fork，外网身份。
  - 内网：`/Users/ralph/Coding/qunhe/clau-codex` -> GitLab repo，内网身份。
- 两边代码同步以 release ref 为边界：外网 release 提交/标签形成后，再把对应源码快照导入内网工作区，用内网身份生成内网 release 同步提交。
- npm 发布优先考虑继续使用内部 registry 里的 `@openai/codex` 通道，因为该包名已经存在于内部源。
- 发布包名前缀暂不改成 `@qunhe/codex`，除非后续明确要求内部 scope 隔离。

## Open Questions

- 内外网两边是否接受“内容等价但 commit hash 不同”的同步方式？这是两套身份提交的自然结果。
- 内部 npm 发布包名是否继续使用 `@openai/codex`，还是改为新的内部 scope（例如 `@qunhe/codex`）？
- 内部发布版本号使用哪个值？需要避开内部已存在的 `0.136.0`。

## Acceptance Criteria

- [x] GitHub 工作区和 GitLab 工作区的提交身份分别可验证。
- [x] GitLab remote 配置为可复用的内部 remote，或给出不污染当前外网身份配置的等效推送方案。
- [x] 指定 release ref 的源码快照成功推送到 `tool-backend/space/clau-codex` 的目标分支，优先使用普通 push 而不是 force push。
- [x] GitLab 内网 release commit 上存在 `clau-codex-v0.135.0` tag。
- [x] GitLab 目标分支推送后可通过 `git ls-remote` 验证到预期 commit。
- [x] 内部 npm 发布流程被记录清楚，包含生成 tarball、发布 platform packages、发布 root wrapper、验证安装的命令。
- [x] 发布前约束被明确：registry 使用 `https://npm-registry.qunhequnhe.com/`，账号为 `xiuran`，版本不得重复。
- [ ] 若实际执行 npm publish，发布后可通过 `npm view ... --registry=https://npm-registry.qunhequnhe.com/` 验证版本。

## Out of Scope

- 不修改 Codex 源码以适配内部 npm 包名，除非确认要从 `@openai/codex` 改名到内部 scope。
- 不发布公网 npm。
- 不调整全局 Git 配置；使用内外网目录隔离或 repo-local 配置规避身份问题。
- 不处理 GitHub release / GHA OIDC trusted publishing 的公网发布流程。

## Technical Notes

- 推荐 Git 同步方式：在 `/Users/ralph/Coding/qunhe/clau-codex` 下创建独立内网 clone，确保有效 Git 身份为 `xiuran / xiuran@qunhemail.com`；当前 `/Users/ralph/Coding/shenty/codex` 继续作为外网 GitHub 工作区。
- 如果只在当前目录加 internal remote，由于 includeIf 会使用外网身份，后续任何内网提交都会带错 author/committer；不适合作为长期内部仓库工作区。
- 首次内部同步默认重建内网 release 提交：在内网工作区导入指定 release ref 的 tracked file 快照并用内网身份提交，commit hash 不同，但身份正确。
- GitLab 目标仓库已有初始化 README，所以默认方案不需要 force push：clone GitLab `master` -> 导入 release ref 源码快照 -> 内网身份提交 -> 普通 push。
- 导入 release 源码快照优先用 `git archive <release-ref>`，不要 `rsync` 当前工作区；这样可以天然排除 dirty worktree、未跟踪文件、构建产物和 Trellis planning 文件。
- `clau-codex-v0.135.0` 使用 lightweight tag；外网 tag 用于导出 release 源码，内网同步提交上再创建同名 lightweight tag，避免 annotated tagger 身份混用。
- npm tarball staging 入口：
  `./scripts/stage_npm_packages.py --release-version <version> --package codex --package codex-responses-api-proxy --package codex-sdk`
- 官方 publish 顺序在 `.github/workflows/rust-release.yml` 中：先发布 platform packages，再发布 root `@openai/codex` wrapper；原因是 root wrapper 的 optional dependency aliases 指向平台包，root 提前发布会导致安装解析不到平台包。
- 内部 registry 当前可认证：
  `npm whoami --registry=https://npm-registry.qunhequnhe.com/` -> `xiuran`。
- 内部 registry 当前存在：
  `npm view @openai/codex name version --registry=https://npm-registry.qunhequnhe.com/` -> `0.136.0`。

## Result

- 外网 release tag：`clau-codex-v0.135.0` -> `373a5bdfddc9156134dce7125060e1c952b5575d`
  - author/committer: `shentien-92 <shenty107@gmail.com>`
- GitHub fork remote refs:
  - `refs/heads/ralph/rust-v0.135.0-custom` -> `373a5bdfddc9156134dce7125060e1c952b5575d`
  - `refs/tags/clau-codex-v0.135.0` -> `373a5bdfddc9156134dce7125060e1c952b5575d`
- 内网工作区：`/Users/ralph/Coding/qunhe/clau-codex`
- 内网 release commit：`ff98a17c95a371190000afc052ab67d9dd3d382b`
  - author/committer: `xiuran <xiuran@qunhemail.com>`
- GitLab remote refs:
  - `refs/heads/master` -> `ff98a17c95a371190000afc052ab67d9dd3d382b`
  - `refs/tags/clau-codex-v0.135.0` -> `ff98a17c95a371190000afc052ab67d9dd3d382b`
- npm publish 未实际执行；已验证内部 registry 认证账号为 `xiuran`，当前 `@openai/codex` 版本为 `0.136.0`。
