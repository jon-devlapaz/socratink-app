import {
  callBridgeSafely,
  invalidBridgeError,
  resultToBridgeError,
} from "../bridge-fail-closed.mjs";
import { eventBuilders } from "../event-facts.mjs";

const GAP_SURFACE = "north_star_reconstruction";
const MAX_VISIBLE_GAP_CHARS = 280;

function northStarGap(events) {
  return events.findLast(
    (event) => event.type === "gap_identified" && event.surface === GAP_SURFACE,
  );
}

function visibleGapFrom(payload, sourceText) {
  const gap = String(payload?.repair_scaffold?.repair_target ?? "").trim();
  if (!gap || gap.length > MAX_VISIBLE_GAP_CHARS || gap.includes("\n")) {
    return null;
  }
  const source = String(sourceText).replace(/\s+/g, " ").trim();
  const normalizedGap = gap.replace(/\s+/g, " ");
  if (normalizedGap.length >= 48 && source.includes(normalizedGap)) {
    return null;
  }
  return gap;
}

export async function handleReconstructionGap({
  events,
  bridge,
  prompt,
  options,
  ctx,
}) {
  if (!ctx.sourceText || !ctx.explanationTarget || !ctx.initialReconstruction) {
    throw new Error("reconstruction-gap-context-required");
  }

  let gapEvent = northStarGap(events);
  const previousFailure = events.at(-1);
  if (
    !gapEvent
    && previousFailure?.type === "bridge_error"
    && previousFailure.phase === "reconstruction_gap"
  ) {
    await prompt.ask("retry_reconstruction_gap", "Retry gap evaluation: ");
  }

  if (!gapEvent) {
    const result = await callBridgeSafely({
      bridge,
      action: "repair-scaffold",
      payload: {
        node_label: ctx.explanationTarget,
        node_mechanism: ctx.sourceText,
        learner_text: ctx.initialReconstruction,
        gap_description:
          "Identify the single most consequential missing causal or explanatory link.",
        log_raw_llm: options.logRawLlm,
      },
    });
    if (!result.ok) {
      events.push(resultToBridgeError({
        result,
        action: "repair-scaffold",
        phase: "reconstruction_gap",
        retryable: true,
      }));
      await prompt.ask("retry_reconstruction_gap", "Retry gap evaluation: ");
      return { llm_calls: [] };
    }

    const gap = visibleGapFrom(result.payload, ctx.sourceText);
    if (!gap) {
      events.push(invalidBridgeError({
        action: "repair-scaffold",
        phase: "reconstruction_gap",
        reason: "gap must be one concise, non-verbatim sentence",
      }));
      await prompt.ask("retry_reconstruction_gap", "Retry gap evaluation: ");
      return { llm_calls: [] };
    }

    const gapId = "north-star-gap-1";
    gapEvent = eventBuilders.gapIdentified({
      surface: GAP_SURFACE,
      gap_id: gapId,
      cue: gap,
      prompt: gap,
      repair_scaffold: result.payload.repair_scaffold,
      graph_neutral: true,
      score_eligible: false,
    });
    events.push(gapEvent);
  }

  const repair = await prompt.ask(
    "initial_repair",
    "Write the repair in your own words: ",
  );
  if (!String(repair).trim()) throw new Error("initial-repair-required");

  const at = ctx.now();
  ctx.initialRepair = repair;
  ctx.initialRepairAt = at;
  events.push(eventBuilders.initialRepairSubmitted({
    text: repair,
    at,
    gap_id: gapEvent.gap_id,
  }));
  console.log("Repair saved exactly as submitted.");
  return {};
}
