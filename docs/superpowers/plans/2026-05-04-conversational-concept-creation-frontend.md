# Conversational Concept Creation — Frontend (Plan B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the form-based `showNameField` branch of `buildContentInputUI` (in `public/js/app.js:684`) with a two-stage conversational flow — Threshold chat → Summary card with three chips and a state-dependent build CTA — wired to the Plan A backend at `POST /api/extract` (already on `dev` at commit `086e617`).

**Architecture:**
- A small chat surface drives a 2-turn (+ optional analogical-fallback) state machine and exits to a summary card. The card holds three editable chips (`Concept`, `Your sketch`, `Source material`) and one CTA whose copy + enabled state derives from a 4-state truth table (spec §3.2). Submit posts `{name, starting_sketch, source}` to `/api/extract`; the backend dispatches between `generate_provisional_map_from_sketch` (no source) and `extract_knowledge_map` (source attached).
- Substantiveness is enforced server-side as the authority; the frontend ports `models/sketch_validation.py` to JS as a UX optimisation that disables the CTA preemptively. Parity is locked by `tests/fixtures/sketch_validation_parity.json` (28 entries incl. unicode) and verified by a node-based fixture test that runs in `pytest`.
- Frontend telemetry events fire through a tiny `Bus.emit('telemetry', …)` + `console.info('telemetry', …)` helper. No backend post endpoint exists yet for client telemetry; that is a documented Plan B follow-up. Server-side telemetry from Plan A is unchanged.

**Tech Stack:**
- Vanilla ES modules in `public/js/`, plain CSS in `public/css/`. No frameworks, no build step, no new npm packages.
- Tests run via `pytest` shelling out to `node --check` (see `tests/test_frontend_syntax.py` for the existing pattern). The new parity test will follow the same shape: load fixture JSON, run a small node script that requires the JS module, compare verdicts.
- Backend is already shipped on `dev`. This plan touches **zero Python production code**; only JS, CSS, and one new test file plus a small node-side runner.

---

## File Structure

### Created
- `public/js/sketch-validation.js` — JS port of `models/sketch_validation.py`. Exported `isSubstantiveSketch(text: string): boolean`. Module-only (no DOM access).
- `public/js/telemetry.js` — Tiny helper. Single export `emitTelemetry(event, extra)`. Wraps `Bus.emit('telemetry', …)` and `console.info('telemetry', …)`. No network calls in v1.
- `public/js/concept-create.js` — New module owning the conversational flow. Exports `buildConversationalCreateUI(container, { onSubmit, onCancel })`. Internal state machine for chat turns + summary card. Imports `isSubstantiveSketch` and `emitTelemetry`.
- `tests/test_frontend_sketch_validation.py` — Pytest harness that runs a node script against `tests/fixtures/sketch_validation_parity.json` and asserts byte-for-byte parity with the Python heuristic. Skips when `node` is not on PATH (mirrors `test_frontend_syntax.py`).
- `tests/_helpers/run_sketch_parity.mjs` — Node runner used by the pytest harness. Loads the fixture, calls `isSubstantiveSketch` for each entry, prints JSON `[{idx, text, expected, actual}]` to stdout. No deps, single file.

### Modified
- `public/js/app.js` — Remove the entire `showNameField === true` branch from `buildContentInputUI` (line 684 onward, including its HTML template, placeholder rotators `PLACEHOLDERS` / `NAME_PLACEHOLDERS` / `phTimer` / `namePhTimer`, and submit construction of `thresholdContext`). The `showNameField === false` branch stays intact (used by other inline-overlay flows). Update `startAddConcept` (line 1199) to call `buildConversationalCreateUI` from the new module instead of `buildContentInputUI({ showNameField: true })`. Update the success path to consume `{provisional_map}` for the new payload while still consuming `{knowledge_map}` for legacy (server returns one or the other depending on dispatch).
- `public/js/ai_service.js` — Add a new export `submitConceptCreate({ name, startingSketch, source, apiKey })` that posts the new payload shape and surfaces 422 `{error, message}` to callers. Keep `generateKnowledgeMap(rawText)` for back-compat (some callers may still use it) but it is no longer invoked by the modal.
- `public/css/components.css` — **Delete** the form-only classes: `.creation-intro`, `.creation-intro-compact`, `.creation-intro-row`, `.creation-intro-title`, `.creation-intro-copy`, `.creation-name-input` + focus/placeholder, `.creation-threshold` + head/copy/input/focus/placeholder, `.creation-fuzzy-toggle` + states, `.creation-fuzzy-row`, `.creation-fuzzy-hint`, `.creation-fuzzy-panel`, `.creation-fuzzy-input`, `.creation-source-meta`, `.creation-source-copy`, `.creation-source-header`, `.creation-validation`. **Keep** the modal shell classes (`.creation-dialog*`), the redesigned `.creation-source-tabs .overlay-tab` styles, `.creation-cancel`, `.creation-submit`, `.creation-footer`, and the `.paste-clipboard-btn` / `.paste-actions` row. **Add** new classes for the chat surface and summary card (Task 7 spells these out explicitly).

### Untouched
- `public/js/api-client.js`, `public/js/auth.js`, `public/js/login.js`, `public/js/feedback.js`, `public/js/graph-view.js`, `public/js/store.js`, `public/js/dom.js`, `public/js/welcome.js`, `public/js/intro-particles.js`, `public/js/tooltips.js`.
- All Python production code under `main.py`, `ai_service.py`, `learning_commons.py`, `models/`, `app_prompts/`. These ship from Plan A and the frontend trusts the contract.
- All existing tests under `tests/` (apart from the new parity test added in this plan).

---

## Self-Review Anchor (read before starting Task 1)

Spec coverage map (each spec section → tasks that cover it):
- §3.1 (Stage A — chat) → Task 4, Task 5.
- §3.2 (Stage B — summary card incl. chip table, CTA truth table, validation copy, edit interactions) → Task 6, Task 7, Task 8.
- §3.3 (Stage C — submit dispatch + LC-as-enrichment trust) → Task 9.
- §4 (frontend file map) → Task 8 (deletion), Task 11 (CSS delete + add).
- §5.4 (telemetry events) → Task 2 (helper) + the events are planted at the correct call sites in Tasks 4, 6, 7, 9.
- §8 (acceptance criteria) → Task 12 (verification gate).
- Anti-pattern list (Appendix B + handoff §"Anti-patterns") → enforced by the absolute bans the implementer must reject; checked in Task 12.

