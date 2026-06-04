/* global process */
import { existsSync, readFileSync, readdirSync, statSync } from "fs"
import { basename, join } from "path"
import { execFileSync } from "child_process"
import { platform } from "os"
import { debugLog } from "./trellis-context.js"

const PYTHON_CMD = platform() === "win32" ? "python" : "python3"
const FALLBACK_PRIORITY = "--"
const TITLE_MAX_LENGTH = 32

export const FIRST_REPLY_NOTICE = `<first-reply-notice>
On the first visible assistant reply in this session, begin with exactly one short Chinese sentence:
Trellis SessionStart 已注入：workflow、当前任务状态、开发者身份、git 状态、active tasks、spec 索引已加载。
Then continue directly with the user's request. This notice is one-shot: do not repeat it after the first assistant reply in the same session.
</first-reply-notice>`

export function trellisHooksDisabled() {
  return process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1"
}

export function trellisUiTransformsDisabled() {
  return trellisHooksDisabled() || process.env.OPENCODE_NON_INTERACTIVE === "1"
}

function hasCuratedJsonlEntry(jsonlPath) {
  try {
    const content = readFileSync(jsonlPath, "utf-8")
    for (const rawLine of content.split(/\r?\n/)) {
      const line = rawLine.trim()
      if (!line) continue
      try {
        const row = JSON.parse(line)
        if (row && typeof row === "object" && typeof row.file === "string" && row.file) {
          return true
        }
      } catch {
        // Ignore malformed line
      }
    }
  } catch {
    return false
  }
  return false
}

function getFallbackUser() {
  return process.env.USER || process.env.USERNAME || "unknown"
}

function getTaskUser(taskData = {}) {
  return taskData.assignee || taskData.creator || taskData.currentUser || getFallbackUser()
}

function getTaskPriority(taskData = {}, fallback = FALLBACK_PRIORITY) {
  return taskData.priority || fallback
}

function countOpenTaskDirectories(directory) {
  const tasksDir = join(directory, ".trellis", "tasks")
  let count = 0

  if (!existsSync(tasksDir)) return count

  try {
    for (const name of readdirSync(tasksDir)) {
      if (name.startsWith(".") || name === "archive") continue

      const taskJsonPath = join(tasksDir, name, "task.json")
      if (!existsSync(taskJsonPath)) continue

      try {
        const taskData = JSON.parse(readFileSync(taskJsonPath, "utf-8"))
        if (taskData?.status === "completed" || taskData?.completedAt) continue
      } catch {
        // If task.json exists but cannot be parsed, still count it as a task directory.
      }

      count += 1
    }
  } catch {
    return count
  }

  return count
}

function withDisplayFields(summary, taskData = {}) {
  const { ctxDirectory, ...rest } = summary
  return {
    priority: getTaskPriority(taskData),
    assignee: getTaskUser(taskData),
    taskCount: countOpenTaskDirectories(ctxDirectory),
    ...rest,
  }
}

