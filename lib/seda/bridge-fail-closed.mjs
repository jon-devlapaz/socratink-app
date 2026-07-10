import { eventBuilders } from "./event-facts.mjs";

const SAFE_ERROR_MESSAGES = {
  BridgeNonJson: "bridge returned non-json output",
  BridgeExitNonZero: "bridge exited nonzero",
  BridgeTimeout: "bridge subprocess timed out",
  BridgeBusy: "bridge is busy; try again",
  BridgeOutputTooLarge: "bridge output exceeded its safe limit",
  BridgeContractInvalid: "bridge response failed contract validation",
};

function clean(value) {
  return String(value ?? "").trim();
}

function cleanString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function isObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function safeBridgeMessage(error, fallback = "bridge failed closed") {
  return SAFE_ERROR_MESSAGES[error] || fallback;
}

export function bridgeErrorEvent({
  action,
  phase,
  error = "BridgeContractInvalid",
  message,
  retryable = false,
  attempts = null,
  diagnostic = null,
  duration_ms = null,
  timeout_ms = null,
}) {
  return eventBuilders.bridgeError({
    action,
    phase,
    error,
    message: message || safeBridgeMessage(error),
    retryable: Boolean(retryable),
    attempts,
    ...(diagnostic
      ? {
          diagnostic_id: diagnostic.id || null,
          diagnostic_path: diagnostic.path || null,
        }
      : {}),
    ...(duration_ms != null ? { duration_ms } : {}),
    ...(timeout_ms != null ? { timeout_ms } : {}),
    bridge_output_revealed: false,
  });
}

export async function callBridgeSafely({ bridge, action, payload }) {
  if (typeof bridge.callBridgeResult === "function") {
    try {
      const result = await bridge.callBridgeResult(action, payload);
      if (result && typeof result.ok === "boolean") return result;
    } catch (error) {
      if (typeof bridge.callBridge !== "function") {
        return {
          ok: false,
          error: error?.error || error?.name || "BridgeCallFailed",
          message: error?.message || "bridge call failed",
          diagnostic: error?.diagnostic || null,
        };
      }
    }
  }
  try {
    return { ok: true, payload: await bridge.callBridge(action, payload) };
  } catch (error) {
    return {
      ok: false,
      error: error?.error || error?.name || "BridgeCallFailed",
      message: error?.message || "bridge call failed",
      diagnostic: error?.diagnostic || null,
    };
  }
}

export function resultToBridgeError({
  result,
  action,
  phase,
  retryable = false,
  attempts = null,
}) {
  const error = result?.error || "BridgeExitNonZero";
  const detail = clean(result?.message);
  return bridgeErrorEvent({
    action,
    phase,
    error,
    retryable,
    attempts,
    diagnostic: result?.diagnostic || null,
    duration_ms: result?.duration_ms ?? null,
    timeout_ms: result?.timeout_ms ?? null,
    message:
      detail || safeBridgeMessage(error, "bridge transport failed closed"),
  });
}

export function invalidBridgeError({ action, phase, reason }) {
  return bridgeErrorEvent({
    action,
    phase,
    error: "BridgeContractInvalid",
    message: reason
      ? `bridge response failed contract validation: ${reason}`
      : SAFE_ERROR_MESSAGES.BridgeContractInvalid,
  });
}

export function validateSubstrateGatePayload(payload) {
  const decision = payload?.substrate_gate;
  if (!isObject(decision)) return "missing substrate_gate object";
  if (typeof decision.substrate_adequate !== "boolean") {
    return "substrate_gate.substrate_adequate must be boolean";
  }
  if (decision.graph_neutral !== true) {
    return "substrate_gate.graph_neutral must be true";
  }
  if (decision.score_eligible !== false) {
    return "substrate_gate.score_eligible must be false";
  }
  return null;
}

export function validateRoutePayload(route) {
  if (!isObject(route)) return "missing route object";
  const routeMap = route.provisional_map;
  const firstNode = route.first_node;
  if (!isObject(routeMap)) return "missing provisional_map object";
  if (!isObject(firstNode)) return "missing first_node object";
  for (const field of ["id", "label", "learner_prompt", "mechanism"]) {
    if (!cleanString(firstNode[field])) return `missing first_node.${field}`;
  }
  if (!Array.isArray(routeMap.backbone) || routeMap.backbone.length === 0) {
    return "provisional_map.backbone must be non-empty";
  }
  if (!Array.isArray(routeMap.clusters)) {
    return "provisional_map.clusters must be an array";
  }

  const firstNodeId = cleanString(firstNode.id);
  const backboneMatches = routeMap.backbone.filter(
    (node) => cleanString(node?.id) === firstNodeId,
  ).length;
  const subnodeMatches = routeMap.clusters.reduce(
    (total, cluster) => total + (Array.isArray(cluster?.subnodes)
      ? cluster.subnodes.filter((node) => cleanString(node?.id) === firstNodeId).length
      : 0),
    0,
  );
  const matches = backboneMatches + subnodeMatches;
  if (matches === 0) return "first_node.id is absent from provisional_map";
  if (matches > 1) return "first_node.id is duplicated in provisional_map";
  return null;
}

export function validateEvaluationPayload(payload, { requireClassification = false } = {}) {
  const evaluation = payload?.evaluation;
  if (!isObject(evaluation)) return "missing evaluation object";
  if (!clean(evaluation.agent_response)) return "missing evaluation.agent_response";
  if (typeof evaluation.score_eligible !== "boolean") {
    return "evaluation.score_eligible must be boolean";
  }
  if (
    (requireClassification || evaluation.score_eligible === true) &&
    !clean(evaluation.classification)
  ) {
    return "missing evaluation.classification";
  }
  return null;
}

export function validateRepairScaffoldPayload(payload) {
  const scaffold = payload?.repair_scaffold;
  if (!isObject(scaffold)) return "missing repair_scaffold object";
  return null;
}

export function validateSocraticDrillPayload(payload) {
  if (!clean(payload?.socratic_question)) return "missing socratic_question";
  return null;
}

export function validateRepairDialoguePayload(payload) {
  const judge = payload?.repair_dialogue;
  if (!isObject(judge)) return "missing repair_dialogue object";
  if (typeof judge.bridge_ready !== "boolean") {
    return "repair_dialogue.bridge_ready must be boolean";
  }
  if (judge.graph_neutral !== true) {
    return "repair_dialogue.graph_neutral must be true";
  }
  if (judge.score_eligible !== false) {
    return "repair_dialogue.score_eligible must be false";
  }
  return null;
}