Type/name consistency lock-in (used across tasks):
- `isSubstantiveSketch(text)` — JS export name. Camel-case (JS convention) even though the Python is `is_substantive_sketch`.
- `emitTelemetry(event, extra)` — single argument shape; `event` is a string like `concept_create.summary.shown`, `extra` is a plain object.
- `buildConversationalCreateUI(container, { onSubmit, onCancel })` — top-level public API of `concept-create.js`. Returns `{ destroy() }` to mirror the existing `buildContentInputUI` contract.
- Internal stage constants: `'chat:turn-1' | 'chat:turn-2' | 'chat:fallback' | 'summary'`.
- Chip identifiers used in telemetry: `'concept' | 'sketch' | 'source'`.
- Source `type` values: `'text' | 'url' | 'file'` — matches backend `SourceAttachment` model.
- Submit payload shape: `{ name: string, starting_sketch: string, source: null | { type, text?, url?, filename? } }`.
- Response shape: `{ provisional_map: {...} }` (no source) or `{ knowledge_map: {...} }` (source attached). Both render with the same downstream graph code; the caller normalizes.

---

## Task 1: JS port of `isSubstantiveSketch` (parity-locked)

**Goal:** A single-file ES module that returns the same verdict as `models/sketch_validation.py` for every entry in `tests/fixtures/sketch_validation_parity.json`. Unicode-correct (`\p{L}\p{N}_\s` with `/u` flag), `MIN_SUBSTANTIVE_TOKENS = 8`, identical stopword set, identical "don't know" pattern list, identical repeated-character rule.

**Files:**
- Create: `public/js/sketch-validation.js`
- Create: `tests/_helpers/run_sketch_parity.mjs`
- Create: `tests/test_frontend_sketch_validation.py`

- [ ] **Step 1: Write the parity-fixture pytest harness (failing test)**

The Python test runs the node helper once and asserts every fixture entry agrees. This is the harness; the JS module does not exist yet.

```python
# tests/test_frontend_sketch_validation.py
"""JS parity test for is_substantive_sketch.

Loads the shared fixture (used by both Python tests and this JS harness),
shells out to a small node runner, and asserts byte-for-byte verdict parity.
A divergence is a release-blocker per spec §5.3 / handoff §2.

Skipped when `node` is unavailable (mirrors tests/test_frontend_syntax.py).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "sketch_validation_parity.json"
RUNNER = REPO_ROOT / "tests" / "_helpers" / "run_sketch_parity.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")
def test_js_sketch_validation_matches_python_for_every_fixture_entry() -> None:
    assert FIXTURE.exists(), f"fixture missing: {FIXTURE}"
    assert RUNNER.exists(), f"node runner missing: {RUNNER}"

    result = subprocess.run(
        ["node", str(RUNNER)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    assert result.returncode == 0, (
        f"node runner failed:\nstdout={result.stdout}\nstderr={result.stderr}"
    )

    rows = json.loads(result.stdout)
    assert isinstance(rows, list) and rows, "runner produced no rows"

    mismatches = [r for r in rows if r["expected"] != r["actual"]]
    if mismatches:
        msg = "\n".join(
            f"  idx={r['idx']} text={r['text']!r} expected={r['expected']} actual={r['actual']}"
            for r in mismatches
        )
        pytest.fail(
            f"JS sketch_validation diverges from Python on {len(mismatches)}/{len(rows)} entries:\n{msg}"
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/test_frontend_sketch_validation.py -v`
Expected: FAIL with `node runner missing` (the runner does not exist yet).

- [ ] **Step 3: Write the node runner**

```javascript
// tests/_helpers/run_sketch_parity.mjs
// Loads the shared parity fixture, runs the JS implementation, prints JSON rows.
// No deps — uses Node's built-in fs and URL handling.

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

import { isSubstantiveSketch } from "../../public/js/sketch-validation.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const fixturePath = resolve(__dirname, "..", "fixtures", "sketch_validation_parity.json");
const fixture = JSON.parse(readFileSync(fixturePath, "utf8"));

const rows = fixture.entries.map((entry, idx) => ({
  idx,
  text: entry.text,
  expected: entry.expected_substantive,
  actual: isSubstantiveSketch(entry.text),
}));

process.stdout.write(JSON.stringify(rows));
```

- [ ] **Step 4: Run test again to verify it still fails (different reason)**

Run: `.venv/bin/pytest tests/test_frontend_sketch_validation.py -v`
Expected: FAIL — node now reports it cannot resolve `../../public/js/sketch-validation.js` (the JS module does not exist yet).

- [ ] **Step 5: Write the JS implementation (parity-locked)**

```javascript
// public/js/sketch-validation.js
//
// Substantiveness heuristic — JS port of models/sketch_validation.py.
// Verified against tests/fixtures/sketch_validation_parity.json by
// tests/test_frontend_sketch_validation.py. A divergence is a
// release-blocker per spec §5.3.
//
// Why /u everywhere: Python's \w is Unicode by default; JS's is ASCII-only.
// Without /u, the same input ("café résumé naïve …") would tokenize differently
// in the two languages and the parity fixture's unicode rows would silently
// fail. See models/sketch_validation.py "JS PORT NOTE" docstring.

export const MIN_SUBSTANTIVE_TOKENS = 8;

const DONT_KNOW_PATTERNS = [
  "idk",
  "i dont know",
  "i don't know",
  "no idea",
  "no clue",
  "dunno",
  "not sure",
];

const STOPWORDS = new Set(
  (
    "a an the and or but if of for in on at to from by with as is are was were " +
    "be been being do does did has have had this that these those it its"
  ).split(/\s+/)
);

const PUNCT_RE = /[^\p{L}\p{N}_\s]/gu;
const WHITESPACE_RE = /\s+/gu;
const REPEATED_CHAR_RE = /^(.)\1{4,}$/u;

function normalize(text) {
  let t = text.trim().toLowerCase();
  t = t.replace(PUNCT_RE, " ");
  t = t.replace(WHITESPACE_RE, " ");
  return t.trim();
}

function isDontKnow(normalized) {
  if (!normalized) return true;
  if (REPEATED_CHAR_RE.test(normalized)) return true;
  for (const pattern of DONT_KNOW_PATTERNS) {
    if (normalized === pattern) return true;
    if (normalized.startsWith(pattern + " ")) {
      const extra = normalized.slice(pattern.length + 1).split(/\s+/u).filter(Boolean);
      if (extra.length <= 3) return true;
    }
  }
  return false;
}

function countSubstantiveTokens(normalized) {
  const tokens = normalized.split(/\s+/u).filter((t) => t && t.length >= 2);
  let count = 0;
  for (const t of tokens) {
    if (!STOPWORDS.has(t)) count += 1;
  }
  return count;
}

export function isSubstantiveSketch(text) {
  if (text === null || text === undefined) return false;
  if (typeof text !== "string") return false;
  const normalized = normalize(text);
  if (!normalized) return false;
  if (isDontKnow(normalized)) return false;
  if (countSubstantiveTokens(normalized) < MIN_SUBSTANTIVE_TOKENS) return false;
  return true;
}
```