export function getStructuredTaskStatus(ctx, platformInput = null) {
  const active = ctx.getActiveTask(platformInput)
  const taskRef = active.taskPath
  if (!taskRef) {
    return withDisplayFields({
      ctxDirectory: ctx.directory,
      kind: "no_task",
      taskRef: null,
      taskId: null,
      taskTitle: null,
      status: "NO ACTIVE TASK",
      source: active.source,
      next: "Classify the current turn and ask for task-creation consent before creating any Trellis task",
      missing: null,
      stale: false,
      ready: false,
    })
  }

  const taskDir = ctx.resolveTaskDir(taskRef)

  if (active.stale || !taskDir || !existsSync(taskDir)) {
    return withDisplayFields({
      ctxDirectory: ctx.directory,
      kind: "stale",
      taskRef,
      taskId: taskRef.split("/").pop(),
      taskTitle: taskRef,
      status: "STALE POINTER",
      source: active.source,
      next: "Task directory not found. Run: python3 ./.trellis/scripts/task.py finish",
      missing: "task directory not found",
      stale: true,
      ready: false,
    })
  }

  let taskData = {}
  const taskJsonPath = join(taskDir, "task.json")
  if (existsSync(taskJsonPath)) {
    try {
      taskData = JSON.parse(readFileSync(taskJsonPath, "utf-8"))
    } catch {
      // Ignore parse errors
    }
  }

  const taskTitle = taskData.title || taskRef
  const taskStatus = taskData.status || "unknown"
  const taskId = taskData.name || taskData.id || basename(taskDir)

  if (taskStatus === "completed") {
    return withDisplayFields({
      ctxDirectory: ctx.directory,
      kind: "completed",
      taskRef,
      taskId,
      taskTitle,
      status: "COMPLETED",
      source: active.source,
      next: "Run /trellis:finish-work. If the working tree is dirty, return to Phase 3.4 first.",
      missing: null,
      stale: false,
      ready: false,
    }, taskData)
  }

  const hasPrd = existsSync(join(taskDir, "prd.md"))
  const hasDesign = existsSync(join(taskDir, "design.md"))
  const hasImplementPlan = existsSync(join(taskDir, "implement.md"))
  const implementJsonl = join(taskDir, "implement.jsonl")
  const checkJsonl = join(taskDir, "check.jsonl")
  const jsonlReady =
    (!existsSync(implementJsonl) || hasCuratedJsonlEntry(implementJsonl)) &&
    (!existsSync(checkJsonl) || hasCuratedJsonlEntry(checkJsonl))

  if (taskStatus === "planning" && !hasPrd) {
    return withDisplayFields({
      ctxDirectory: ctx.directory,
      kind: "not_ready",
      taskRef,
      taskId,
      taskTitle,
      status: taskStatus,
      source: active.source,
      next: "Load trellis-brainstorm and write prd.md. Stay in planning.",
      missing: "prd.md not created",
      stale: false,
      ready: false,
    }, taskData)
  }

  if (taskStatus === "planning") {
    const missingComplex = []
    if (!hasDesign) missingComplex.push("design.md")
    if (!hasImplementPlan) missingComplex.push("implement.md")
    const missing = []
    if (missingComplex.length > 0) missing.push(missingComplex.join(", "))
    if (!jsonlReady) missing.push("implement.jsonl / check.jsonl curated entries")
    return withDisplayFields({
      ctxDirectory: ctx.directory,
      kind: missing.length > 0 ? "not_ready" : "ready",
      taskRef,
      taskId,
      taskTitle,
      status: taskStatus,
      source: active.source,
      next: missing.length > 0
        ? `Complete planning artifacts: ${missing.join("; ")}. Do not enter implementation until the user confirms start.`
        : "Planning artifacts are present; ask for review before `task.py start`",
      missing: missing.length > 0 ? missing.join("; ") : null,
      stale: false,
      ready: missing.length === 0,
    }, taskData)
  }

  return withDisplayFields({
    ctxDirectory: ctx.directory,
    kind: "ready",
    taskRef,
    taskId,
    taskTitle,
    status: taskStatus,
    source: active.source,
    next: "Follow the matching per-turn workflow-state. Implementation/check context order is jsonl entries -> `prd.md` -> `design.md if present` -> `implement.md if present`.",
    missing: null,
    stale: false,
    ready: true,
  }, taskData)
}

function getTaskStatus(ctx, platformInput = null) {
  const summary = getStructuredTaskStatus(ctx, platformInput)
  if (summary.kind === "no_task") {
    return `Status: ${summary.status}\nSource: ${summary.source}\nNext: ${summary.next}`
  }
  if (summary.kind === "stale") {
    return `Status: ${summary.status}\nTask: ${summary.taskRef}\nSource: ${summary.source}\nNext: ${summary.next}`
  }
  if (summary.kind === "completed") {
    return `Status: ${summary.status}\nTask: ${summary.taskTitle}\nSource: ${summary.source}\nNext: ${summary.next}`
  }
  if (summary.kind === "not_ready") {
    return `Status: ${summary.status}\nTask: ${summary.taskTitle}\nSource: ${summary.source}\nMissing: ${summary.missing}\nNext: ${summary.next}`
  }

  return `Status: ${String(summary.status).toUpperCase()}\nTask: ${summary.taskTitle}\nSource: ${summary.source}\nNext: ${summary.next}`
}

