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

  function joinSketch() {
    return state.sketchTurns.filter((s) => s && s.trim()).join("\n\n");
  }

  function sketchIsSubstantive() {
    return isSubstantiveSketch(joinSketch());
  }

  function ctaCopyForState() {
    if (state.source && sketchIsSubstantive()) return "Build from my map and source";
    if (state.source && !sketchIsSubstantive()) return "Build from source";
    if (!state.source && sketchIsSubstantive()) return "Build from my starting map";
    // Disabled state — copy still reads "Build from my starting map" so the
    // CTA does not flicker text on every keystroke; the disabled attribute +
    // the sketch-chip footer copy carry the strategy framing instead.
    return "Build from my starting map";
  }

  function ctaEnabledForState() {
    const concept = state.concept.trim();
    if (!concept) return false;
    if (state.source) return true;
    return sketchIsSubstantive();
  }

  function sourceChipDescriptor() {
    if (!state.source) return null;
    if (state.source.type === "url") {
      const len = (state.source.text || "").length.toLocaleString();
      return `${len} chars from a URL`;
    }
    if (state.source.type === "file") {
      const filename = state.source.filename || "file";
      const len = (state.source.text || "").length.toLocaleString();
      return `${filename} · ${len} chars`;
    }
    // text
    const len = (state.source.text || "").length.toLocaleString();
    return `${len} chars pasted`;
  }

  function renderSummary() {
    const concept = state.concept.trim();
    const sketch = joinSketch();
    const sketchOk = isSubstantiveSketch(sketch);
    const sourceDesc = sourceChipDescriptor();
    const ctaCopy = ctaCopyForState();
    const ctaEnabled = ctaEnabledForState();

    const breadcrumbLabel =
      concept ? `↑ chat (collapsed): "${escHtml(concept)}" · sketch captured`
              : "↑ chat (collapsed): sketch captured";

    const sketchBlockedFooter = !state.source && !sketchOk;

    container.innerHTML = `
      <div class="creation-summary">
        <p class="creation-chat-breadcrumb" aria-hidden="true">${breadcrumbLabel}</p>

        <span class="creation-section-eyebrow">STARTING MAP</span>

        <article class="creation-chip" data-chip="concept">
          <div class="creation-chip-label-row">
            <span class="creation-chip-label">CONCEPT</span>
            <button class="creation-chip-action" type="button" data-action="edit-concept">edit</button>
          </div>
          <div class="creation-chip-value" data-role="concept-value">${escHtml(concept)}</div>
        </article>

        <article class="creation-chip" data-chip="sketch">
          <div class="creation-chip-label-row">
            <span class="creation-chip-label">YOUR SKETCH</span>
            <button class="creation-chip-action" type="button" data-action="edit-sketch">edit</button>
          </div>
          <div class="creation-chip-value" data-role="sketch-value">${escHtml(sketch)}</div>
          ${sketchBlockedFooter
            ? `<p class="creation-chip-footer" data-role="sketch-footer">${escHtml(SKETCH_FOOTER_BLOCKED)}</p>`
            : ""}
        </article>

        <article class="creation-chip ${sourceDesc ? "" : "creation-chip-empty"}" data-chip="source">
          <div class="creation-chip-label-row">
            <span class="creation-chip-label">SOURCE MATERIAL</span>
            <button class="creation-chip-action" type="button" data-action="${sourceDesc ? "replace-source" : "add-source"}">
              ${sourceDesc ? "replace" : "Add source"}
            </button>
          </div>
          <div class="creation-chip-value" data-role="source-value">
            ${sourceDesc
              ? escHtml(sourceDesc)
              : '<span class="creation-chip-empty-text">None added — build will start from your model only</span>'}
          </div>
        </article>

        <div class="creation-footer">
          <button class="creation-cancel" type="button">Cancel</button>
          <button class="creation-submit creation-build-cta" type="button" ${ctaEnabled ? "" : "disabled"}>
            ${escHtml(ctaCopy)}
          </button>
        </div>

        <p class="creation-dialog-meta">${FOOTER_DEFAULT}</p>
      </div>
    `;

    // Wire cancel + submit (the chip edit + source actions land in Tasks 7-8).
    container.querySelector(".creation-cancel").addEventListener("click", () => onCancel?.());
    const submitBtn = container.querySelector(".creation-submit");
    submitBtn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      if (submitBtn.disabled) {
        const reason = !state.concept.trim()
          ? "missing_concept"
          : "thin_sketch_no_source";
        handleDisabledClickAttempt(reason);
        return;
      }
      doSubmit();
    });

    emitTelemetry("concept_create.summary.shown", {
      has_concept: Boolean(concept),
      has_sketch: Boolean(sketch),
      sketch_len: sketch.length,
    });
  }

  // Stub — real submit ships in Task 9.
  function doSubmit() {
    /* implemented in Task 9 */
  }

  function rerenderSummary() {
    // Cheap full re-render — chip state is small, DOM is shallow, no
    // animation interrupted by re-render in v1. If perf bites later,
    // swap to surgical updates per chip.
    renderSummary();
  }

  // Wire the disabled-CTA telemetry. The CTA's disabled attribute prevents
  // the click in normal use, but if an integration test or assistive tech
  // somehow triggers an activation we want telemetry to log the block.
  // (Server-side validation is the authority either way.)
  function handleDisabledClickAttempt(reason) {
    emitTelemetry("concept_create.build_blocked", {
      reason,
      origin: "client",
    });
  }

  // Boot the first chat turn.
  renderChat();

  return { destroy };
}