- [ ] **Step 6: Run parity test to verify it passes**

Run: `.venv/bin/pytest tests/test_frontend_sketch_validation.py -v`
Expected: PASS.

If any fixture entry fails, do **not** edit the fixture. Edit the JS until it conforms — see the failure message; the most common drift is forgetting the `/u` flag on a regex or letting `length >= 2` exclude a 2-byte multi-codepoint glyph.

- [ ] **Step 7: Run the existing module-syntax test to make sure the new JS file parses**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS — including a parametrized case for `sketch-validation.mjs`.

- [ ] **Step 8: Commit**

```bash
git add public/js/sketch-validation.js \
        tests/_helpers/run_sketch_parity.mjs \
        tests/test_frontend_sketch_validation.py
git commit -m "feat(ui): port is_substantive_sketch to JS with parity test"
```

---

## Task 2: Frontend telemetry helper

**Goal:** A single-line emit point that flows the spec §5.4 frontend events through `Bus` and `console.info`. No backend post endpoint in v1; that's a follow-up tracked in the PR description.

**Files:**
- Create: `public/js/telemetry.js`
- Test: `tests/test_frontend_syntax.py` (already covers — verifies the new module parses)

- [ ] **Step 1: Write the telemetry helper**

```javascript
// public/js/telemetry.js
//
// Frontend telemetry emit point for the conversational concept-creation flow.
// Spec §5.4 lists the events. The events are observable in three places:
//
//   1. Browser console (`console.info('telemetry', { event, ...extra })`)
//   2. Bus listeners (`Bus.on('telemetry', fn)`) — for in-app debug overlays
//   3. Future: a /api/telemetry endpoint. Not wired in v1 — the helper takes
//      one shape so adding the network post is a one-line change later.
//
// Server-side telemetry (concept_create.lc.queried, .build_blocked, .ai_call,
// etc.) flows through Python's structured logger from main.py — that path is
// already shipped in Plan A. Client events use `origin: 'client'` so the
// dashboards can detect client/server validation drift.

import { Bus } from "./bus.js";

export function emitTelemetry(event, extra = {}) {
  if (typeof event !== "string" || !event) return;
  const payload = { event, ...extra };
  try {
    Bus.emit("telemetry", payload);
  } catch (err) {
    /* Bus is best-effort. Never let telemetry break the UI. */
  }
  // eslint-disable-next-line no-console
  console.info("telemetry", payload);
}
```

- [ ] **Step 2: Verify module-syntax test picks up the new file**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS, including `telemetry.mjs` as a parametrized case.

- [ ] **Step 3: Commit**

```bash
git add public/js/telemetry.js
git commit -m "feat(ui): add minimal telemetry helper for concept-create events"
```

---

## Task 3: Scaffold `concept-create.js` module shell

**Goal:** Stand up the new module with its public API and a no-op stage machine, so subsequent tasks can fill in the surfaces without a name/wiring scramble at the end.

**Files:**
- Create: `public/js/concept-create.js`

- [ ] **Step 1: Write the module skeleton**

```javascript
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
```

- [ ] **Step 2: Run the module-syntax test**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS — concept-create.mjs parses.

- [ ] **Step 3: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): scaffold concept-create module shell"
```

---

## Task 4: Stage A — chat surface + state machine

**Goal:** Render the breadcrumb header (eyebrow `NEW CONCEPT`, title `Start a concept`), an AI-question line, a textarea composer, and a submit button. Drive the turn-1 → turn-2 → (fallback?) → exit transitions. Emit `concept_create.chat.turn_started` and `concept_create.chat.turn_replied` per spec §5.4. Cancel calls `onCancel()`. No chat bubbles, no avatars, no typing indicators — text on the page, calm composer.

**Files:**
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Add the chat renderer**

Inside `buildConversationalCreateUI`, add functions and call the first one when the stage is one of the chat stages.

```javascript
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
```

- [ ] **Step 2: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): chat stage state machine + composer"
```

---

## Task 5: Stage B skeleton — summary card with three chips (read-only)

**Goal:** Render the chip layout (concept, sketch, source-material) in a non-edit, read-only state with the chat collapsed to a one-line breadcrumb. CTA copy/state lands in Task 6; edit interactions in Task 7; source-material panel in Task 8. This task locks the DOM shape so subsequent tasks plug in.

**Files:**
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Replace the placeholder `renderSummary` with the real layout**

```javascript
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
      if (submitBtn.disabled) return;
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
```

- [ ] **Step 2: Manually drive the state machine in DevTools**

Run: `python -m http.server 8000` (or the existing dev server) and open the modal. Type a concept name, then a substantive 12-word sketch. Confirm the summary appears with the three chips, the chat breadcrumb shows the concept name, the build CTA is enabled and reads `Build from my starting map`. Type a thin sketch (`idk`) and confirm the fallback turn appears, then exits to a summary where the build CTA is disabled and the sketch chip shows the strategy-framed footer copy.

(This is exploratory — the visual smoke is logged formally in Task 12.)

- [ ] **Step 3: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): summary card layout (read-only chips)"
```

---

## Task 6: CTA truth table + state-dependent copy + sketch-blocked footer

**Goal:** Lock the CTA + footer to the spec §3.2 truth table. Already partly done in Task 5; this task wires re-renders so the CTA + footer track state mutations and adds the `concept_create.build_blocked` telemetry on disabled-state submit attempts.

**Files:**
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Add a `rerenderSummary()` shorthand and use it everywhere chip state mutates**

This is mostly a no-op until Tasks 7-8 add the chip edit + source-attach paths, but defining it here keeps later tasks tight.

```javascript
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
```

- [ ] **Step 2: Wire `handleDisabledClickAttempt` into the submit binding**

In `renderSummary`, replace the current submit binding with:

```javascript
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
```

- [ ] **Step 3: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): CTA truth table + blocked-build telemetry"
```

---

## Task 7: Chip edit interactions (concept + sketch)

**Goal:** Click `edit` on the concept chip → swap the value for an `<input>`; click `edit` on the sketch chip → swap for a `<textarea>`. Save on blur, on `Enter` (concept only), or on `Cmd/Ctrl+Enter` (sketch). Cancel via `Escape` reverts to the prior value. Emit `concept_create.summary.edited` with `{chip}` per spec §5.4.