function truncateStatusTitle(title) {
  const normalized = String(title || "").replace(/\s+/g, " ").trim()
  if (normalized.length <= TITLE_MAX_LENGTH) return normalized
  return `${normalized.slice(0, TITLE_MAX_LENGTH - 1)}…`
}

function truncateToWidth(text, maxWidth) {
  const normalized = String(text || "").replace(/\s+/g, " ").trim()
  if (!Number.isFinite(maxWidth) || maxWidth <= 1 || normalized.length <= maxWidth) {
    return normalized
  }
  return `${normalized.slice(0, Math.max(1, maxWidth - 1))}…`
}

export function fitTrellisStatusLine(card, maxWidth) {
  return fitTrellisStatusParts(card, maxWidth).line
}

export function fitTrellisStatusParts(card, maxWidth) {
  const line = String(card?.line2 || card?.detail || "")
  const safeWidth = Number.isFinite(maxWidth) && maxWidth > 0 ? maxWidth : line.length
  const parts = card?.parts || {}
  const badge = parts.priority || "--"
  const sessionPrefix = typeof parts.sessionPrefix === "string" ? parts.sessionPrefix : ""
  const title = typeof parts.title === "string" ? parts.title : ""
  const user = typeof parts.user === "string" ? parts.user : "unknown"
  const taskCount = Number.isFinite(parts.taskCount) ? parts.taskCount : 0
  const fullSuffix = ` · ${user} · ${taskCount} task(s)`
  const compactSuffix = ` · ${user}`

  if (title && line.endsWith(fullSuffix)) {
    const prefix = `${sessionPrefix ? `${sessionPrefix} · ` : ""}[${badge}] `
    const fullTitleWidth = safeWidth - prefix.length - fullSuffix.length
    if (fullTitleWidth >= 2) {
      const fittedTitle = truncateToWidth(title, fullTitleWidth)
      return {
        badge,
        title: fittedTitle,
        user,
        taskCount,
        showTaskCount: true,
        line: `${prefix}${fittedTitle}${fullSuffix}`,
      }
    }

    const compactTitleWidth = safeWidth - prefix.length - compactSuffix.length
    if (compactTitleWidth >= 2) {
      const fittedTitle = truncateToWidth(title, compactTitleWidth)
      return {
        badge,
        title: fittedTitle,
        user,
        taskCount,
        showTaskCount: false,
        line: `${prefix}${fittedTitle}${compactSuffix}`,
      }
    }
  }

  const fallbackLine = truncateToWidth(line, safeWidth)
  return {
    badge,
    title: fallbackLine,
    user,
    taskCount,
    showTaskCount: false,
    line: fallbackLine,
  }
}

function getStatusCardFields(summary) {
  const statusText = String(summary.status || summary.kind || "unknown").toLowerCase()
  const priority = summary.priority || FALLBACK_PRIORITY
  const rawTitle = summary.taskTitle || summary.taskId || summary.taskRef || "Trellis no active task"
  const title = truncateStatusTitle(rawTitle)
  const user = summary.assignee || getFallbackUser()
  const taskCount = Number.isFinite(summary.taskCount) ? summary.taskCount : 0
  return { statusText, priority, title, user, taskCount }
}

function getPlatformLabel(summary) {
  const source = typeof summary?.source === "string" ? summary.source : ""
  const contextKey = source.split(":").pop() || ""
  const platformName = contextKey.split("_")[0] || ""
  const labels = {
    claude: "CC",
    codex: "CX",
    opencode: "OC",
  }
  return labels[platformName] || "--"
}

