/**
 * Trellis Context Manager
 *
 * Utility class for OpenCode plugins providing file reading,
 * JSONL parsing, and context building capabilities.
 */

import { existsSync, readFileSync, appendFileSync, readdirSync, statSync } from "fs"
import { isAbsolute, join } from "path"
import { platform } from "os"
import { execSync } from "child_process"
import { createHash } from "crypto"
import process from "process"

const PYTHON_CMD = platform() === "win32" ? "python" : "python3"
const DEBUG_LOG = "/tmp/trellis-plugin-debug.log"

function debugLog(prefix, ...args) {
  const timestamp = new Date().toISOString()
  const msg = `[${timestamp}] [${prefix}] ${args.map(a => typeof a === "object" ? JSON.stringify(a) : a).join(" ")}\n`
  try {
    appendFileSync(DEBUG_LOG, msg)
  } catch {
    // ignore
  }
}

function stringValue(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null
}

function sanitizeKey(raw) {
  const safe = raw.trim().replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^[._-]+|[._-]+$/g, "")
  return safe ? safe.slice(0, 160) : ""
}

function hashValue(raw) {
  return createHash("sha256").update(raw).digest("hex").slice(0, 24)
}

function lookupString(data, keys) {
  if (!data || typeof data !== "object") return null
  for (const key of keys) {
    const value = stringValue(data[key])
    if (value) return value
  }
  for (const nestedKey of ["input", "properties", "event", "hook_input", "hookInput"]) {
    const nested = data[nestedKey]
    if (nested && typeof nested === "object") {
      const value = lookupString(nested, keys)
      if (value) return value
    }
  }
  return null
}

function booleanFlag(value) {
  return value === true || value === "true" || value === 1 || value === "1"
}

function buildContextKey(platformName, kind, value) {
  if (kind === "transcript") {
    return `${platformName}_transcript_${hashValue(value)}`
  }
  const safeValue = sanitizeKey(value)
  return safeValue ? `${platformName}_${safeValue}` : `${platformName}_${hashValue(value)}`
}

const TRELLIS_SUBAGENT_RE = /^trellis-(implement|check|research)$/

export function isTrellisSubagent(input) {
  if (!input || typeof input !== "object") return false
  const agent = typeof input.agent === "string" ? input.agent.trim() : ""
  return TRELLIS_SUBAGENT_RE.test(agent)
}

export class TrellisContext {
  constructor(directory) {
    this.directory = directory
    debugLog("context", "TrellisContext initialized", { directory })
  }

  isTrellisProject() {
    return existsSync(join(this.directory, ".trellis"))
  }

  /** @param {Record<string, unknown> | null} platformInput */
  getContextKey(platformInput = null) {
    const override = stringValue(process.env.TRELLIS_CONTEXT_ID)
    if (override) {
      return sanitizeKey(override) || hashValue(override)
    }

    const runID = stringValue(process.env.OPENCODE_RUN_ID)
    if (runID) return buildContextKey("opencode", "session", runID)

    const input = platformInput && typeof platformInput === "object" ? platformInput : null
    if (!input) return null

    const directContextKey = lookupString(input, ["contextKey", "context_key", "trellisContextKey", "TRELLIS_CONTEXT_ID"])
    if (directContextKey) {
      const safeKey = sanitizeKey(directContextKey)
      if (safeKey && this.readContext(safeKey)) return safeKey
    }

    const sessionID = lookupString(input, ["session_id", "sessionId", "sessionID"])
    if (sessionID) {
      const directKey = sanitizeKey(sessionID)
      if (directKey && directKey.startsWith("opencode_") && this.readContext(directKey)) return directKey

      const key = buildContextKey("opencode", "session", sessionID)
      if (this.readContext(key)) return key
    }

    const conversationID = lookupString(input, ["conversation_id", "conversationId", "conversationID"])
    if (conversationID) {
      const key = buildContextKey("opencode", "conversation", conversationID)
      if (this.readContext(key)) return key
    }

    const transcriptPath = lookupString(input, ["transcript_path", "transcriptPath", "transcript"])
    if (transcriptPath) {
      const key = buildContextKey("opencode", "transcript", transcriptPath)
      if (this.readContext(key)) return key
    }

    return null
  }