**Files:**
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Add edit-mode renderers for the concept and sketch chips**

```javascript
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
```

- [ ] **Step 2: Call `attachChipEditHandlers()` at the end of `renderSummary`**

```javascript
    // last line of renderSummary, after the existing wiring:
    attachChipEditHandlers();
```

- [ ] **Step 3: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): inline chip edit for concept + sketch"
```

---

## Task 8: Source-material chip + source panel

**Goal:** Click `Add source` on the source chip → expand an inline panel with `Text | URL | File` tabs (reusing the existing redesigned `.creation-source-tabs` styles + `.overlay-tab` + `.overlay-textarea` + `.overlay-url-input` + `.overlay-dropzone`). On attach, collapse the panel and show the descriptor. Emit `concept_create.source.added` with `{type}`. Click `replace` to re-open.

This task **does not** add new CSS for the panel itself — it reuses the existing tab/textarea/dropzone classes already in `components.css` (which the 2026-05-01 polish redesigned). The chip wrapper styles are added in Task 11.

**Files:**
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Add the source-panel renderer + attach logic**

```javascript
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
    const urlFeedback = valueEl.querySelector(".overlay-url-feedback");
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
        refreshAttachEnabled();
      });
    });

    textarea.addEventListener("input", refreshAttachEnabled);
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

  // Hook into renderSummary's chip wiring.
  function attachSourceChipHandlers() {
    const addBtn = container.querySelector('[data-action="add-source"]');
    const replaceBtn = container.querySelector('[data-action="replace-source"]');
    if (addBtn) addBtn.addEventListener("click", () => beginEditSource());
    if (replaceBtn) replaceBtn.addEventListener("click", () => beginEditSource());
  }
```

- [ ] **Step 2: Call `attachSourceChipHandlers()` at the end of `renderSummary`**

```javascript
    // alongside attachChipEditHandlers():
    attachSourceChipHandlers();
```

- [ ] **Step 3: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/js/concept-create.js
git commit -m "feat(ui): source-material chip with inline tabs panel"
```

---

## Task 9: Submit pipeline → POST `/api/extract` with new payload + 422 handling

**Goal:** When the build CTA fires, post `{name, starting_sketch, source}` to `/api/extract`, surface the response's `provisional_map` (or `knowledge_map` for source path) to the caller, and render the server's `message` field in the appropriate chip footer when 422s come back. Add the new `submitConceptCreate` export to `ai_service.js` and call it from `concept-create.js`'s `doSubmit`. URL-source submits go through `/api/extract-url` first to fetch the text, then through `/api/extract` with `type: "text"` (mirrors today's behavior so the new code path doesn't accidentally regress URL handling).

**Files:**
- Modify: `public/js/ai_service.js`
- Modify: `public/js/concept-create.js`

- [ ] **Step 1: Extend `ai_service.js` with `submitConceptCreate`**

```javascript
// public/js/ai_service.js (full file after edit)

export async function generateKnowledgeMap(rawText, onProgress) {
  if (onProgress) onProgress("Drafting map...");
  const apiKey = localStorage.getItem("gemini_key") || undefined;
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: rawText, api_key: apiKey }),
  });
  if (!response.ok) {
    const err = await response.text().catch(() => "");
    throw new Error(`Server error ${response.status}: ${err}`);
  }
  const data = await response.json();
  return data.knowledge_map;
}

/**
 * Conversational concept-create submit. Posts the spec §5.3 payload shape
 * and returns the parsed `provisional_map` (no source) or `knowledge_map`
 * (source attached). On 422, throws an Error with `.status` and `.body`
 * (the parsed `{error, message}` payload) so the caller can render the
 * message inline.
 *
 * @param {{ name: string, startingSketch: string,
 *           source: null | { type: 'text'|'url'|'file', text?: string, url?: string, filename?: string },
 *           apiKey?: string }} args
 * @returns {Promise<{ provisional_map?: object, knowledge_map?: object }>}
 */
export async function submitConceptCreate({ name, startingSketch, source, apiKey }) {
  const body = {
    name,
    starting_sketch: startingSketch,
    source,
    api_key: apiKey,
  };
  const response = await fetch("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (response.status === 422) {
    const payload = await response.json().catch(() => ({}));
    const detail = payload.detail || payload || {};
    const err = new Error(detail.message || "Submission rejected.");
    err.status = 422;
    err.body = detail;
    throw err;
  }
  if (!response.ok) {
    const txt = await response.text().catch(() => "");
    const err = new Error(`Server error ${response.status}: ${txt}`);
    err.status = response.status;
    throw err;
  }
  return response.json();
}
```

- [ ] **Step 2: Wire `doSubmit` in `concept-create.js`**

```javascript
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
          // Keep the original URL on the client for telemetry / display only.
          // Backend payload uses type: "text" so the dispatcher takes the
          // existing extract_knowledge_map path on this submit.
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
      const apiKey = (typeof localStorage !== "undefined" && localStorage.getItem("gemini_key")) || undefined;
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
      showSubmitError("submit", (err && err.message) || "Couldn't submit. Try again.");
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
      // The footer slot was either already rendered (blocked state) or not.
      // If not present, append it so the message lands beneath the sketch chip.
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
    // Generic fallback: prepend a banner above the footer.
    const summary = container.querySelector(".creation-summary");
    if (!summary) return;
    summary.insertAdjacentHTML(
      "beforeend",
      `<p class="creation-chip-footer">${escHtml(message)}</p>`
    );
  }
```

