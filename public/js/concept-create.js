// public/js/concept-create.js
//
// Conversational concept creation — Stage A (chat) → Stage B (summary card).
// Replaces the form-based showNameField branch of buildContentInputUI.
// Spec: docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md
// Plan: docs/superpowers/plans/2026-05-04-conversational-concept-creation-frontend.md
//
// Public API: buildConversationalCreateUI(container, { onSubmit, onCancel }).
// Returns { destroy() } so callers can clean up on dialog close.
//
// This module owns ZERO graph rendering and ZERO API key reading. It receives
// onSubmit({ name, startingSketch, source }) and the caller posts to the
// backend — same separation of concerns the form-based flow used.

import { isSubstantiveSketch } from "./sketch-validation.js";
import { emitTelemetry } from "./telemetry.js";

const STAGE = Object.freeze({
  CHAT_TURN_1: "chat:turn-1",
  CHAT_TURN_2: "chat:turn-2",
  CHAT_FALLBACK: "chat:fallback",
  SUMMARY: "summary",
});

// Hardcoded chat copy for v1. The shape is locked by the spec; the literal
// strings derive verbatim from the threshold-chat system prompt example
// (app_prompts/threshold-chat-system-v1.txt) so no voice drift can sneak in
// while the frontend still hardcodes them. A future plan wires these to a
// /api/threshold-chat-turn endpoint and removes the hardcode.
const CHAT_COPY = Object.freeze({
  TURN_1: "What do you want to understand?",
  TURN_2: "Sketch what you think it does — rough is fine. What parts come to mind?",
  // The fallback is generic-but-honest for v1: "inputs and outputs" is the
  // input-output frame most causal concepts share, derived in spirit from the
  // spec's analogical-fallback rule. Concept-derived analogy generation is a
  // documented Plan B follow-up — see plan §"Out of scope".
  FALLBACK:
    "Try this: think of something familiar that takes inputs and produces outputs. " +
    "What inputs does this concept take, and what does it produce?",
});

const FOOTER_DEFAULT = "Study content stays locked until the cold attempt.";
const SKETCH_FOOTER_BLOCKED =
  "A few words about how you think it works will give socratink something to draft from. " +
  "Or attach source material — either path opens the build.";

export function buildConversationalCreateUI(container, { onSubmit, onCancel }) {
  const state = {
    stage: STAGE.CHAT_TURN_1,
    concept: "",
    sketchTurns: [],          // verbatim learner replies; concatenated into chip value
    source: null,              // { type, text?, url?, filename? } once attached
    usedFallback: false,
    submitting: false,
  };

  function destroy() {
    container.innerHTML = "";
  }

  // Subsequent tasks fill in renderChat / renderSummary / submit logic and
  // call them from here. For now, stub with a placeholder so the module is
  // importable without errors.
  container.innerHTML = "";

  return { destroy };
}
