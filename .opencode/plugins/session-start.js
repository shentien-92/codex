/**
 * Trellis Session Start Plugin
 *
 * Provides compact Trellis routing context through OpenCode's hidden system
 * transform. It intentionally does not mutate visible message hooks, so session-start
 * control text is not persisted into visible user messages.
 */

import process from "process"
import { TrellisContext, contextCollector, debugLog } from "../lib/trellis-context.js"
import { buildCompactSessionContext, trellisUiTransformsDisabled } from "../lib/session-utils.js"

// OpenCode 1.2.x expects plugins to be factory functions (see inject-subagent-context.js comment).
export default async ({ directory }) => {
  const ctx = new TrellisContext(directory)
  debugLog("session", "Plugin loaded, directory:", directory)

  return {
    event: ({ event }) => {
      try {
        if (event?.type === "session.compacted" && event?.properties?.sessionID) {
          const sessionID = event.properties.sessionID
          contextCollector.clear(sessionID)
          debugLog("session", "Cleared processed flag after compaction for session:", sessionID)
        }
      } catch (error) {
        debugLog(
          "session",
          "Error in event hook:",
          error instanceof Error ? error.message : String(error),
        )
      }
    },

    "experimental.chat.system.transform": async (input, output) => {
      try {
        if (process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1") {
          debugLog("session", "Skipping system transform - hooks disabled")
          return
        }
        if (trellisUiTransformsDisabled()) {
          debugLog("session", "Skipping system transform - disabled or non-interactive")
          return
        }
        if (!ctx.isTrellisProject()) {
          return
        }

        const sessionID = input?.sessionID || ""
        const includeFirstReplyNotice = sessionID ? !contextCollector.isProcessed(sessionID) : false
        const systemContext = buildCompactSessionContext(ctx, input, {
          includeFirstReplyNotice,
        })
        if (!systemContext) return

        if (!Array.isArray(output.system)) {
          output.system = []
        }
        output.system.push(systemContext)
        if (sessionID) {
          contextCollector.markProcessed(sessionID)
        }
        debugLog("session", "Added compact system context, length:", systemContext.length)
      } catch (error) {
        debugLog(
          "session",
          "Error in system transform:",
          error instanceof Error ? error.message : String(error),
        )
      }
    },
  }
}