export function formatTrellisStatusCard(summary) {
  const { statusText, priority, title, user, taskCount } = getStatusCardFields(summary)

  if (summary.kind === "no_task") {
    const line1 = "Trellis no active task"
    const line2 = `[${priority}] ${statusText} · ${user} · ${taskCount} task(s)`
    return {
      title: line1,
      detail: line2,
      line1,
      line2,
      parts: {
        priority,
        title: line1,
        status: statusText,
        user,
        taskCount,
      },
      tone: "muted",
    }
  }

  if (summary.kind === "stale") {
    const line1 = "Trellis stale task pointer"
    const line2 = `[${priority}] ${statusText} · ${user} · ${taskCount} task(s)`
    return {
      title: line1,
      detail: line2,
      line1,
      line2,
      parts: {
        priority,
        title: line1,
        status: statusText,
        user,
        taskCount,
      },
      tone: "warning",
    }
  }

  const line1 = title
  const line2 = `[${priority}] ${statusText} · ${user} · ${taskCount} task(s)`

  return {
    title: line1,
    detail: line2,
    line1,
    line2,
    parts: {
      priority,
      title,
      status: statusText,
      user,
      taskCount,
    },
    tone: summary.kind === "not_ready" ? "warning" : "normal",
  }
}

export function formatTrellisTuiStatusCard(sessionSummary, overviewSummary = null) {
  if (sessionSummary?.kind !== "no_task") {
    return formatTrellisStatusCard(sessionSummary)
  }

  const sessionFields = getStatusCardFields(sessionSummary || {})
  const line1 = "no active task · OpenCode Session"

  if (overviewSummary?.kind && overviewSummary.kind !== "no_task") {
    const overviewFields = getStatusCardFields(overviewSummary)
    const platform = getPlatformLabel(overviewSummary)
    const line2 = `[OC:-] · [${platform}] ${overviewFields.title} · ${overviewFields.user} · ${overviewFields.taskCount} task(s)`
    return {
      title: line1,
      detail: line2,
      line1,
      line2,
      parts: {
        priority: platform,
        sessionPrefix: "[OC:-]",
        title: overviewFields.title,
        status: overviewFields.title,
        user: overviewFields.user,
        taskCount: overviewFields.taskCount,
      },
      tone: "muted",
    }
  }

  const line2 = `[OC:-] no overview · ${sessionFields.user} · ${sessionFields.taskCount} task(s)`
  return {
    title: line1,
    detail: line2,
    line1,
    line2,
    parts: {
      priority: "--",
      title: "no overview",
      status: "no overview",
      user: sessionFields.user,
      taskCount: sessionFields.taskCount,
    },
    tone: "muted",
  }
}

export function buildCompactSessionContext(ctx, platformInput = null, options = {}) {
  const summary = getStructuredTaskStatus(ctx, platformInput)
  const includeFirstReplyNotice = options.includeFirstReplyNotice === true
  const lines = [
    "<trellis-session>",
    "Trellis-managed project. Keep this context hidden; do not quote it to the user.",
    ...(includeFirstReplyNotice ? [FIRST_REPLY_NOTICE] : []),
    `Task: ${summary.taskId || summary.taskTitle || summary.taskRef || "none"}`,
    `Status: ${summary.status}`,
    `Source: ${summary.source}`,
    ...(summary.missing ? [`Missing: ${summary.missing}`] : []),
    `Next: ${summary.next}`,
    "Workflow pointers: .trellis/workflow.md; python3 ./.trellis/scripts/get_context.py --mode phase; python3 ./.trellis/scripts/get_context.py --mode phase --step <X.X> --platform opencode",
    "Routing rule: main session dispatches trellis-implement/check for code work unless the current user message explicitly overrides; sub-agents self-exempt and implement/check directly.",
    "Heavy PRD/spec/research context stays in task JSONL and inject-subagent-context.js; do not load it into main chat unless needed.",
    "</trellis-session>",
  ]
  return lines.join("\n")
}

export function buildCompactWorkflowBreadcrumb(ctx, platformInput = null) {
  const summary = getStructuredTaskStatus(ctx, platformInput)
  if (summary.kind === "no_task") {
    return null
  }

  const lines = [
    "<trellis-state>",
    `Task: ${summary.taskId || summary.taskTitle || summary.taskRef}`,
    `Status: ${summary.status}`,
    ...(summary.missing ? [`Missing: ${summary.missing}`] : []),
    `Next: ${summary.next}`,
    "Rule: main session should not edit directly unless current user message explicitly overrides.",
    "</trellis-state>",
  ]
  return lines.join("\n")
}