  shouldUseLatestSessionFallback(platformInput = null) {
    const input = platformInput && typeof platformInput === "object" ? platformInput : null
    if (!input) return false
    const platformName = this.getPlatformName(input)
    return platformName === "opencode" && booleanFlag(input._trellis_latest_session_fallback)
  }

  getPlatformName(platformInput = null) {
    const input = platformInput && typeof platformInput === "object" ? platformInput : null
    const explicit = lookupString(input, ["_trellis_platform", "trellis_platform", "platform"])
    return explicit || null
  }

  readLatestRuntimeSession(platformInput = null) {
    const sessionsDir = join(this.directory, ".trellis", ".runtime", "sessions")
    if (!existsSync(sessionsDir)) return null

    const platformName = this.getPlatformName(platformInput)
    const candidates = []

    try {
      for (const name of readdirSync(sessionsDir)) {
        if (!name.endsWith(".json")) continue

        const contextKey = name.slice(0, -".json".length)
        const context = this.readContext(contextKey)
        if (!context || typeof context !== "object") continue

        const taskRef = this.normalizeTaskRef(context.current_task || "")
        if (!taskRef) continue

        const contextPlatform = typeof context.platform === "string" ? context.platform : contextKey.split("_", 1)[0]
        let statMtime = 0
        try {
          statMtime = statSync(join(sessionsDir, name)).mtimeMs
        } catch {
          // Ignore stat errors; last_seen_at may still be available.
        }

        const lastSeenAt = Date.parse(context.last_seen_at || "") || 0
        candidates.push({
          contextKey,
          taskRef,
          platform: contextPlatform,
          timestamp: Math.max(lastSeenAt, statMtime),
        })
      }
    } catch {
      return null
    }

    const matchingPlatform = platformName
      ? candidates.filter(candidate => candidate.platform === platformName || candidate.contextKey.startsWith(`${platformName}_`))
      : []
    const pool = matchingPlatform.length > 0 ? matchingPlatform : candidates
    pool.sort((a, b) => b.timestamp - a.timestamp || a.contextKey.localeCompare(b.contextKey))
    return pool[0] || null
  }

  readContext(contextKey) {
    try {
      const contextPath = join(this.directory, ".trellis", ".runtime", "sessions", `${contextKey}.json`)
      if (!existsSync(contextPath)) return null
      return JSON.parse(readFileSync(contextPath, "utf-8"))
    } catch {
      return null
    }
  }

  /** @param {Record<string, unknown> | null} platformInput */
  getActiveTask(platformInput = null) {
    const contextKey = this.getContextKey(platformInput)
    if (contextKey) {
      const context = this.readContext(contextKey)
      const taskRef = this.normalizeTaskRef(context?.current_task || "")
      if (taskRef) {
        const taskDir = this.resolveTaskDir(taskRef)
        return {
          taskPath: taskRef,
          source: `session:${contextKey}`,
          stale: !taskDir || !existsSync(taskDir),
        }
      }
    }

    if (this.shouldUseLatestSessionFallback(platformInput)) {
      const latest = this.readLatestRuntimeSession(platformInput)
      if (latest) {
        const taskDir = this.resolveTaskDir(latest.taskRef)
        return {
          taskPath: latest.taskRef,
          source: `session-latest:${latest.contextKey}`,
          stale: !taskDir || !existsSync(taskDir),
        }
      }
    }

    return { taskPath: null, source: "none", stale: false }
  }

