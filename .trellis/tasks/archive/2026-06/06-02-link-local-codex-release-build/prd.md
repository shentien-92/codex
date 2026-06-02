# link local codex release build

## Goal

Build the local Codex Rust CLI in release mode and make Ralph's shell `codex`
command resolve to that release binary instead of the old debug binary / npm
wrapper.

## What I Already Know

- `which -a codex` resolves to
  `/Users/ralph/.nvm/versions/node/v22.22.1/bin/codex`.
- That path is currently a symlink to
  `/Users/ralph/Coding/shenty/codex/codex-rs/target/debug/codex`.
- Global npm still has `@openai/codex@0.135.0` installed under the active nvm
  Node.
- `codex-rs/target/release/codex` exists but predates the latest local commit,
  so it must be rebuilt before linking.

## Requirements

- Build a non-dev release binary from the current working tree.
- Repoint Ralph's local `codex` command to the rebuilt release binary.
- Remove the old global npm `@openai/codex` package if it is still installed.
- Verify `codex` resolves to the release binary and runs successfully.

## Acceptance Criteria

- [x] `codex-rs/target/release/codex` is rebuilt after the latest local commit.
- [x] `command -v codex` points at the active nvm bin path.
- [x] The active nvm bin `codex` symlink points at
      `codex-rs/target/release/codex`.
- [x] `npm list -g --depth=0 @openai/codex` no longer reports an installed
      global package.
- [x] `codex --version` runs from the shell command.

## Completion Notes

- Built with `cargo build --release -p codex-cli`.
- Build finished successfully in 47m 45s.
- Rebuilt release binary:
  `/Users/ralph/Coding/shenty/codex/codex-rs/target/release/codex`.
- Active shell command:
  `/Users/ralph/.nvm/versions/node/v22.22.1/bin/codex`.
- The active shell command is now a symlink to the release binary.
- Removed global npm `@openai/codex`; the active nvm global package list is
  empty for that package.
- Verified `codex --version` prints `codex-cli 0.135.0`.

## Out of Scope

- Publishing or packaging a release artifact.
- Changing repository source code.
- Changing shell startup files unless the symlink approach stops working.
