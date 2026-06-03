# 同步 Codex repo 到内部 GitLab 并发布内部 npm - Implement

## Plan

1. 验证当前外网工作区状态和身份。
2. 确认要同步的 release ref，例如 `rust-v0.135.0` 或内部 custom release ref。
3. clone 或更新内网工作区 `/Users/ralph/Coding/qunhe/clau-codex`。
4. 验证内网工作区身份为 `xiuran / xiuran@qunhemail.com`。
5. 用 `git archive <release-ref>` 导出 release 源码快照。
6. 清理内网工作区中除 `.git/` 以外的旧文件。
7. 解包 release 源码快照到内网工作区。
8. 检查内网工作区 diff，确认来源是 release tracked files。
9. 内网工作区提交并普通 push 到 GitLab `master`。
10. 用 `git ls-remote` 验证 GitLab `master` 指向新提交。
11. 记录内部 npm 发布命令和验证命令。

## Release Snapshot Rule

不要用 `rsync` 当前工作区导入内网 release 源码。当前工作区可能包含：

- release tag 之后的开发提交
- dirty worktree 改动
- 未跟踪 Trellis planning 文件
- 构建产物或缓存

使用 `git archive <release-ref>` 可以只导出该 release ref 跟踪的源码文件。

示例：

```bash
git -C /Users/ralph/Coding/shenty/codex archive --format=tar rust-v0.135.0 | tar -x -C /Users/ralph/Coding/qunhe/clau-codex
```

## Validation Commands

```bash
git -C /Users/ralph/Coding/shenty/codex config user.name
git -C /Users/ralph/Coding/shenty/codex config user.email

git -C /Users/ralph/Coding/qunhe/clau-codex config user.name
git -C /Users/ralph/Coding/qunhe/clau-codex config user.email

git -C /Users/ralph/Coding/shenty/codex rev-parse <release-ref>
git -C /Users/ralph/Coding/shenty/codex status --short

git ls-remote git@gitlab.qunhequnhe.com:tool-backend/space/clau-codex.git refs/heads/master
```

## npm Publishing Notes

Generate tarballs:

```bash
./scripts/stage_npm_packages.py \
  --release-version <version> \
  --package codex \
  --package codex-responses-api-proxy \
  --package codex-sdk
```

Verify auth and current version:

```bash
npm whoami --registry=https://npm-registry.qunhequnhe.com/
npm view @openai/codex version --registry=https://npm-registry.qunhequnhe.com/
```

Publish tarballs with explicit registry:

```bash
npm publish dist/npm/codex-npm-linux-x64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-linux-arm64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-darwin-x64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-darwin-arm64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-win32-x64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-win32-arm64-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-responses-api-proxy-npm-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-sdk-npm-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
npm publish dist/npm/codex-npm-<version>.tgz --registry=https://npm-registry.qunhequnhe.com/
```

Validate:

```bash
npm view @openai/codex version --registry=https://npm-registry.qunhequnhe.com/
npm install -g @openai/codex@<version> --registry=https://npm-registry.qunhequnhe.com/
codex --version
```
