/**
 * Trellis Workflow State Injection Plugin
 *
 * Adds compact per-request Trellis routing hints through OpenCode's hidden
 * messages transform. The breadcrumb exists only for the model request and is
 * not written back to visible chat history.
 */

import process from "process"
import { TrellisContext, debugLog } from "../lib/trellis-context.js"
import { buildCompactWorkflowBreadcrumb, trellisUiTransformsDisabled } from "../lib/session-utils.js"

function getLastUserMessage(messages) {
  if (!Array.isArray(messages)) return null
  for (let i = messages.length - 1; i >= 0; i--) {
    const message = messages[i]
    if (message?.info?.role === "user" && Array.isArray(message.parts)) {
      return message
    }
  }
  return null
}

function getPlatformInput(input, message) {
  const info = message?.info && typeof message.info === "object" ? message.info : {}
  return {
    ...(input && typeof input === "object" ? input : {}),
    ...info,
  }
}

function makeSyntheticPart(message, text) {
  const messageID = message?.info?.id || "trellis-hidden-message"
  const sessionID = message?.info?.sessionID || "trellis-hidden-session"
  return {
    id: `${messageID}-trellis-state`,
    sessionID,
    messageID,
    type: "text",
    text,
    synthetic: true,
    metadata: {
      trellis: {
        workflowState: true,
        hiddenTransform: true,
      },
    },
  }
}

// OpenCode 1.2.x expects plugins to be factory functions (see inject-subagent-context.js comment).
export default async ({ directory }) => {
  const ctx = new TrellisContext(directory)
  debugLog("workflow-state", "Plugin loaded, directory:", directory)

  return {
    "experimental.chat.messages.transform": async (input, output) => {
      try {
        if (process.env.TRELLIS_HOOKS === "0" || process.env.TRELLIS_DISABLE_HOOKS === "1") {
          return
        }
        if (trellisUiTransformsDisabled()) {
          return
        }
        if (!ctx.isTrellisProject()) {
          return
        }

        const lastUserMessage = getLastUserMessage(output?.messages)
        if (!lastUserMessage) {
          debugLog("workflow-state", "Skipping hidden breadcrumb - no user message")
          return
        }

        const breadcrumb = buildCompactWorkflowBreadcrumb(
          ctx,
          getPlatformInput(input, lastUserMessage),
        )
        if (!breadcrumb) {
          debugLog("workflow-state", "Skipping hidden breadcrumb - no active task")
          return
        }

        lastUserMessage.parts.push(makeSyntheticPart(lastUserMessage, breadcrumb))
        debugLog("workflow-state", "Added hidden workflow breadcrumb, length:", breadcrumb.length)
      } catch (error) {
        debugLog(
          "workflow-state",
          "Error in messages transform:",
          error instanceof Error ? error.message : String(error),
        )
      }
    },
  }
}
