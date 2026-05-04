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

  // Helper: minimal escape for inline text (we only inject sanitized strings,
  // but defensive-by-default — these never escape into innerHTML untrusted).
  function escHtml(s) {
    return String(s ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function questionForStage(stage) {
    if (stage === STAGE.CHAT_TURN_1) return CHAT_COPY.TURN_1;
    if (stage === STAGE.CHAT_TURN_2) return CHAT_COPY.TURN_2;
    if (stage === STAGE.CHAT_FALLBACK) return CHAT_COPY.FALLBACK;
    return "";
  }

  function turnNumberForStage(stage) {
    if (stage === STAGE.CHAT_TURN_1) return 1;
    if (stage === STAGE.CHAT_TURN_2) return 2;
    if (stage === STAGE.CHAT_FALLBACK) return "fallback";
    return null;
  }

  function renderChat() {
    const turn = turnNumberForStage(state.stage);
    const question = questionForStage(state.stage);
    const hasPrior = state.sketchTurns.length > 0 || state.concept !== "";

    container.innerHTML = `
      <div class="creation-chat" data-stage="${escHtml(state.stage)}">
        <p class="creation-chat-question" id="creation-chat-question">${escHtml(question)}</p>
        <textarea
          class="creation-chat-composer"
          id="creation-chat-composer"
          aria-labelledby="creation-chat-question"
          maxlength="2000"
          rows="3"
          placeholder=""></textarea>
        <div class="creation-footer">
          <button class="creation-cancel" type="button">Cancel</button>
          <button class="creation-submit" type="button" disabled>Continue</button>
        </div>
      </div>
    `;

    const composer = container.querySelector(".creation-chat-composer");
    const cancelBtn = container.querySelector(".creation-cancel");
    const submitBtn = container.querySelector(".creation-submit");

    composer.focus();
    composer.addEventListener("input", () => {
      submitBtn.disabled = composer.value.trim().length === 0;
    });
    composer.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !submitBtn.disabled) {
        e.preventDefault();
        submitChatTurn(composer.value.trim());
      }
      if (e.key === "Escape") {
        e.preventDefault();
        onCancel?.();
      }
    });

    cancelBtn.addEventListener("click", () => onCancel?.());
    submitBtn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      if (submitBtn.disabled) return;
      submitChatTurn(composer.value.trim());
    });

    emitTelemetry("concept_create.chat.turn_started", {
      turn,
      has_prior_reply: hasPrior,
    });
  }

  function submitChatTurn(reply) {
    if (!reply) return;
    const turn = turnNumberForStage(state.stage);

    if (state.stage === STAGE.CHAT_TURN_1) {
      // Turn 1 reply is the concept name (verbatim for v1; canonicalisation
      // is a documented follow-up). The learner can edit the chip later.
      state.concept = reply;
      emitTelemetry("concept_create.chat.turn_replied", {
        turn,
        reply_len: reply.length,
        used_fallback: false,
      });
      state.stage = STAGE.CHAT_TURN_2;
      renderChat();
      return;
    }

    if (state.stage === STAGE.CHAT_TURN_2) {
      state.sketchTurns.push(reply);
      const isThin = !isSubstantiveSketch(reply);
      emitTelemetry("concept_create.chat.turn_replied", {
        turn,
        reply_len: reply.length,
        used_fallback: false,
      });
      if (isThin) {
        state.stage = STAGE.CHAT_FALLBACK;
        state.usedFallback = true;
        renderChat();
        return;
      }
      state.stage = STAGE.SUMMARY;
      renderSummary();
      return;
    }

    if (state.stage === STAGE.CHAT_FALLBACK) {
      state.sketchTurns.push(reply);
      emitTelemetry("concept_create.chat.turn_replied", {
        turn,
        reply_len: reply.length,
        used_fallback: true,
      });
      state.stage = STAGE.SUMMARY;
      renderSummary();
      return;
    }
  }

  // Placeholder until Task 5 ships the real summary renderer.
  function renderSummary() {
    container.innerHTML =
      '<div class="creation-summary"><p>Summary card pending (Task 5).</p></div>';
  }

  // Boot the first chat turn.
  renderChat();

  return { destroy };
}