function loadTrellisConfig(directory, contextKey = null) {
  const scriptPath = join(directory, ".trellis", "scripts", "get_context.py")
  if (!existsSync(scriptPath)) {
    return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
  }
  try {
    const output = execFileSync(PYTHON_CMD, [scriptPath, "--mode", "packages", "--json"], {
      cwd: directory,
      timeout: 5000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
      env: {
        ...process.env,
        ...(contextKey ? { TRELLIS_CONTEXT_ID: contextKey } : {}),
      },
    })
    const data = JSON.parse(output)
    if (data.mode !== "monorepo") {
      return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
    }
    const pkgDict = {}
    for (const pkg of (data.packages || [])) {
      pkgDict[pkg.name] = pkg
    }
    return {
      isMonorepo: true,
      packages: pkgDict,
      specScope: data.specScope || null,
      activeTaskPackage: data.activeTaskPackage || null,
      defaultPackage: data.defaultPackage || null,
    }
  } catch (e) {
    debugLog("session", "loadTrellisConfig error:", e.message)
    return { isMonorepo: false, packages: {}, specScope: null, activeTaskPackage: null, defaultPackage: null }
  }
}

function checkLegacySpec(directory, config) {
  if (!config.isMonorepo || Object.keys(config.packages).length === 0) {
    return null
  }

  const specDir = join(directory, ".trellis", "spec")
  if (!existsSync(specDir)) return null

  let hasLegacy = false
  for (const name of ["backend", "frontend"]) {
    if (existsSync(join(specDir, name, "index.md"))) {
      hasLegacy = true
      break
    }
  }
  if (!hasLegacy) return null

  const pkgNames = Object.keys(config.packages).sort()
  const missing = pkgNames.filter(name => !existsSync(join(specDir, name)))

  if (missing.length === 0) return null

  if (missing.length === pkgNames.length) {
    return (
      `[!] Legacy spec structure detected: found \`spec/backend/\` or \`spec/frontend/\` ` +
      `but no package-scoped \`spec/<package>/\` directories.\n` +
      `Monorepo packages: ${pkgNames.join(", ")}\n` +
      `Please reorganize: \`spec/backend/\` -> \`spec/<package>/backend/\``
    )
  }
  return (
    `[!] Partial spec migration detected: packages ${missing.join(", ")} ` +
    `still missing \`spec/<pkg>/\` directory.\n` +
    `Please complete migration for all packages.`
  )
}

function resolveSpecScope(config) {
  if (!config.isMonorepo || Object.keys(config.packages).length === 0) {
    return null
  }

  const { specScope, activeTaskPackage, defaultPackage, packages } = config
  if (specScope == null) return null

  if (specScope === "active_task") {
    if (activeTaskPackage && activeTaskPackage in packages) return new Set([activeTaskPackage])
    if (defaultPackage && defaultPackage in packages) return new Set([defaultPackage])
    return null
  }

  if (Array.isArray(specScope)) {
    const valid = new Set()
    for (const entry of specScope) {
      if (entry in packages) {
        valid.add(entry)
      }
    }
    if (valid.size > 0) return valid
    if (activeTaskPackage && activeTaskPackage in packages) return new Set([activeTaskPackage])
    if (defaultPackage && defaultPackage in packages) return new Set([defaultPackage])
    return null
  }

  return null
}

function collectSpecIndexPaths(directory, allowedPkgs) {
  const specDir = join(directory, ".trellis", "spec")
  const paths = []

  const guidesIndex = join(specDir, "guides", "index.md")
  if (existsSync(guidesIndex)) {
    paths.push(".trellis/spec/guides/index.md")
  }

  if (!existsSync(specDir)) return paths

  try {
    const subs = readdirSync(specDir).filter(name => {
      if (name.startsWith(".") || name === "guides") return false
      try {
        return statSync(join(specDir, name)).isDirectory()
      } catch {
        return false
      }
    }).sort()

    for (const sub of subs) {
      const indexFile = join(specDir, sub, "index.md")
      if (existsSync(indexFile)) {
        paths.push(`.trellis/spec/${sub}/index.md`)
      } else {
        if (allowedPkgs !== null && !allowedPkgs.has(sub)) continue
        try {
          const nested = readdirSync(join(specDir, sub)).filter(name => {
            try {
              return statSync(join(specDir, sub, name)).isDirectory()
            } catch {
              return false
            }
          }).sort()
          for (const layer of nested) {
            const nestedIndex = join(specDir, sub, layer, "index.md")
            if (existsSync(nestedIndex)) {
              paths.push(`.trellis/spec/${sub}/${layer}/index.md`)
            }
          }
        } catch {
          // Ignore directory read errors
        }
      }
    }
  } catch {
    // Ignore spec directory read errors
  }

  return paths
}

