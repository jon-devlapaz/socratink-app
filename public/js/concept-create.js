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

    attachChipEditHandlers();
    attachSourceChipHandlers();
  }

  async function doSubmit() {
    if (state.submitting) return;
    state.submitting = true;

    const concept = state.concept.trim();
    const sketch = joinSketch();

    emitTelemetry("concept_create.build_clicked", {
      has_source: Boolean(state.source),
      has_sketch: Boolean(sketch),
    });

    let resolvedSource = state.source;

    // URL source path: hop through /api/extract-url first to materialise text.
    // The /api/extract dispatcher rejects URL sources directly (see main.py
    // _resolve_extract_path: 'URL sources go through /api/extract-url.').
    if (resolvedSource && resolvedSource.type === "url" && !resolvedSource.text) {
      try {
        const { extractUrl } = await import("./api-client.js");
        const fetched = await extractUrl({ url: resolvedSource.url });
        // /api/extract-url returns {text, title, url} per source_intake.
        resolvedSource = {
          type: "text",
          text: String(fetched.text || ""),
          // Preserve the original URL on the resolved source so app.js can
          // store sourceUrl on the concept record. Backend payload uses
          // type: "text" so the dispatcher takes the existing
          // extract_knowledge_map path on this submit.
          url: resolvedSource.url,
        };
      } catch (err) {
        state.submitting = false;
        showSubmitError(
          "source",
          err && err.message ? err.message : "Couldn't fetch that URL."
        );
        return;
      }
    }

    try {
      const { submitConceptCreate } = await import("./ai_service.js");
      const apiKey =
        (typeof localStorage !== "undefined" && localStorage.getItem("gemini_key")) ||
        undefined;
      const data = await submitConceptCreate({
        name: concept,
        startingSketch: sketch,
        source: resolvedSource,
        apiKey,
      });
      state.submitting = false;
      // Hand off to the caller; one of provisional_map / knowledge_map is set.
      onSubmit?.({
        name: concept,
        startingSketch: sketch,
        source: resolvedSource,
        provisionalMap: data.provisional_map || data.knowledge_map || null,
      });
    } catch (err) {
      state.submitting = false;
      if (err && err.status === 422 && err.body) {
        const code = err.body.error;
        const message = err.body.message || "Submission rejected.";
        if (code === "missing_concept") {
          showSubmitError("concept", message);
          return;
        }
        if (code === "thin_sketch_no_source") {
          showSubmitError("sketch", message);
          return;
        }
      }
      showSubmitError(
        "submit",
        (err && err.message) || "Couldn't submit. Try again."
      );
    }
  }

  function showSubmitError(target, message) {
    rerenderSummary();
    if (target === "concept") {
      const valueEl = container.querySelector('[data-role="concept-value"]');
      if (valueEl) {
        valueEl.insertAdjacentHTML(
          "afterend",
          `<p class="creation-chip-footer">${escHtml(message)}</p>`
        );
      }
      return;
    }
    if (target === "sketch") {
      const sketchChip = container.querySelector('[data-chip="sketch"]');
      if (!sketchChip) return;
      const existing = sketchChip.querySelector(".creation-chip-footer");
      if (existing) existing.textContent = message;
      else
        sketchChip.insertAdjacentHTML(
          "beforeend",
          `<p class="creation-chip-footer">${escHtml(message)}</p>`
        );
      return;
    }
    if (target === "source") {
      const sourceChip = container.querySelector('[data-chip="source"]');
      if (!sourceChip) return;
      sourceChip.insertAdjacentHTML(
        "beforeend",
        `<p class="creation-chip-footer">${escHtml(message)}</p>`
      );
      return;
    }
    // Generic fallback: append a banner below the summary.
    const summary = container.querySelector(".creation-summary");
    if (!summary) return;
    summary.insertAdjacentHTML(
      "beforeend",
      `<p class="creation-chip-footer">${escHtml(message)}</p>`
    );
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

  function attachChipEditHandlers() {
    const editConceptBtn = container.querySelector('[data-action="edit-concept"]');
    const editSketchBtn = container.querySelector('[data-action="edit-sketch"]');
    if (editConceptBtn) editConceptBtn.addEventListener("click", () => beginEditConcept());
    if (editSketchBtn) editSketchBtn.addEventListener("click", () => beginEditSketch());
  }

  function beginEditConcept() {
    const valueEl = container.querySelector('[data-role="concept-value"]');
    if (!valueEl) return;
    const prior = state.concept;
    valueEl.innerHTML = `
      <input
        class="creation-chip-input"
        type="text"
        maxlength="200"
        value="${escHtml(prior)}"
        aria-label="Concept name">
    `;
    const input = valueEl.querySelector(".creation-chip-input");
    input.focus();
    input.select();

    function save() {
      const next = input.value.trim();
      if (next !== prior) {
        state.concept = next;
        emitTelemetry("concept_create.summary.edited", { chip: "concept" });
      }
      rerenderSummary();
    }
    function cancel() {
      rerenderSummary();
    }
    input.addEventListener("blur", save);
    input.addEventListener("keydown", (e) => {
      // stopPropagation: prevent the modal-level Escape handler from closing
      // the dialog while we're editing a chip in place.
      if (e.key === "Escape") {
        e.stopPropagation();
        e.preventDefault();
        cancel();
      }
      if (e.key === "Enter") {
        e.preventDefault();
        save();
      }
    });
  }

  function beginEditSketch() {
    const valueEl = container.querySelector('[data-role="sketch-value"]');
    if (!valueEl) return;
    const prior = joinSketch();
    valueEl.innerHTML = `
      <textarea
        class="creation-chip-textarea"
        maxlength="10000"
        rows="4"
        aria-label="Your sketch">${escHtml(prior)}</textarea>
    `;
    const textarea = valueEl.querySelector(".creation-chip-textarea");
    textarea.focus();
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);

    function save() {
      const next = textarea.value;
      if (next !== prior) {
        // Replace all sketchTurns with the edited value as a single turn.
        // Subsequent edits are a single-turn sketch from the learner's POV.
        state.sketchTurns = next.trim() ? [next] : [];
        emitTelemetry("concept_create.summary.edited", { chip: "sketch" });
      }
      rerenderSummary();
    }
    function cancel() {
      rerenderSummary();
    }
    textarea.addEventListener("blur", save);
    textarea.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        e.preventDefault();
        cancel();
      }
      if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        save();
      }
    });
  }

  function beginEditSource() {
    const sourceChip = container.querySelector('[data-chip="source"]');
    if (!sourceChip) return;
    const valueEl = sourceChip.querySelector('[data-role="source-value"]');
    valueEl.innerHTML = `
      <div class="creation-source-panel">
        <div class="overlay-tabs creation-source-tabs">
          <button class="overlay-tab active" type="button" data-tab="paste">Text</button>
          <button class="overlay-tab" type="button" data-tab="url">URL</button>
          <button class="overlay-tab" type="button" data-tab="upload">File</button>
        </div>
        <div class="overlay-panel" data-panel="paste">
          <textarea class="overlay-textarea" placeholder="Paste source material here." maxlength="500000"></textarea>
        </div>
        <div class="overlay-panel" data-panel="url" style="display:none">
          <input class="overlay-url-input" type="url" placeholder="https://example.com/article">
          <p class="overlay-dropfeedback overlay-url-feedback"></p>
        </div>
        <div class="overlay-panel" data-panel="upload" style="display:none">
          <div class="overlay-dropzone">
            Drop a file or click to browse<br>
            <span style="font-size:11px;opacity:0.65">.txt &nbsp; .md &nbsp; .pdf &nbsp; up to 2MB</span>
          </div>
          <input type="file" accept=".txt,.md,.pdf" style="display:none">
          <p class="overlay-dropfeedback overlay-file-feedback"></p>
        </div>
        <div class="creation-source-panel-footer">
          <button class="creation-source-panel-cancel" type="button">Cancel</button>
          <button class="creation-source-panel-attach" type="button" disabled>Attach</button>
        </div>
      </div>
    `;

    const tabs = valueEl.querySelectorAll(".overlay-tab");
    const panels = valueEl.querySelectorAll(".overlay-panel");
    let activeTab = "paste";
    let pendingFileText = "";
    let pendingFileName = "";

    const textarea = valueEl.querySelector(".overlay-textarea");
    const urlInput = valueEl.querySelector(".overlay-url-input");
    const dropzone = valueEl.querySelector(".overlay-dropzone");
    const fileInput = valueEl.querySelector('input[type="file"]');
    const fileFeedback = valueEl.querySelector(".overlay-file-feedback");
    const cancelBtn = valueEl.querySelector(".creation-source-panel-cancel");
    const attachBtn = valueEl.querySelector(".creation-source-panel-attach");

    function panelHasContent() {
      if (activeTab === "paste") return textarea.value.trim().length > 0;
      if (activeTab === "url") return urlInput.value.trim().length > 0;
      return pendingFileText.length > 0;
    }
    function refreshAttachEnabled() {
      attachBtn.disabled = !panelHasContent();
    }

    tabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        activeTab = tab.dataset.tab;
        tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === activeTab));
        panels.forEach((p) => {
          p.style.display = p.dataset.panel === activeTab ? "" : "none";
        });
        valueEl.querySelectorAll(".overlay-dropfeedback").forEach((f) => {
          f.textContent = "";
          f.className = "overlay-dropfeedback";
        });
        refreshAttachEnabled();
      });
    });

    textarea.addEventListener("input", refreshAttachEnabled);
    // URL validation is server-side: Task 9 hops through /api/extract-url, which
    // applies source_intake's allow-list (private-IP block, video-host block, scheme
    // checks). The client only enables Attach when the field is non-empty.
    urlInput.addEventListener("input", refreshAttachEnabled);

    dropzone.addEventListener("click", () => fileInput.click());
    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });
    dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      const f = e.dataTransfer.files?.[0];
      if (f) handleFile(f);
    });
    fileInput.addEventListener("change", () => {
      const f = fileInput.files?.[0];
      if (f) handleFile(f);
    });

    function handleFile(file) {
      // Two-megabyte cap mirrors the form-era constraint.
      if (file.size > 2 * 1024 * 1024) {
        fileFeedback.className = "overlay-dropfeedback error";
        fileFeedback.textContent = "File is over 2MB.";
        pendingFileText = "";
        pendingFileName = "";
        refreshAttachEnabled();
        return;
      }
      const reader = new FileReader();
      reader.onload = () => {
        pendingFileText = String(reader.result || "");
        pendingFileName = file.name;
        fileFeedback.className = "overlay-dropfeedback ok";
        fileFeedback.textContent = `${file.name} · ${pendingFileText.length.toLocaleString()} chars`;
        refreshAttachEnabled();
      };
      reader.onerror = () => {
        fileFeedback.className = "overlay-dropfeedback error";
        fileFeedback.textContent = "Couldn't read that file.";
        pendingFileText = "";
        pendingFileName = "";
        refreshAttachEnabled();
      };
      reader.readAsText(file);
    }

    cancelBtn.addEventListener("click", () => rerenderSummary());

    attachBtn.addEventListener("mousedown", (e) => {
      e.preventDefault();
      if (attachBtn.disabled) return;
      if (activeTab === "paste") {
        const text = textarea.value.trim();
        if (!text) return;
        state.source = { type: "text", text };
      } else if (activeTab === "url") {
        // The Plan A backend expects URL fetching to go through /api/extract-url
        // (separate endpoint). For now we capture the URL on the client; Task 9
        // routes URL submits through that endpoint. The chip stores the URL
        // and the fetched text once the URL endpoint succeeds.
        const url = urlInput.value.trim();
        if (!url) return;
        state.source = { type: "url", url, text: "", filename: "" };
      } else {
        if (!pendingFileText) return;
        state.source = { type: "file", text: pendingFileText, filename: pendingFileName };
      }
      emitTelemetry("concept_create.source.added", { type: state.source.type });
      rerenderSummary();
    });
  }

  function attachSourceChipHandlers() {
    const addBtn = container.querySelector('[data-action="add-source"]');
    const replaceBtn = container.querySelector('[data-action="replace-source"]');
    if (addBtn) addBtn.addEventListener("click", () => beginEditSource());
    if (replaceBtn) replaceBtn.addEventListener("click", () => beginEditSource());
  }

  // Boot the first chat turn.
  renderChat();

  return { destroy };
}