- [ ] **Step 3: Module-parse smoke**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/js/ai_service.js public/js/concept-create.js
git commit -m "feat(ui): submit pipeline + 422 handling for concept-create"
```

---

## Task 10: Replace `buildContentInputUI`'s `showNameField` branch in `app.js`

**Goal:** Have `startAddConcept` call the new `buildConversationalCreateUI` instead of `buildContentInputUI({ showNameField: true })`. Delete the dead form template, the placeholder rotators, and the form-only event handlers from `buildContentInputUI`. The non-`showNameField` branch (the inline overlay extract path) stays intact.

**Files:**
- Modify: `public/js/app.js`

- [ ] **Step 1: In `startAddConcept` (currently around line 1219), replace the `buildContentInputUI({ showNameField: true, ... })` call with `buildConversationalCreateUI`**

The existing call site needs the success-path branching adjusted because the response shape changes. Replace the relevant section:

```javascript
    // public/js/app.js — inside startAddConcept, after the guest-mode early return:
    const { buildConversationalCreateUI } = await import("./concept-create.js");
    buildConversationalCreateUI(dialog.shellContent, {
      onCancel: () => closeCreationDialog(),
      onSubmit: async ({ name, startingSketch, source, provisionalMap }) => {
        const concepts = loadConcepts();
        if (concepts.length >= 4) { renderAddTrigger(); return; }
        closeCreationDialog();

        const id = generateId();
        const extractStartedAt = new Date().toISOString();
        const extractStartedPerf = performance.now();

        // The provisional_map is already drafted by /api/extract before
        // onSubmit fires. We still render the extract-overlay for the brief
        // moment between dialog close and graph mount so the transition is
        // not a jump cut. (TODO: refactor the overlay to mount before submit
        // for true progress feedback once this lands.)

        // Reuse today's provisional-map handling code path. The map is one
        // of {provisional_map, knowledge_map} from the response; we pass
        // whichever is set and the existing render code consumes it the same.
        const knowledgeMap = provisionalMap;
        if (!isValidKnowledgeMap(knowledgeMap)) {
          // Fall through to the existing error banner code.
          mountCreationDialog();
          dialog.bannerSlot.appendChild(
            buildErrorBanner(sanitizeExtractError(new Error("invalid map")))
          );
          return;
        }

        // Persist the new concept the same way the form path did.
        // (The existing post-submit code is untouched — we just hand it the
        // already-extracted map. The function below mirrors today's
        // pattern around saveConcept + selectConcept + showMapView.)
        finishConceptCreate({
          id,
          name,
          knowledgeMap,
          startedAt: extractStartedAt,
          startedPerf: extractStartedPerf,
          startingSketch,
          source,
        });
      },
    });
```

The existing `startAddConcept` body has substantial overlay/animation logic (the `extract-overlay`, particle grid, progress bar, etc.) that runs while `extract_knowledge_map` is fetching. Two options exist:

**Option A (recommended for v1):** Move the overlay into `concept-create.js`'s `doSubmit` so it shows during the network call. Cleanest semantics; the dialog already closes before the network call resolves.

**Option B (lighter touch):** Leave the overlay code where it is and call it from `onSubmit` with the already-resolved map. Faster to implement; the overlay flickers briefly but the UX is acceptable for v1.

**Choose Option B for v1.** Refactor to Option A is logged as a Plan B follow-up. Implementation:

```javascript
      onSubmit: async ({ name, startingSketch, source, provisionalMap }) => {
        // Validate before destroying the dialog (so we can recover inline).
        if (!isValidKnowledgeMap(provisionalMap)) {
          // Re-mount; show the error banner; let the user retry.
          const dialog2 = mountCreationDialog();
          dialog2.bannerSlot.appendChild(
            buildErrorBanner(sanitizeExtractError(new Error("invalid map")))
          );
          buildConversationalCreateUI(dialog2.shellContent, { /* same handlers */ });
          return;
        }

        const concepts = loadConcepts();
        if (concepts.length >= 4) { renderAddTrigger(); return; }
        closeCreationDialog();

        // Hand the validated map to the existing post-submit flow. The
        // existing code path mounts the extract-overlay → renders the graph
        // → persists via saveConcept. For v1 we wrap that path into a
        // helper, finishConceptCreate, that takes the map directly and skips
        // the network call.
        finishConceptCreateWithMap({
          id: generateId(),
          name,
          knowledgeMap: provisionalMap,
          startedAtIso: new Date().toISOString(),
          startedPerf: performance.now(),
          startingSketch,
          source,
        });
      },
```

`finishConceptCreateWithMap` is a new helper extracted from the existing `startAddConcept` body that runs everything after the network call resolves. Lift the overlay-mount → graph-render → persistence code into it. Specific instructions:

- Cut the body of `startAddConcept` from `closeCreationDialog();` (line ~1229) through the end of the `onSubmit` handler — the `extractOverlay` creation, particle grid, progress bar, the `try { const knowledgeMap = await generateKnowledgeMap(...) }` block, the `saveConcept(...)` call, the `selectConcept(...)` and `showMapView(...)` calls, and the cleanup teardown.
- Wrap that body in `function finishConceptCreateWithMap({ id, name, knowledgeMap, startedAtIso, startedPerf, startingSketch, source }) { ... }`.
- Replace the network call (`generateKnowledgeMap(text)`) with a no-op since the map is already passed in. Keep the overlay+progress UI for visual continuity (it shows briefly between dialog close and graph mount; the existing code's animation cycle is short enough).
- The existing `saveConcept` call should still receive the `name`, `knowledgeMap`, and any threshold context it expects. If today's `saveConcept` reads from a `thresholdContext` field, pass `startingSketch` (the new equivalent) under that name to preserve the contract.

- [ ] **Step 2: Delete the `showNameField === true` branch of `buildContentInputUI`**

Inside `buildContentInputUI` (line 684), the function has two paths controlled by `showNameField`. Remove the form-only HTML template (the `${showNameField ? '<div class="creation-intro …">…</div>' : ''}` branch and onward through `creation-source-meta`, `creation-validation`, the threshold/fuzzy panels, etc.), the form-only event handlers (`creation-name-input` listeners, `creation-threshold-input` listeners, fuzzy toggle handler, the `PLACEHOLDERS` and `NAME_PLACEHOLDERS` rotators with their `phTimer` / `namePhTimer`), and the form-only state in `doSubmit` (the `thresholdContext` construction, the `name` / `fuzzyText` references). The `showNameField === false` branch (which is the inline overlay extract path) and its non-form behavior remain untouched.

After the cut, the function should accept either:
- `showNameField: false` (today's other call site, unchanged), or
- (no other code path remains; the function's `showNameField === true` branch is gone).

If `showNameField` is now always false, simplify by removing the parameter and the conditional. Search the codebase for other callers that pass `showNameField: true` and update them; if none remain, drop the parameter from `buildContentInputUI`.

- [ ] **Step 3: Run module-syntax test**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS — `app.js` parses cleanly.

- [ ] **Step 4: Manually load the dev server and walk the flow**

```bash
cd .worktrees/concept-create-frontend
.venv/bin/uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`, click `new tink`, walk through:
1. Type a concept name in turn 1.
2. Type a substantive sketch in turn 2.
3. Confirm summary card appears with three chips.
4. Confirm CTA reads `Build from my starting map` and is enabled.
5. Click build; confirm the modal closes, the extract overlay shows briefly, the graph renders.

Repeat with a thin sketch (`idk`) — confirm fallback chat appears, then summary appears with CTA disabled and the strategy-framed footer beneath the sketch chip.

Repeat with a substantive sketch + `Add source` → paste text → `Attach`. Confirm CTA reads `Build from my map and source`, click build, confirm graph renders.

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js
git commit -m "feat(ui): replace form modal with conversational create flow"
```

---