function readDeveloper(directory) {
  try {
    const content = readFileSync(join(directory, ".trellis", ".developer"), "utf-8")
    for (const line of content.split(/\r?\n/)) {
      if (line.startsWith("name=")) return line.slice("name=".length).trim()
    }
  } catch {
    // Ignore missing developer file
  }
  return "(not initialized)"
}

function runGit(directory, args) {
  try {
    return execFileSync("git", args, {
      cwd: directory,
      timeout: 3000,
      encoding: "utf-8",
      stdio: ["pipe", "pipe", "pipe"],
    }).trim()
  } catch {
    return ""
  }
}

function buildCompactCurrentState(ctx, platformInput, specIndexPaths) {
  const directory = ctx.directory
  const lines = []
  lines.push(`Developer: ${readDeveloper(directory)}`)

  const branch = runGit(directory, ["branch", "--show-current"]) || "(detached)"
  const dirtyCount = runGit(directory, ["status", "--porcelain"])
    .split(/\r?\n/)
    .filter(line => line.trim()).length
  lines.push(`Git: branch ${branch}; ${dirtyCount === 0 ? "clean" : `dirty ${dirtyCount} paths`}.`)

  const active = ctx.getActiveTask(platformInput)
  if (active.taskPath) {
    const taskDir = ctx.resolveTaskDir(active.taskPath)
    let status = "unknown"
    if (taskDir) {
      try {
        const data = JSON.parse(readFileSync(join(taskDir, "task.json"), "utf-8"))
        status = data.status || "unknown"
      } catch {
        // Ignore parse errors
      }
    }
    lines.push(`Current task: ${active.taskPath}; status=${status}.`)
  } else {
    lines.push("Current task: none.")
  }

  const tasksDir = join(directory, ".trellis", "tasks")
  if (existsSync(tasksDir)) {
    try {
      const activeTasks = readdirSync(tasksDir, { withFileTypes: true })
        .filter(entry => entry.isDirectory() && entry.name !== "archive" && existsSync(join(tasksDir, entry.name, "task.json")))
      lines.push(`Active tasks: ${activeTasks.length} total. Use \`python3 ./.trellis/scripts/task.py list --mine\` only if needed.`)
    } catch {
      // Ignore task list errors
    }
  }

  const developer = readDeveloper(directory)
  const workspaceDir = join(directory, ".trellis", "workspace", developer)
  if (developer !== "(not initialized)" && existsSync(workspaceDir)) {
    try {
      const journals = readdirSync(workspaceDir)
        .filter(name => /^journal-\d+\.md$/.test(name))
        .sort((a, b) => Number(a.match(/\d+/)?.[0] || 0) - Number(b.match(/\d+/)?.[0] || 0))
      const journal = journals[journals.length - 1]
      if (journal) {
        const journalPath = join(workspaceDir, journal)
        const lineCount = readFileSync(journalPath, "utf-8").split(/\r?\n/).length
        lines.push(`Journal: .trellis/workspace/${developer}/${journal}, ${lineCount} / 2000 lines.`)
      }
    } catch {
      // Ignore journal errors
    }
  }

  if (specIndexPaths.length > 0) {
    lines.push(`Spec indexes: ${specIndexPaths.length} available.`)
  }

  return lines.join("\n")
}

