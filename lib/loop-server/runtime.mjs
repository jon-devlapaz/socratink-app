import { pathToFileURL } from "node:url";
import { createBridgeClient } from "../bridge/client.mjs";
import { llmEnvOverrides } from "./llm-options.mjs";
import { resolveTuiPaths, preflightTuiPaths } from "../config/paths.mjs";
import {
  createSessionKernel,
  loadAgentContracts,
  makeAgentLookup,
} from "../seda/session-kernel.mjs";
import {
  CannotRehydrateSession,
  createRehydratedSessionKernel,
} from "../seda/session-rehydration.mjs";
import { eventBuilders } from "../seda/event-facts.mjs";
import { initTrainingDerive } from "../seda/training-summary.mjs";

const paths = resolveTuiPaths();
preflightTuiPaths(paths);
const { callBridge, callBridgeResult } = createBridgeClient(paths);
await initTrainingDerive(paths);
const trainingStore = await import(
  pathToFileURL(paths.trainingStorePath).href
);
const { createTrainingStore } = trainingStore;

export async function loadAgentLookup() {
  const contracts = await loadAgentContracts(paths.workspaceRoot);
  const lookup = makeAgentLookup(contracts);
  return { contracts, lookup };
}

export function makeSections() {
  return function section(_kind, label) {
    return `[${label}]`;
  };
}

function sessionBridgeWithDiagnostics({ llm, diagnosticsDir = null } = {}) {
  const envOverrides = llmEnvOverrides(llm);
  if (!envOverrides && !diagnosticsDir) return { callBridge, callBridgeResult };
  const client = createBridgeClient({ ...paths, envOverrides, diagnosticsDir });
  return {
    callBridge: client.callBridge,
    callBridgeResult: client.callBridgeResult,
  };
}

export async function createSessionState({
  agentLookup,
  agentContracts,
  id = null,
  events = null,
  llm = null,
  sourceLessDoorBootstrap = false,
  northStarIntake = false,
  sourceRevision = null,
  bridgeDiagnosticsDir = null,
}) {
  const bridge = sessionBridgeWithDiagnostics({ llm, diagnosticsDir: bridgeDiagnosticsDir });
  const kernel = events
    ? await createRehydratedSessionKernel({
        createTrainingStore,
        bridge,
        agentContracts,
        agentLookup,
        section: makeSections(),
        colorEnabled: false,
        logDir: null,
        events,
      })
    : createSessionKernel({
        createTrainingStore,
        bridge,
        agentContracts,
        agentLookup,
        section: makeSections(),
        colorEnabled: false,
        logDir: null,
      });
  bindResolvedSourceRevision(kernel, sourceRevision, {
    isRehydrated: Array.isArray(events),
  });
  return {
    id: id || crypto.randomUUID(),
    phase: events
      ? (kernel.phase ?? "idle")
      : northStarIntake === true
        ? "source_intake"
        : (kernel.phase || "idle"),
    status: "active",
    pendingInput: null,
    transcript: [],
    awaiting: null,
    record: null,
    llm: llm || null,
    bridgeDiagnosticsDir,
    ...kernel,
    evidenceHolds: kernel.ctx.evidenceHolds,
    options: {
      color: "never",
      logRawLlm: false,
      loopUi: true,
      loopUiPacing: "one_beat",
      sourceLessDoorBootstrap: sourceLessDoorBootstrap === true,
    },
  };
}

export { paths };

function bindResolvedSourceRevision(kernel, sourceRevision, { isRehydrated }) {
  const persisted = kernel.ctx.sourceRevision;
  if (persisted && !sourceRevision) {
    throw new CannotRehydrateSession("referenced source revision was not resolved", {
      source_revision_id: persisted.revision_id,
    });
  }
  if (!sourceRevision) return;

  const fact = {
    source_id: sourceRevision.sourceId,
    revision_id: sourceRevision.revisionId,
    normalization_version: sourceRevision.normalizationVersion,
    extraction_version: sourceRevision.extractionVersion,
    parser_version: sourceRevision.parserVersion,
    source_kind: sourceRevision.sourceKind,
  };
  if (
    !sourceRevision.normalizedText
    || (
      persisted
      && !sourceRevisionFactMatches(persisted, fact)
    )
  ) {
    throw new CannotRehydrateSession("resolved source revision does not match session fact", {
      source_revision_id: persisted?.revision_id || fact.revision_id,
    });
  }
  kernel.ctx.sourceText = sourceRevision.normalizedText;
  kernel.ctx.sourceRevision = fact;
  if (!isRehydrated) {
    kernel.events.push(eventBuilders.sourceReferenced({
      sourceRevision: fact,
      at: kernel.ctx.now(),
    }));
  }
}

function sourceRevisionFactMatches(left, right) {
  return (
    left?.source_id === right.source_id
    && left?.revision_id === right.revision_id
    && left?.normalization_version === right.normalization_version
    && left?.extraction_version === right.extraction_version
    && left?.parser_version === right.parser_version
    && left?.source_kind === right.source_kind
  );
}
