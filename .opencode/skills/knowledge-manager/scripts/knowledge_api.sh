#!/bin/sh
#
# knowledge_api.sh —— Gaea 知识库命令网关薄封装
#
# 所有逻辑（SQL 组装、参数校验、结构转换、审计日志）都下沉到后端：
#   POST /know/skillApi/cli/exec   请求体 = {"command": "...", "args": {...}}
#
# 本脚本只负责一件事：把 <命令> + <JSON 参数> 打包成请求体并通过 curl 发送。
# 不依赖 Python、不依赖 jq，只依赖 /bin/sh 和 curl。
#
# 运行环境：
#   - macOS / Linux / WSL：开箱即用
#   - Windows：Git Bash（curl 随 Git for Windows 附带，或直接用 Windows 10+ 的 curl.exe）
#
# 环境变量：
#   GAEA_BASE_URL  平台地址（默认 https://gaea-beta.qunhequnhe.com）
#   LIBRIFY_TOKEN  可选；若设置则覆盖文件中的 Token（便于 CI 临时注入）
#
# Librify 专属 Token（请求头 librify-token）：
#   默认从本技能根目录的文件 librify-token 读取（与 SKILL.md 同级，本地自建，勿提交）
#   未配置时仍会请求，并在标准错误输出提示去页面复制并写入该文件
#
# 用法：
#   knowledge_api.sh <命令> [JSON参数 | @参数文件路径 | -]
#   knowledge_api.sh commands                 # 列出所有已注册命令
#   knowledge_api.sh --help
#
# 例子：
#   knowledge_api.sh roots
#   knowledge_api.sh nodes '{"parentId": 123}'
#   knowledge_api.sh sql-query '{"dbType":"mysql","sql":"SELECT id FROM nodes WHERE isDeleted = 0 LIMIT 5"}'
#   knowledge_api.sh upsert-doc @/tmp/upsert.json
#   echo '{"nodeId":123}' | knowledge_api.sh nodes -

set -eu

GAEA_BASE_URL="${GAEA_BASE_URL:-https://gaea-beta.qunhequnhe.com}"
EXEC_URL="${GAEA_BASE_URL%/}/know/skillApi/cli/exec"
COMMANDS_URL="${GAEA_BASE_URL%/}/know/skillApi/cli/commands"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
SKILL_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)"
TOKEN_FILE="$SKILL_ROOT/librify-token"

# Librify 专属 Token：优先环境变量 LIBRIFY_TOKEN，否则读技能根目录文件 librify-token
# 兼容少数进程注入的 librify-token 环境键；普通 shell 中请使用 LIBRIFY_TOKEN。
LIBRIFY_TOKEN_RESOLVED="${LIBRIFY_TOKEN:-}"
if [ -z "$LIBRIFY_TOKEN_RESOLVED" ]; then
  LIBRIFY_TOKEN_RESOLVED=$(printenv 'librify-token' 2>/dev/null || true)
fi
if [ -z "$LIBRIFY_TOKEN_RESOLVED" ] && [ -f "$TOKEN_FILE" ]; then
  while IFS= read -r _line || [ -n "$_line" ]; do
    _t=$(printf '%s\n' "$_line" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//;s/\r$//')
    [ -z "$_t" ] && continue
    case "$_t" in \#*) continue ;; esac
    LIBRIFY_TOKEN_RESOLVED="$_t"
    break
  done < "$TOKEN_FILE"
fi
unset _line _t 2>/dev/null || true

warn_missing_librify_token() {
  echo "[WARN] 未配置 Librify 专属 Token。请打开 https://librify.qunhequnhe.com/#/tool/knowledgeManagerSkill 获取 Token，然后写入技能根目录 librify-token 文件，或临时设置 LIBRIFY_TOKEN。未带头或 Token 无效时网关将返回错误。" >&2
}

usage() {
  sed -n '2,33p' "$0" | sed 's/^# \{0,1\}//'
}

case "${1:-}" in
  -h|--help|"")
    usage
    [ -z "${1:-}" ] && exit 1
    exit 0
    ;;
  commands)
    if [ -z "$LIBRIFY_TOKEN_RESOLVED" ]; then
      warn_missing_librify_token
    fi
    set --
    if [ -n "$LIBRIFY_TOKEN_RESOLVED" ]; then
      set -- "$@" -H "librify-token: $LIBRIFY_TOKEN_RESOLVED"
    fi
    curl -sS "$@" "$COMMANDS_URL"
    echo
    exit 0
    ;;
esac

command="$1"
case "$command" in
  *[!a-zA-Z0-9_-]*|'')
    echo "[ERROR] 非法命令名: $command" >&2
    exit 1
    ;;
esac

raw_args="${2:-{}}"
case "$raw_args" in
  @*)
    file_path="${raw_args#@}"
    if [ ! -f "$file_path" ]; then
      echo "[ERROR] 参数文件不存在: $file_path" >&2
      exit 1
    fi
    args_json=$(cat "$file_path")
    ;;
  -)
    args_json=$(cat)
    ;;
  *)
    args_json="$raw_args"
    ;;
esac

if [ -z "$args_json" ]; then
  args_json="{}"
fi

tmpfile=$(mktemp 2>/dev/null || mktemp -t gaea.XXXXXX)
cleanup() {
  rm -f "$tmpfile"
}
trap cleanup EXIT HUP INT TERM
{
  printf '{"command":"%s","args":' "$command"
  printf '%s' "$args_json"
  printf '}'
} > "$tmpfile"

if [ -z "$LIBRIFY_TOKEN_RESOLVED" ]; then
  warn_missing_librify_token
fi

set --
set -- "$@" -X POST -H "Content-Type: application/json; charset=utf-8"
if [ -n "$LIBRIFY_TOKEN_RESOLVED" ]; then
  set -- "$@" -H "librify-token: $LIBRIFY_TOKEN_RESOLVED"
fi
set -- "$@" --data-binary @"$tmpfile" "$EXEC_URL"
curl -sS "$@"
exit_code=$?

echo
exit $exit_code