export function buildSessionContext(ctx, platformInput = null) {
  const directory = ctx.directory
  const contextKey = typeof ctx.getContextKey === "function"
    ? ctx.getContextKey(platformInput)
    : null

  const config = loadTrellisConfig(directory, contextKey)
  const allowedPkgs = resolveSpecScope(config)
  const paths = collectSpecIndexPaths(directory, allowedPkgs)

  const parts = []

  parts.push(`<session-context>
Trellis compact SessionStart context. Use it to orient the session; load details on demand.
</session-context>`)
  parts.push(FIRST_REPLY_NOTICE)

  const legacyWarning = checkLegacySpec(directory, config)
  if (legacyWarning) {
    parts.push(`<migration-warning>\n${legacyWarning}\n</migration-warning>`)
  }

  parts.push("<current-state>")
  parts.push(buildCompactCurrentState(ctx, platformInput, paths))
  parts.push("</current-state>")

  const workflowContent = ctx.readProjectFile(".trellis/workflow.md")
  if (workflowContent) {
    const allLines = workflowContent.split("\n")
    const overviewLines = [
      "# Development Workflow - Session Summary",
      "Full guide: .trellis/workflow.md. Step detail: `python3 ./.trellis/scripts/get_context.py --mode phase --step <X.Y>`.",
      "",
    ]

    let rangeStart = -1
    let rangeEnd = allLines.length
    for (let i = 0; i < allLines.length; i++) {
      const stripped = allLines[i].trim()
      if (rangeStart === -1 && stripped === "## Phase Index") {
        rangeStart = i
      } else if (rangeStart !== -1 && stripped === "## Phase 1: Plan") {
        rangeEnd = i
        break
      }
    }
    if (rangeStart !== -1) {
      const strippedStateBlocks = allLines
        .slice(rangeStart, rangeEnd)
        .join("\n")
        .replace(/\[workflow-state:([A-Za-z0-9_-]+)\]\s*\n[\s\S]*?\n\s*\[\/workflow-state:\1\]\n?/g, "")
        .replace(/<!--[\s\S]*?-->/g, "")
        .replace(/^\[(?!\/?workflow-state:)\/?[^\]\n]+\]\s*\n?/gm, "")
        .replace(/\n{3,}/g, "\n\n")
      overviewLines.push(strippedStateBlocks.trimEnd())
    }

    parts.push("<trellis-workflow>")
    parts.push(overviewLines.join("\n").trimEnd())
    parts.push("</trellis-workflow>")
  }

  parts.push("<guidelines>")
  parts.push(
    "Task context order for implementation/check: jsonl entries -> `prd.md` -> " +
    "`design.md if present` -> `implement.md if present`. Missing optional artifacts " +
    "are skipped for lightweight tasks.\n"
  )

  if (paths.length > 0) {
    parts.push("## Available indexes (read on demand)")
    for (const p of paths) {
      parts.push(`- ${p}`)
    }
    parts.push("")
  }

  parts.push(
    "Discover more via: " +
    "`python3 ./.trellis/scripts/get_context.py --mode packages`"
  )
  parts.push("</guidelines>")

  const taskStatus = getTaskStatus(ctx, platformInput)
  parts.push(`<task-status>\n${taskStatus}\n</task-status>`)

  parts.push(`<ready>
Context loaded. Follow <task-status>. Load workflow/spec/task details only when needed.
</ready>`)

  return parts.join("\n\n")
}

function getTrellisMetadata(metadata) {
  if (!metadata || typeof metadata !== "object") {
    return {}
  }

  const trellis = metadata.trellis
  if (!trellis || typeof trellis !== "object") {
    return {}
  }

  return trellis
}

function hasSessionStartMarker(part) {
  if (!part || part.type !== "text" || typeof part.text !== "string") {
    return false
  }

  return getTrellisMetadata(part.metadata).sessionStart === true
}

export function hasInjectedTrellisContext(messages) {
  if (!Array.isArray(messages)) {
    return false
  }

  return messages.some(message => {
    if (!message?.info || message.info.role !== "user" || !Array.isArray(message.parts)) {
      return false
    }

    return message.parts.some(hasSessionStartMarker)
  })
}

export async function hasPersistedInjectedContext(client, directory, sessionID) {
  try {
    const response = await client.session.messages({
      path: { id: sessionID },
      query: { directory },
      throwOnError: true,
    })
    return hasInjectedTrellisContext(response.data || [])
  } catch (error) {
    debugLog(
      "session",
      "Failed to read session history for dedupe:",
      error instanceof Error ? error.message : String(error),
    )
    return false
  }
}