## Task 11: CSS — delete dead form classes, add chat + summary classes

**Goal:** Update `public/css/components.css`. Remove the form-only classes; add the chat surface, summary card, and chip styles. Respect cream/ink/violet palette, single violet accent at rest (the build CTA), violet-tinted shadows, and `prefers-reduced-motion`. No emoji, no exclamation marks, no gradient text, no glass-morphism, no left-stripe borders.

**Files:**
- Modify: `public/css/components.css`

- [ ] **Step 1: Delete the form-only classes**

Remove every rule whose selector starts with one of:
- `.creation-intro`, `.creation-intro-compact`, `.creation-intro-row`, `.creation-intro-title`, `.creation-intro-copy`
- `.creation-name-input` (and its `:focus`, `::placeholder` rules)
- `.creation-threshold`, `.creation-threshold-head`, `.creation-threshold-copy`, `.creation-threshold-input` (incl. `:focus`, `::placeholder`)
- `.creation-fuzzy-toggle` (incl. `:hover`, `:focus-visible`), `.creation-fuzzy-row`, `.creation-fuzzy-hint` (incl. `[hidden]`), `.creation-fuzzy-panel` (incl. `[hidden]`), `.creation-fuzzy-input` (incl. `:focus`, `::placeholder`)
- `.creation-source-meta`, `.creation-source-copy`, `.creation-source-header`
- `.creation-validation`
- `.creation-field`
- `.creation-section-label` (re-introduce a replacement under the new names below if needed for the source panel — Task 8 reuses the existing `.overlay-tab` system, which doesn't depend on `.creation-section-label`).
- `.creation-capacity-pill` (only used in the form path; Plan B removes it).

Also remove the `.creation-intro-row` block inside the `@media (max-width: ...)` responsive section if present.

Keep:
- `.creation-dialog`, `.creation-dialog-scrim`, `.creation-dialog-shell`, `.creation-dialog-header`, `.creation-dialog-kicker`, `.creation-dialog-close`, `.creation-dialog-title`, `.creation-dialog-meta`, `.creation-dialog-banner-slot`, `.creation-dialog-content` — modal shell.
- `.creation-source-tabs .overlay-tab` (and `.active`, `:hover`) — redesigned 2026-05-01 polish, reused by the source panel.
- `.creation-cancel`, `.creation-submit` (and disabled / hover) — button styles.
- `.creation-footer` — flex row at the bottom of any creation surface.
- `.creation-banner`, `.creation-banner--guest`, `.creation-banner--error`, `.creation-guest-actions`, `.btn-browse-starters`, `.auth-link` — guest mode + error banners.
- `.paste-actions`, `.paste-clipboard-btn` — used inside the source panel.
- `.creation-dialog-content .overlay-textarea` — sizing rule for textareas inside the modal.

- [ ] **Step 2: Append the new chat + summary classes**

Append these rules at the bottom of the existing `creation-*` section in `components.css` (around the area where the deleted classes used to live, after `.creation-footer`):

```css
/* ─────────────────────────────────────────────────────────────
 * Conversational concept creation (Plan B, 2026-05-04).
 * Two surfaces: chat (Stage A) and summary card (Stage B).
 * One violet accent at rest = the build CTA. Eyebrows are
 * lavender (--accent-secondary), which is secondary and does
 * not double-count.
 * ─────────────────────────────────────────────────────────── */

.creation-chat {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 0 0;
}
.creation-chat-question {
  margin: 0;
  font-family: var(--font-display, var(--font-body));
  font-size: 16px;
  line-height: 1.45;
  font-weight: 500;
  color: var(--text);
  letter-spacing: -0.005em;
}
.creation-chat-composer {
  width: 100%;
  min-height: 88px;
  resize: vertical;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-card);
  color: var(--text);
  padding: 11px 12px;
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.5;
  outline: none;
  box-sizing: border-box;
  transition:
    border-color var(--duration-micro, 140ms) var(--ease-standard, ease),
    box-shadow var(--duration-micro, 140ms) var(--ease-standard, ease);
}
.creation-chat-composer:focus {
  border-color: var(--primary);
  box-shadow: var(--accent-ring);
}
.creation-chat-breadcrumb {
  margin: 0 0 4px;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-sub);
  font-style: normal;
}

.creation-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 4px 0 0;
}
.creation-section-eyebrow {
  display: inline-block;
  margin: 4px 0 -4px;
  font-family: var(--font-body);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--accent-secondary, var(--text-sub));
  text-transform: uppercase;
}

.creation-chip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border: 1px solid var(--border-subtle, var(--border));
  border-radius: 12px;
  background: var(--surface-card);
  /* Inset 1px lit-edge highlight — the cream-paper feel. */
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.78);
  transition:
    border-color var(--duration-micro, 140ms) var(--ease-standard, ease),
    background-color var(--theme-transition-ms) var(--theme-transition-ease),
    color var(--theme-transition-ms) var(--theme-transition-ease);
}
.creation-chip-empty {
  background: transparent;
  border-style: dashed;
  box-shadow: none;
}
.creation-chip-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.creation-chip-label {
  font-family: var(--font-body);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: var(--text-sub);
  text-transform: uppercase;
}
.creation-chip-action {
  background: transparent;
  border: 0;
  padding: 0;
  font: inherit;
  font-size: 11.5px;
  font-weight: 500;
  color: var(--text-sub);
  cursor: pointer;
  text-decoration: none;
  transition: color var(--duration-micro, 140ms) var(--ease-standard, ease);
}
.creation-chip-action:hover {
  color: var(--primary);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.creation-chip-action:focus-visible {
  outline: none;
  box-shadow: var(--accent-ring);
  border-radius: 4px;
}
.creation-chip-value {
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--text);
  white-space: pre-wrap;
  word-break: break-word;
}
.creation-chip-empty-text {
  font-style: italic;
  color: var(--text-sub);
}
.creation-chip-input,
.creation-chip-textarea {
  width: 100%;
  background: var(--surface-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
  font-family: inherit;
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--text);
  outline: none;
  box-sizing: border-box;
  transition:
    border-color var(--duration-micro, 140ms) var(--ease-standard, ease),
    box-shadow var(--duration-micro, 140ms) var(--ease-standard, ease);
}
.creation-chip-textarea {
  min-height: 88px;
  resize: vertical;
}
.creation-chip-input:focus,
.creation-chip-textarea:focus {
  border-color: var(--primary);
  box-shadow: var(--accent-ring);
}
.creation-chip-footer {
  margin: 4px 0 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--text-sub);
}

/* Source-material panel inside the source chip (when expanded). Reuses the
 * existing .overlay-tabs / .overlay-panel / .overlay-textarea / .overlay-url-input
 * / .overlay-dropzone styles already in components.css; this block adds only
 * the wrapper + footer styles specific to the panel-inside-chip presentation. */
.creation-source-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.creation-source-panel-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.creation-source-panel-cancel {
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 6px 12px;
  font: inherit;
  font-size: 12px;
  color: var(--text-sub);
  cursor: pointer;
  transition:
    color var(--duration-micro, 140ms) var(--ease-standard, ease),
    border-color var(--duration-micro, 140ms) var(--ease-standard, ease);
}
.creation-source-panel-cancel:hover {
  color: var(--text);
  border-color: var(--primary);
}
.creation-source-panel-attach {
  background: var(--primary);
  color: var(--accent-on-primary, white);
  border: 0;
  border-radius: 8px;
  padding: 6px 14px;
  font: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--shadow-inline);
  transition: opacity var(--duration-micro, 140ms) var(--ease-standard, ease);
}
.creation-source-panel-attach:disabled {
  background: var(--locked, var(--border));
  cursor: not-allowed;
  box-shadow: none;
}
.creation-source-panel-attach:not(:disabled):hover {
  opacity: 0.88;
}

@media (prefers-reduced-motion: reduce) {
  .creation-chat-composer,
  .creation-chip,
  .creation-chip-action,
  .creation-chip-input,
  .creation-chip-textarea,
  .creation-source-panel-cancel,
  .creation-source-panel-attach {
    transition: none;
  }
}
```

If `--accent-secondary`, `--accent-ring`, `--border-subtle`, `--shadow-inline`, `--accent-on-primary`, or `--ease-standard` are not defined in the project's token files, drop them and use the closest existing token (most are referenced in `colors_and_type.css`; verify before removing). Do **not** invent new hex values.

- [ ] **Step 2 (verification): grep for forbidden patterns**

Run from the worktree root:

```bash
grep -nE 'background-clip:\s*text|backdrop-filter:\s*blur\([^)]*\)\s*[^;]*\s+blur\(|border-left:\s*[2-9]px|border-right:\s*[2-9]px' public/css/components.css
```

Expected: no matches inside the new chat/summary classes (some matches in unrelated parts of the file are fine — only the new rules need to be clean).

Also grep for emoji / exclamation marks in the new copy strings:

```bash
grep -nE '[!]|🎉|✨|💡|🔥|⚡' public/js/concept-create.js
```

Expected: no matches (the only `!` in the file should be JS negation operators in identifiers like `!state.source` — those are fine).

- [ ] **Step 3: Module-parse smoke (no JS changes but quick to run)**

Run: `.venv/bin/pytest tests/test_frontend_syntax.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add public/css/components.css
git commit -m "feat(ui): chat + summary chip styles; remove dead form CSS"
```

---

## Task 12: Acceptance verification + visual smoke

**Goal:** Walk all 12 acceptance criteria from the handoff. Capture screenshots. Run the full local test suite. Run `bash scripts/qa-smoke.sh` against the local server.

**Files:**
- (No code changes; verification + PR description.)

- [ ] **Step 1: Local end-to-end smoke (no source)**

Boot the server (`uvicorn main:app --reload --port 8000`), open `http://localhost:8000`, click `new tink`. Walk:

1. Turn 1 question: `What do you want to understand?` — type `Photosynthesis`, submit.
2. Turn 2 question: `Sketch what you think it does — rough is fine. What parts come to mind?` — type a substantive sketch like `Plants take in light through leaves and convert CO2 and water into sugar and oxygen, somehow stored in chloroplasts.`, submit.
3. Summary card appears: chips show concept and sketch; source chip is empty with the "None added — build will start from your model only" copy; CTA reads `Build from my starting map` and is enabled.
4. Click build. Confirm the extract overlay shows briefly and the provisional graph renders.

- [ ] **Step 2: Local end-to-end smoke (with source attached)**

Repeat the flow; on the summary card, click `Add source`, paste a passage of source text, click `Attach`. Confirm:
- Source chip transitions from `None added…` to `<N> chars pasted` with a `replace` action.
- CTA copy updates to `Build from my map and source`.
- Click build; confirm graph renders via the source-attached path.

- [ ] **Step 3: Local end-to-end smoke (thin sketch + no source)**

Repeat the flow with a thin sketch (e.g., `idk`). Confirm:
- The fallback chat turn appears with the input-output framing copy.
- After the fallback reply, the summary card appears.
- CTA is **disabled** (visually muted, `disabled` attribute set).
- The sketch chip shows the strategy-framed footer copy verbatim: `A few words about how you think it works will give socratink something to draft from. Or attach source material — either path opens the build.`
- Edit the sketch chip to a substantive value: confirm CTA re-enables.
- Re-edit to thin again, then click `Add source` and attach text: confirm CTA re-enables and copy reads `Build from source`.

- [ ] **Step 4: 422 round-trip smoke (server-side defense in depth)**

In DevTools console, force a thin-sketch + no-source submit by manipulating the chip state:

```javascript
// quick manual repro in the console:
fetch("/api/extract", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ name: "Test", starting_sketch: "idk", source: null }),
}).then(r => r.json()).then(console.log);
```

Expected: 422 with `{detail: {error: "thin_sketch_no_source", message: "..."}}`.

In the actual UI, the client-side check disables the CTA before this can happen — the test is to confirm the server-side gate is the safety net.

- [ ] **Step 5: Hard-stop verification**

Confirm there is no UI affordance to:
- Trigger a third AI chat turn after turn 2 (or after the fallback if it fired).
- Re-open the chat once the summary card appears.
- Edit the chat breadcrumb (it's a `<p>`, not a button).

- [ ] **Step 6: Single-violet-at-rest verification**

On the summary card with all chips populated, confirm exactly one element uses the hard `--primary` fill at rest: the build CTA. The eyebrow (`STARTING MAP`) uses `--accent-secondary` (lavender), which is secondary by definition. Chip `edit` actions are violet on `:hover` but `--text-sub` at rest.

- [ ] **Step 7: Reduced-motion check**

In DevTools → Rendering → Emulate CSS media feature `prefers-reduced-motion: reduce`. Walk the flow again: confirm chip swaps, edit-mode entries, and CTA re-enables happen instantly with no transitions.

- [ ] **Step 8: Run the full Python test suite**

```bash
.venv/bin/pytest tests/ --ignore=tests/e2e -q
```

Expected: all green. The new parity test, the existing module-syntax test, the existing extract-route tests, and the existing telemetry tests all pass.

- [ ] **Step 9: Run `bash scripts/qa-smoke.sh` against local**

```bash
bash scripts/qa-smoke.sh local
```

Expected: PASS. (If pre-existing playwright tests rely on the old form selectors, those tests are already updated by the handoff's premise that the form is replaced — confirm by inspecting `tests/e2e/test_smoke.py` and updating selectors if needed; that update is a permitted scope-extension within Plan B.)

- [ ] **Step 10: Visual smoke screenshots**

Capture, for the PR description:
- Chat turn 1 (question + composer, light mode)
- Chat turn 2 (question + composer, light mode)
- Summary card with no source attached (light mode)
- Summary card with source attached (light mode)
- Summary card with thin sketch + no source (CTA disabled with footer copy, light mode)
- Same five in dark mode

Save under `docs/superpowers/handoff-evidence/2026-05-04-concept-create-frontend/` (create the directory). Reference the screenshots in the PR body.

- [ ] **Step 11: Final grep sweep — banned patterns**

Run from worktree root:

```bash
grep -rnE '[!]\)|exclamation|emoji|🎉|✨|💡|🔥|⚡|background-clip:\s*text' public/js/concept-create.js public/css/components.css | grep -vE '!disabled|!== ?null|!==|!== undefined|!== ""|!=='
```

Expected: no matches. (`!==` style operators are filtered out by the second grep; only literal exclamation marks in copy or true emoji should remain — none are expected.)

Run a separate sweep for accidental affirmation phrases:

```bash
grep -nE 'Great start|Got it|Fair enough|interesting!|Awesome|Nice work' public/js/concept-create.js
```

Expected: no matches.

- [ ] **Step 12: Commit the screenshot evidence + final touch-up if needed**

```bash
git add docs/superpowers/handoff-evidence/2026-05-04-concept-create-frontend/
git commit -m "docs(handoff): visual smoke evidence for concept-create frontend"
```

- [ ] **Step 13: Open the PR**

```bash
gh pr create --title "feat(ui): conversational concept creation — chat → summary card flow" --body "$(cat <<'EOF'
## Summary
- Replaces the form-based concept-creation modal with a 2-turn (+ analogical fallback) chat → summary-card flow per spec docs/superpowers/specs/2026-05-02-conversational-concept-creation-design.md
- Wires to the Plan A backend (already on dev at 086e617): POST /api/extract dispatches between source-less generate_provisional_map_from_sketch and existing extract_knowledge_map
- Ports models/sketch_validation.is_substantive_sketch to JS with a fixture-locked parity test (28 entries incl. unicode); divergence is a release-blocker

## Test plan
- [x] .venv/bin/pytest tests/ --ignore=tests/e2e -q passes
- [x] bash scripts/qa-smoke.sh local passes
- [x] Visual smoke (light + dark, all 5 states) — see screenshots under docs/superpowers/handoff-evidence/2026-05-04-concept-create-frontend/
- [x] Hard-stop verification: no UI path to a 3rd AI turn or to reopen the chat
- [x] Single-violet-at-rest: the build CTA is the only --primary element at rest
- [x] Server-side 422 round-trip: thin sketch + no source via direct POST returns thin_sketch_no_source

## Follow-ups (Plan C / future)
- Reconcile DESIGN.md §3 Screen 1 to reflect conversational threshold capture
- Wire chat turns to a real /api/threshold-chat-turn endpoint (currently hardcoded turn-2 + fallback copy that mirrors app_prompts/threshold-chat-system-v1.txt verbatim)
- Concept-derived analogy generation (currently a generic input-output fallback)
- Frontend telemetry network post (currently console + Bus only)
EOF
)"
```

---

## Out of scope — explicitly deferred to Plan C / follow-ups

These show up here so the executor doesn't try to land them in this branch:

1. **DESIGN.md §3 Screen 1 update** describing the conversational threshold capture. Plan C reconciles the binding doc; this branch ships the implementation.
2. **`/api/threshold-chat-turn` endpoint.** Turn 2 + fallback copy are hardcoded for v1. Their literal text mirrors `app_prompts/threshold-chat-system-v1.txt` verbatim; voice drift cannot sneak in even with the hardcode in place.
3. **Concept-derived analogy generation.** The v1 fallback is the input-output frame, generic-but-honest. Real concept-derived analogies require the new endpoint above.
4. **Frontend telemetry network post.** Events flow through `Bus.emit('telemetry', …)` and `console.info`. Adding a `/api/telemetry` post is one line in `telemetry.js` once the backend endpoint exists.
5. **`finishConceptCreate` overlay refactor (Option A).** The extract-overlay flicker between dialog close and graph mount is acceptable for v1. Option A in Task 10 moves the overlay into `concept-create.js`'s `doSubmit` so it covers the network call cleanly.
6. **Standards-alignment metadata on tiles**, **Prerequisite-aware Interleaving Bridge**, **LC Evaluator gating** — already declared out-of-scope by spec §7. Listed here for completeness.

---

## Risk register (operational reminders for the executor)

| Risk | Mitigation in this plan |
|---|---|
| JS substantiveness heuristic diverges from Python | Task 1 fixture-locked parity test, runs in CI; release-blocker if any entry mismatches. |
| Voice drift in hardcoded chat copy | Turn-2 + fallback text are literal mirrors of `app_prompts/threshold-chat-system-v1.txt`'s example shape. Acceptance criterion #10 (handoff) reviews against the prompt. |
| Edit-chip Escape closes the modal mid-edit | `e.stopPropagation()` in chip edit Escape handlers (Task 7), so the modal-level Escape handler does not fire. |
| Server returns `provisional_map` (new path) but frontend expects `knowledge_map` | Task 9's `submitConceptCreate` consumer normalises with <code>data.provisional_map &#124;&#124; data.knowledge_map</code>. |
| URL source attached, but `/api/extract` rejects URL types | Task 9 hops through `/api/extract-url` first to materialise text, then submits as `type: "text"`; mirrors today's behavior. |
| Telemetry events fire at the wrong shape and confuse the dashboards | Each event's `extra={...}` shape is fixed in spec §5.4; tasks plant events at the named call sites with the named fields. |
| CSS deletion accidentally removes a class still in use elsewhere | Task 11 enumerates the keep-list explicitly; before deleting any class, the executor must `grep -n` for it across `public/` to confirm no other surface uses it. |
| Source-panel breaks file uploads on Safari (FileReader) | Plan B keeps the existing `FileReader.readAsText` pattern — same as the form-based flow used; no new platform surface. |
| Modal focus-trap drops focus when the source panel mounts | `creation-dialog-shell`'s `trapFocusHandler` walks the live `focusables` list each Tab keypress, so newly-mounted inputs join the cycle automatically. |