  _resolveSingleSessionFallback() {
    const sessionsDir = join(this.directory, ".trellis", ".runtime", "sessions")
    if (!existsSync(sessionsDir)) return null

    let files
    try {
      files = readdirSync(sessionsDir)
        .filter(name => name.endsWith(".json"))
        .sort()
    } catch {
      return null
    }
    if (files.length !== 1) return null

    const fallbackKey = files[0].replace(/\.json$/, "")
    const context = this.readContext(fallbackKey)
    const taskRef = this.normalizeTaskRef(context?.current_task || "")
    if (!taskRef) return null

    const taskDir = this.resolveTaskDir(taskRef)
    return {
      taskPath: taskRef,
      source: `session-fallback:${fallbackKey}`,
      stale: !taskDir || !existsSync(taskDir),
    }
  }

  getCurrentTask(platformInput = null) {
    return this.getActiveTask(platformInput).taskPath
  }

  normalizeTaskRef(taskRef) {
    if (!taskRef) {
      return ""
    }

    if (isAbsolute(taskRef)) {
      return taskRef.trim()
    }

    let normalized = taskRef.trim().replace(/\\/g, "/")
    while (normalized.startsWith("./")) {
      normalized = normalized.slice(2)
    }

    if (normalized.startsWith("tasks/")) {
      return `.trellis/${normalized}`
    }

    return normalized
  }

  resolveTaskDir(taskRef) {
    const normalized = this.normalizeTaskRef(taskRef)
    if (!normalized) {
      return null
    }

    if (isAbsolute(normalized)) {
      return normalized
    }

    if (normalized.startsWith(".trellis/")) {
      return join(this.directory, normalized)
    }

    return join(this.directory, ".trellis", "tasks", normalized)
  }

  readFile(filePath) {
    try {
      if (existsSync(filePath)) {
        return readFileSync(filePath, "utf-8")
      }
    } catch {
      // Ignore read errors
    }
    return null
  }

  readProjectFile(relativePath) {
    return this.readFile(join(this.directory, relativePath))
  }

  runScript(scriptPath, cwd = null, contextKey = null) {
    try {
      const result = execSync(`${PYTHON_CMD} "${scriptPath}"`, {
        cwd: cwd || this.directory,
        timeout: 10000,
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
        env: {
          ...process.env,
          ...(contextKey ? { TRELLIS_CONTEXT_ID: contextKey } : {}),
        },
      })
      return result || ""
    } catch {
      return ""
    }
  }

  readDirectoryMdFiles(dirPath, maxFiles = 20) {
    const results = []
    const fullPath = join(this.directory, dirPath)

    if (!existsSync(fullPath)) {
      return results
    }

    try {
      const files = readdirSync(fullPath)
        .filter(f => f.endsWith(".md"))
        .sort()
        .slice(0, maxFiles)

      for (const filename of files) {
        const filePath = join(dirPath, filename)
        const content = this.readProjectFile(filePath)
        if (content) {
          results.push({ path: filePath, content })
        }
      }
    } catch {
      // Ignore directory read errors
    }

    return results
  }

  readJsonlWithFiles(jsonlPath) {
    const results = []
    const content = this.readFile(jsonlPath)
    if (!content) return results

    for (const line of content.split("\n")) {
      if (!line.trim()) continue
      try {
        const item = JSON.parse(line)
        const file = item.file || item.path
        const entryType = item.type || "file"

        if (!file) continue

        if (entryType === "directory") {
          const dirEntries = this.readDirectoryMdFiles(file)
          results.push(...dirEntries)
        } else {
          const fullPath = join(this.directory, file)
          const fileContent = this.readFile(fullPath)
          if (fileContent) {
            results.push({ path: file, content: fileContent })
          }
        }
      } catch {
        // Ignore parse errors for individual lines
      }
    }
    return results
  }

  buildContextFromEntries(entries) {
    return entries.map(e => `=== ${e.path} ===\n${e.content}`).join("\n\n")
  }
}

class ContextCollector {
  constructor() {
    this.processed = new Set()
  }

  markProcessed(sessionID) {
    this.processed.add(sessionID)
  }

  isProcessed(sessionID) {
    return this.processed.has(sessionID)
  }

  clear(sessionID) {
    this.processed.delete(sessionID)
  }
}

export const contextCollector = new ContextCollector()
export { debugLog }
