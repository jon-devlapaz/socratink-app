# Drill Chamber Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the ironclad drill chamber design (validated in `public/_lab/drill-chamber-iterations.html?variant=ironclad`) into production. The drill becomes a separate focused view ("the chamber") that takes over the screen when the learner taps "Try from memory" on a concept page. The current embedded drill UI inside the right `graph-detail` panel is replaced.

**Architecture:**
- Add a new top-level view `#drill-chamber-view` as a sibling of `#map-content` / `#graph-content` / `#ignition-view` inside `<main id="app-main">`.
- New JS module `public/js/drill-chamber.js` owns the chamber's mount/unmount/render — it does NOT duplicate `/api/drill` networking; it reuses the existing `requestDrillTurn` / `appendBubble` machinery, which gets refactored to be DOM-agnostic via injected DOM-handle parameters.
- New CSS file `public/css/drill-chamber.css` ports the ironclad lab styles (uses `--violet-600`, `--lavender-500`, `--text-strong`, etc. — no hardcoded hex except where the lab spec requires them, e.g. obsidian backdrop).
- The existing `<div class="drill-ui drill-ui-embedded" id="drill-ui">` block inside `graph-detail` is removed. The `cancelDrill` flow restores the concept page (map view).
- Backend `/api/drill` is unchanged.

**Tech Stack:**
- Vanilla JS modules (matches `public/js/app.js` style)
- CSS via cascade — link in `public/index.html`
- Playwright for the browser smoke
- Existing `chat-message` rendering helpers in `app.js` get parameterized for the new history container

---

## File Structure

**Create:**
- `public/css/drill-chamber.css` — chamber-specific styles (ported from `public/_lab/drill-chamber-iterations.html?variant=ironclad`)
- `public/js/drill-chamber.js` — chamber view module (mount, unmount, render question, append turn, focus composer, exit-to-map)
- `tests/e2e/test_drill_chamber.py` — Playwright e2e covering: enter chamber from concept, send turn, receive AI response, exit to map

**Modify:**
- `public/index.html` — add `<link rel="stylesheet" href="css/drill-chamber.css">`, add `<div id="drill-chamber-view" hidden>` markup, REMOVE the `<div class="drill-ui drill-ui-embedded">` block (lines ~411–421), bump `?v=` on `index.html`-imported assets touched
- `public/js/app.js` — refactor `appendBubble` and `requestDrillTurn` to accept DOM-handle params (or read them from a single source-of-truth getter); rewrite `startDrill` to call `DrillChamber.show(activeConcept, nodeContext)`; rewrite `cancelDrill` to call `DrillChamber.hide()` and restore `showMapView`; delete the embedded `#chat-input` / `#chat-history` references that pointed at the removed markup

**Untouched:**
- `public/js/graph-view.js` (cytoscape constellation) — chamber doesn't render the map
- `auth/`, `main.py`, `ai_service.py`, `/api/drill` route — backend unchanged
- `public/_lab/*` — the lab page stays as the design-of-record reference

---

## Acceptance Criteria (these must be true before merge)

1. Tapping the active node's primary CTA on the concept page opens the chamber full-screen; the map+detail two-pane is no longer visible
2. The chamber displays the AI's first prompt for the active node, a textarea, "Send turn" ghost pill, and a `← Return to map · {concept name} · {entry name}` breadcrumb
3. Sending a turn (Enter or "Send turn") POSTs to `/api/drill`, receives the response, accumulates the prior AI question + learner reply into the history widget at top, swaps the next AI question into the active block, clears the textarea
4. Tapping `← Return to map` hides the chamber and restores the concept page exactly as it was
5. The doctrine survives the port: no praise copy, no scoring, no "AI is typing" indicator, the post-attempt artifact does NOT regress to generic content
6. Reduced motion clients get instant transitions
7. Coverage gate (`./scripts/check-coverage.sh`) exits 0
8. The Playwright smoke (`scripts/qa-smoke.sh local`) passes

---

## Task 1: Worktree setup + baseline

**Files:**
- (no edits in this task)

- [ ] **Step 1: Verify .worktrees/ is gitignored**

```bash
git check-ignore -q .worktrees && echo "ok" || echo "MISSING"
```

Expected: `ok`. If MISSING, add `.worktrees/` to `.gitignore` and commit before proceeding.

- [ ] **Step 2: Create worktree off dev**

```bash
git worktree add .worktrees/drill-chamber-port -b feat/drill-chamber-port dev
cd .worktrees/drill-chamber-port
```

- [ ] **Step 3: Verify clean baseline tests**

```bash
pytest tests/ -q --ignore=tests/e2e -x | tail -10
```

Expected: 0 failed (e2e excluded — they require a running dev server which the worktree won't have).

- [ ] **Step 4: Confirm dev server convention**

Read `AGENTS.md`'s "Common development commands" section and note: dev server runs from main checkout via `bash scripts/dev.sh`, NOT from the worktree. Do NOT start a second dev server in the worktree — instead, the smoke step at the end runs against the main checkout's dev server after porting changes there.

---

## Task 2: Static stub of the chamber view (markup + CSS file links, hidden by default)

**Files:**
- Create: `public/css/drill-chamber.css`
- Modify: `public/index.html` (add link + view container)

- [ ] **Step 1: Create empty CSS file with header**

Create `public/css/drill-chamber.css`:

```css
/* drill-chamber.css
   Production styles for the ironclad drill chamber view.
   Design-of-record: public/_lab/drill-chamber-iterations.html?variant=ironclad
   Reads from public/css/variables.css for tokens. */

#drill-chamber-view[hidden] { display: none; }
```

- [ ] **Step 2: Link CSS into index.html**

In `public/index.html`, find the existing stylesheet links near the top of `<head>` (look for `<link rel="stylesheet" href="css/components.css">` and similar). Append:

```html
<link rel="stylesheet" href="css/drill-chamber.css?v=1">
```

Place it AFTER `components.css` so component-level resets don't clobber chamber styles.

- [ ] **Step 3: Add hidden chamber view container in index.html**

Inside `<main id="app-main">`, AFTER the closing `</section>` for the existing graph/map view (look for the section that contains `#graph-content`), add:

```html
<section id="drill-chamber-view" class="drill-chamber-view" hidden aria-label="Drill chamber">
  <div class="drill-chamber__inner">
    <nav class="drill-chamber__crumb" aria-label="Drill location">
      <a href="javascript:void(0)" id="chamber-exit" aria-label="Return to map">
        <svg class="drill-chamber__back" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
        Return to map
      </a>
      <span class="drill-chamber__sep" aria-hidden="true">·</span>
      <span id="chamber-concept-name">—</span>
      <span class="drill-chamber__sep" aria-hidden="true">·</span>
      <span class="drill-chamber__here" id="chamber-entry-name">—</span>
    </nav>

    <div class="drill-chamber__history" id="chamber-history-widget" hidden>
      <div class="drill-chamber__history-summary">
        <span class="drill-chamber__history-count" id="chamber-history-count">0</span>
        earlier turns this attempt
      </div>
      <button class="drill-chamber__history-toggle" id="chamber-history-toggle" type="button" aria-expanded="false" aria-controls="chamber-history-expanded">show</button>
      <div class="drill-chamber__history-expanded" id="chamber-history-expanded"></div>
    </div>

    <div class="drill-chamber__active" id="chamber-active">
      <p class="drill-chamber__question" id="chamber-question">—</p>
      <div class="drill-chamber__composer">
        <textarea id="chamber-composer" placeholder="Write what comes to mind. Fragments are fine." aria-label="Your reply" rows="3"></textarea>
        <div class="drill-chamber__composer-foot">
          <span class="drill-chamber__hint">a sentence is enough · cmd · return to send</span>
          <button class="drill-chamber__send" id="chamber-send" type="button">Send turn</button>
        </div>
      </div>
    </div>
  </div>
</section>
```

- [ ] **Step 4: Smoke-load the page in the dev server (manual verify)**

In the main checkout (NOT the worktree), copy these changes over before proceeding (or pause and proceed in the main checkout for browser verification). Run:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/css/drill-chamber.css
```

Expected: `200`.

- [ ] **Step 5: Commit**

```bash
git add public/css/drill-chamber.css public/index.html
git commit -m "feat(drill-chamber): scaffold hidden chamber view + CSS link"
```

---

## Task 3: Chamber CSS — port ironclad styles from the lab page

**Files:**
- Modify: `public/css/drill-chamber.css`

- [ ] **Step 1: Read the source**

Open `public/_lab/drill-chamber-iterations.html` and locate the `/* D-3 — IRONCLAD */` CSS block (search for `.v-iron`). The block runs from the comment header through the `@media (prefers-reduced-motion: reduce)` rule for `.v-iron__active`.

- [ ] **Step 2: Port the styles, replacing `.v-iron` with `.drill-chamber-view` / `.drill-chamber__*`**

Append to `public/css/drill-chamber.css`:

```css
/* ============================================================
   IRONCLAD chamber — ported from
   public/_lab/drill-chamber-iterations.html (variant=ironclad).
   Synthesized from 3 customer-feedback rounds (Maya/Jordan/Robert).
   Companion notes: public/_lab/drill-chamber-iterations.NOTES.md
   ============================================================ */

.drill-chamber-view {
  background: #07050f;
  color: rgba(247, 236, 225, 0.96);
  font-family: 'Inter', 'Manrope', -apple-system, system-ui, sans-serif;
  min-height: 100vh;
  position: relative;
  display: block;
}

.drill-chamber__inner {
  max-width: 760px;
  margin: 0 auto;
  padding: 24px 36px 100px;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 1;
}

/* Desk lamp behind the active block — single soft halo. */
.drill-chamber-view::before {
  content: "";
  position: fixed;
  top: 80px; bottom: 0;
  left: 0; right: 0;
  pointer-events: none;
  z-index: 0;
  background: radial-gradient(ellipse 45% 30% at 50% 55%, rgba(176, 156, 224, 0.07), transparent 70%);
}

/* Crumb */
.drill-chamber__crumb {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 0 36px;
  font-size: 12px;
  color: rgba(247, 236, 225, 0.48);
  opacity: 0.78;
  transition: opacity 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber-view:has(.drill-chamber__composer textarea:focus) .drill-chamber__crumb {
  opacity: 0.30;
}
.drill-chamber__crumb a {
  color: rgba(176, 156, 224, 0.78);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: color 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__crumb a:hover { color: rgba(247, 236, 225, 0.96); }
.drill-chamber__sep { color: rgba(247, 236, 225, 0.18); }
.drill-chamber__here { color: rgba(247, 236, 225, 0.92); }
.drill-chamber__back { width: 13px; height: 13px; transform: translateY(1px); }

/* History widget */
.drill-chamber__history {
  display: flex; align-items: center; justify-content: space-between;
  gap: 18px;
  padding: 12px 16px;
  background: transparent;
  border: 1px solid rgba(247, 236, 225, 0.06);
  border-radius: 10px;
  margin-bottom: 64px;
  transition: all 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__history-summary {
  font-size: 12px;
  color: rgba(247, 236, 225, 0.55);
  letter-spacing: 0.02em;
}
.drill-chamber__history-count {
  font-family: ui-monospace, monospace;
  color: rgba(176, 156, 224, 0.78);
  letter-spacing: 0.06em;
  margin-right: 8px;
}
.drill-chamber__history-toggle {
  background: transparent;
  border: 1px solid rgba(247, 236, 225, 0.10);
  border-radius: 999px;
  padding: 4px 12px;
  color: rgba(247, 236, 225, 0.55);
  font-family: ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__history-toggle:hover {
  color: rgba(247, 236, 225, 0.92);
  border-color: rgba(176, 156, 224, 0.40);
}
.drill-chamber__history-expanded {
  display: none;
  width: 100%;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px dashed rgba(247, 236, 225, 0.10);
  animation: drill-chamber-fade 320ms cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes drill-chamber-fade { from { opacity: 0; } to { opacity: 1; } }
.drill-chamber__history.is-expanded {
  flex-direction: column; align-items: stretch;
}
.drill-chamber__history.is-expanded .drill-chamber__history-expanded { display: block; }
.drill-chamber__history-turn {
  padding: 10px 0;
  font-size: 14px;
  line-height: 1.6;
}
.drill-chamber__history-turn-meta {
  font-family: ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  margin-bottom: 4px;
  color: rgba(176, 156, 224, 0.55);
}
.drill-chamber__history-turn--learner .drill-chamber__history-turn-meta {
  color: rgba(202, 196, 206, 0.55);
}
.drill-chamber__history-body { color: rgba(247, 236, 225, 0.68); }

/* Active block — anchor pillar on the left edge */
.drill-chamber__active {
  flex: 1;
  display: flex; flex-direction: column;
  justify-content: center; align-items: stretch;
  max-width: 580px;
  margin: 0 auto;
  width: 100%;
  position: relative;
  padding-left: 24px;
  transition: opacity 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__active::before {
  content: "";
  position: absolute;
  left: 0; top: 18px; bottom: 18px;
  width: 1px;
  background: linear-gradient(
    180deg,
    transparent,
    rgba(176, 156, 224, 0.42) 30%,
    rgba(176, 156, 224, 0.42) 70%,
    transparent
  );
}
.drill-chamber__question {
  font-family: 'Geom', 'Outfit', -apple-system, system-ui, sans-serif;
  font-size: 24px;
  font-weight: 500;
  letter-spacing: -0.01em;
  line-height: 1.5;
  color: rgba(247, 236, 225, 0.96);
  margin: 0 0 38px;
  /* No italics. Gravity from weight + size. */
}

.drill-chamber__composer { width: 100%; }
.drill-chamber__composer textarea {
  width: 100%;
  background: transparent;
  border: 0;
  border-bottom: 1px solid rgba(247, 236, 225, 0.16);
  outline: 0;
  resize: none;
  color: rgba(247, 236, 225, 0.96);
  font-family: inherit;
  font-size: 17px;
  line-height: 1.72;
  padding: 12px 0;
  min-height: 90px;
  transition: border-bottom-color 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__composer textarea:focus { border-bottom-color: rgba(176, 156, 224, 0.55); }
.drill-chamber__composer textarea::placeholder { color: rgba(247, 236, 225, 0.30); }
.drill-chamber__composer-foot {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 14px;
  font-size: 11px;
  letter-spacing: 0.04em;
  color: rgba(247, 236, 225, 0.36);
}
.drill-chamber__hint { color: rgba(247, 236, 225, 0.36); }
.drill-chamber__send {
  background: transparent;
  color: rgba(176, 156, 224, 0.85);
  border: 1px solid rgba(176, 156, 224, 0.32);
  border-radius: 999px;
  padding: 8px 22px;
  font-family: inherit;
  font-size: 12px;
  letter-spacing: 0.04em;
  cursor: pointer;
  transition: all 240ms cubic-bezier(0.16, 1, 0.3, 1);
}
.drill-chamber__send:hover {
  background: rgba(176, 156, 224, 0.10);
  border-color: rgba(176, 156, 224, 0.60);
  color: rgba(247, 236, 225, 0.96);
}
.drill-chamber__send[disabled] { opacity: 0.40; cursor: not-allowed; }

/* Subtle motion on send */
.drill-chamber__active.is-fading-out { opacity: 0.22; transition-duration: 240ms; }
.drill-chamber__active.is-fading-in { animation: drill-chamber-active-in 320ms cubic-bezier(0.16, 1, 0.3, 1) both; }
@keyframes drill-chamber-active-in {
  from { opacity: 0; transform: translateY(4px); }
  to   { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .drill-chamber__active,
  .drill-chamber__history-expanded { animation: none; transition: none; }
}
```

- [ ] **Step 2.5: Cache-bust the CSS link**

In `public/index.html`, bump `drill-chamber.css?v=1` → `drill-chamber.css?v=2`.

- [ ] **Step 3: Manual visual smoke (in main checkout via dev server)**

Temporarily reveal the chamber to verify CSS:

```bash
# In a browser, run from devtools:
document.getElementById('drill-chamber-view').hidden = false;
document.getElementById('chamber-question').textContent = 'Where does the proton gradient on the inner membrane drive ATP synthase?';
document.getElementById('chamber-concept-name').textContent = 'Mitochondrial respiration';
document.getElementById('chamber-entry-name').textContent = 'Core thesis';
```

Confirm visually: dark background, single column, anchor pillar visible on left of active block, composer hairline lights violet on focus, history widget hidden until populated.

- [ ] **Step 4: Hide it again**

```js
document.getElementById('drill-chamber-view').hidden = true;
```

- [ ] **Step 5: Commit**

```bash
git add public/css/drill-chamber.css public/index.html
git commit -m "feat(drill-chamber): port ironclad styles from lab"
```

---

## Task 4: Chamber JS module — render + state, no networking yet

**Files:**
- Create: `public/js/drill-chamber.js`
- Test: `tests/e2e/test_drill_chamber.py` (added in later task)

- [ ] **Step 1: Create the module skeleton**

Create `public/js/drill-chamber.js`:

```js
/* drill-chamber.js — production view module for the ironclad drill chamber.
   Design-of-record: public/_lab/drill-chamber-iterations.html?variant=ironclad
   Companion notes: public/_lab/drill-chamber-iterations.NOTES.md

   Public surface:
     - DrillChamber.show({conceptName, entryName, question})
     - DrillChamber.hide()
     - DrillChamber.appendHistoryTurn(role, text)   // role = 'ai' | 'learner'
     - DrillChamber.swapQuestion(text)               // animates the question swap
     - DrillChamber.setComposerEnabled(bool)
     - DrillChamber.getComposerValue()
     - DrillChamber.clearComposer()
     - DrillChamber.onSend(handler)                  // handler receives raw composer text
     - DrillChamber.onExit(handler)
*/

const els = {};
let sendHandler = null;
let exitHandler = null;
let historyTurns = 0;

function bind() {
  if (els.bound) return;
  els.view = document.getElementById('drill-chamber-view');
  els.conceptName = document.getElementById('chamber-concept-name');
  els.entryName = document.getElementById('chamber-entry-name');
  els.question = document.getElementById('chamber-question');
  els.active = document.getElementById('chamber-active');
  els.composer = document.getElementById('chamber-composer');
  els.send = document.getElementById('chamber-send');
  els.exit = document.getElementById('chamber-exit');
  els.historyWidget = document.getElementById('chamber-history-widget');
  els.historyCount = document.getElementById('chamber-history-count');
  els.historyToggle = document.getElementById('chamber-history-toggle');
  els.historyExpanded = document.getElementById('chamber-history-expanded');

  if (!els.view) return;

  els.send.addEventListener('click', () => {
    if (typeof sendHandler !== 'function') return;
    sendHandler(getComposerValue());
  });
  els.composer.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      e.preventDefault();
      els.send.click();
    }
  });
  els.exit.addEventListener('click', () => {
    if (typeof exitHandler === 'function') exitHandler();
  });
  els.historyToggle.addEventListener('click', () => {
    const expanded = els.historyWidget.classList.toggle('is-expanded');
    els.historyToggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    els.historyToggle.textContent = expanded ? 'hide' : 'show';
  });

  els.bound = true;
}

function show({ conceptName, entryName, question }) {
  bind();
  if (!els.view) return;
  els.conceptName.textContent = conceptName || '—';
  els.entryName.textContent = entryName || '—';
  els.question.textContent = question || '—';
  els.composer.value = '';
  setComposerEnabled(true);
  resetHistory();
  els.view.hidden = false;
  // focus after the view becomes visible
  requestAnimationFrame(() => els.composer.focus());
}

function hide() {
  bind();
  if (!els.view) return;
  els.view.hidden = true;
}

function resetHistory() {
  bind();
  historyTurns = 0;
  els.historyCount.textContent = '0';
  els.historyExpanded.innerHTML = '';
  els.historyWidget.hidden = true;
  els.historyWidget.classList.remove('is-expanded');
  els.historyToggle.setAttribute('aria-expanded', 'false');
  els.historyToggle.textContent = 'show';
}

function appendHistoryTurn(role, text) {
  bind();
  const turn = document.createElement('div');
  turn.className = 'drill-chamber__history-turn' + (role === 'learner' ? ' drill-chamber__history-turn--learner' : '');
  const meta = document.createElement('div');
  meta.className = 'drill-chamber__history-turn-meta';
  meta.textContent = role === 'learner' ? 'you' : 'socratink';
  const body = document.createElement('div');
  body.className = 'drill-chamber__history-body';
  body.textContent = text;
  turn.appendChild(meta);
  turn.appendChild(body);
  els.historyExpanded.appendChild(turn);
  historyTurns += 1;
  els.historyCount.textContent = String(historyTurns);
  els.historyWidget.hidden = false;
}

function swapQuestion(nextText) {
  bind();
  els.active.classList.add('is-fading-out');
  setTimeout(() => {
    els.question.textContent = nextText;
    els.composer.value = '';
    els.active.classList.remove('is-fading-out');
    void els.active.offsetWidth;
    els.active.classList.add('is-fading-in');
    setTimeout(() => els.active.classList.remove('is-fading-in'), 360);
    els.composer.focus();
  }, 240);
}

function setComposerEnabled(enabled) {
  bind();
  els.composer.disabled = !enabled;
  els.send.disabled = !enabled;
}

function getComposerValue() {
  bind();
  return (els.composer.value || '').trim();
}

function clearComposer() {
  bind();
  els.composer.value = '';
}

function onSend(handler) { sendHandler = handler; }
function onExit(handler) { exitHandler = handler; }

window.DrillChamber = {
  show, hide, appendHistoryTurn, swapQuestion,
  setComposerEnabled, getComposerValue, clearComposer,
  onSend, onExit,
};
```

- [ ] **Step 2: Link the module in index.html**

In `public/index.html`, after the `<script type="module" src="js/app.js?v=82"></script>` line, add:

```html
<script src="js/drill-chamber.js?v=1"></script>
```

(Plain script, not module — the chamber attaches to `window.DrillChamber` for app.js to call.)

- [ ] **Step 3: Manual smoke (in main checkout via dev server)**

```js
DrillChamber.show({ conceptName: 'Mitochondrial respiration', entryName: 'Core thesis', question: 'Where does the proton gradient drive ATP synthase?' });
DrillChamber.appendHistoryTurn('ai', 'Walk me through the linking step.');
DrillChamber.appendHistoryTurn('learner', 'Pyruvate becomes acetyl-CoA via pyruvate dehydrogenase, releasing CO2.');
DrillChamber.swapQuestion('And the NADH — where does it come from in this step?');
DrillChamber.hide();
```

Expected: chamber appears with seeded data, history widget shows "2 earlier turns", expand button reveals the two turns, swap animation runs, hide collapses cleanly.

- [ ] **Step 4: Commit**

```bash
git add public/js/drill-chamber.js public/index.html
git commit -m "feat(drill-chamber): add chamber view module"
```

---

## Task 5: Wire entry — startDrill opens the chamber instead of expanding embedded UI

**Files:**
- Modify: `public/js/app.js`

- [ ] **Step 1: Locate startDrill**

In `public/js/app.js`, find the function `startDrill(nodeContext = null)` (around line 3496). Read through to the end of the function — it currently sets `activeDrillNode`, configures the embedded UI, calls `currentGraphController?.setActiveDrillNode?.()`, makes the first `/api/drill` call, and renders the AI's first prompt into `chatHistory`.

- [ ] **Step 2: Insert chamber-show before the first `/api/drill` call**

At the point where the first `/api/drill` call happens (after the spacing/limit guards, before the `requestDrillTurn(...)` invocation that fetches the opening AI prompt), insert:

```js
const conceptName = concept?.name || concept?.metadata?.name || 'Concept';
const entryName = nodeContext.fullLabel || nodeContext.id || 'Entry';
window.DrillChamber.show({
  conceptName,
  entryName,
  question: nodeContext.detail || 'Explain this in your own words.',
});
window.DrillChamber.setComposerEnabled(false);  // wait for first AI turn to enable
```

Replace the placeholder seed-question once the first `/api/drill` response arrives — see Task 6.

- [ ] **Step 3: Wire the chamber's send + exit handlers**

Inside `startDrill`, AFTER `DrillChamber.show(...)`, register the handlers:

```js
window.DrillChamber.onSend(async (text) => {
  if (!text || drillState.pending) return;
  window.DrillChamber.appendHistoryTurn('learner', text);
  window.DrillChamber.appendHistoryTurn('ai', els.chamberQuestionLastShown || '');
  // The above two lines accumulate the "completed turn" into history.
  // The ai turn was the question we'd just been asked; learner is what they wrote.
  // requestDrillTurn handles the network + response rendering (Task 6).
  window.DrillChamber.setComposerEnabled(false);
  try {
    await requestDrillTurn(text);
  } catch (err) {
    console.error(err);
    window.DrillChamber.swapQuestion('The drill service failed to respond. Try again when ready.');
    window.DrillChamber.setComposerEnabled(true);
  }
});

window.DrillChamber.onExit(() => {
  cancelDrill();
});
```

(Note: `els.chamberQuestionLastShown` is a closure value the chamber-aware refactor of `requestDrillTurn` will set in Task 6. For now, omit that line if it errors and re-add in Task 6.)

- [ ] **Step 4: Commit**

```bash
git add public/js/app.js
git commit -m "feat(drill-chamber): wire startDrill to open chamber view"
```

---

## Task 6: Refactor requestDrillTurn to render into the chamber

**Files:**
- Modify: `public/js/app.js`

- [ ] **Step 1: Find requestDrillTurn**

In `public/js/app.js`, find `async function requestDrillTurn(text)` (search for the function — it's near `appendBubble`). Read it. It currently posts to `/api/drill`, processes the response, calls `appendBubble('ai', data.agent_response)`, and updates graph state.

- [ ] **Step 2: Replace bubble rendering with chamber-aware rendering**

Where the current code does `appendBubble('ai', data.agent_response)`, replace with:

```js
// Render the AI response into the chamber, not the embedded chat history.
window.DrillChamber.swapQuestion(data.agent_response || '—');
window.DrillChamber.setComposerEnabled(!data.session_terminated);
// Track the last-shown question so the next learner turn can be paired with
// it in history (see startDrill onSend handler).
els.chamberQuestionLastShown = data.agent_response || '';
```

If `els` is not in scope, declare a module-level `let chamberLastShownQuestion = '';` near the top of the drill-related code and use it in both places.

- [ ] **Step 3: Stub `appendBubble` so old call sites do not crash**

`appendBubble` may still be called from elsewhere. Make it a no-op for `'user'` (the chamber doesn't need it — the learner already sees their text in the composer until they send) and route `'ai'` calls to the chamber:

```js
function appendBubble(role, text) {
  if (role === 'ai' && window.DrillChamber) {
    window.DrillChamber.swapQuestion(text);
  }
  // 'user' is handled by the chamber's history widget on send.
}
```

- [ ] **Step 4: Update the seed prompt path**

In `startDrill`, after the first `/api/drill` call resolves and the chamber is ready, ensure the chamber's question shows the AI's opening prompt (not the placeholder seed). Verify this by reading the actual data flow in `startDrill`. If the opening prompt comes back from `/api/drill` with `data.agent_response`, the existing `swapQuestion` call in Step 2 already covers it.

- [ ] **Step 5: Manual smoke**

In the main checkout dev server:
1. Open a concept, click "Try from memory" on the active node
2. Confirm the chamber appears with the AI's opening question
3. Type a reply, hit cmd+return
4. Confirm: composer disables, the AI response replaces the question (with fade), composer re-enables, history widget shows "2 earlier turns", expand reveals the two turns
5. Hit "← Return to map" — confirm the chamber hides and the concept page is restored

- [ ] **Step 6: Commit**

```bash
git add public/js/app.js
git commit -m "feat(drill-chamber): route drill responses through chamber view"
```

---

## Task 7: Wire exit — cancelDrill closes the chamber and restores map view

**Files:**
- Modify: `public/js/app.js`

- [ ] **Step 1: Find cancelDrill**

`cancelDrill()` is around line 3605 in `public/js/app.js`.

- [ ] **Step 2: Add chamber-hide call**

At the START of `cancelDrill`, before any other state cleanup, add:

```js
if (window.DrillChamber) {
  window.DrillChamber.hide();
}
```

- [ ] **Step 3: Restore map view if not already visible**

Inside `cancelDrill`, after the existing `chatHistory.innerHTML = ''` line (or wherever the function currently restores UI), ensure the concept page is shown:

```js
// Restore the concept page view (map + detail). The chamber hid it on entry.
const activeConcept = getActiveConcept();
if (activeConcept) {
  showMapView(activeConcept, { keepSelection: true });
}
```

If `showMapView` accepts no `keepSelection` option, call `showMapView(activeConcept)` and accept the default reset.

- [ ] **Step 4: Manual smoke**

Repeat the smoke from Task 6 Step 5. Specifically verify:
- After exit, the concept page renders with the map and the prior-active node still visible/highlighted
- No stale chamber state — opening a different concept and entering its chamber works fresh

- [ ] **Step 5: Commit**

```bash
git add public/js/app.js
git commit -m "feat(drill-chamber): wire cancelDrill to hide chamber + restore map"
```

---

## Task 8: Remove the embedded drill UI from the graph-detail panel

**Files:**
- Modify: `public/index.html`
- Modify: `public/js/app.js`
- Modify: `public/css/layout.css`

- [ ] **Step 1: Delete the embedded drill markup**

In `public/index.html`, remove the entire block:

```html
<div class="drill-ui drill-ui-embedded" id="drill-ui">
  <div class="drill-header">
    <button class="drill-back" onclick="App.cancelDrill()">← Back</button>
    <span class="drill-title" id="drill-title">Cold Attempt</span>
  </div>
  <div class="chat-history" id="chat-history"></div>
  <div class="chat-input-area">
    <textarea class="chat-input" id="chat-input" placeholder="Write what you can reconstruct from memory."
      rows="2"></textarea>
  </div>
</div>
```

- [ ] **Step 2: Remove orphan DOM-handle assignments in app.js**

In `public/js/app.js`, near the top where `chatInput`, `chatHistory`, `drillUi`, `drillTitle` are bound (around line 33), keep the variable declarations but make their `getElementById` calls null-safe (they will return null after the markup deletion). Then audit any usage of `chatInput.disabled = ...`, `chatHistory.innerHTML = ...`, etc., and guard each:

```js
if (chatInput) chatInput.value = '';
if (chatInput) chatInput.disabled = true;
if (chatHistory) chatHistory.innerHTML = '';
```

This is defensive — many call sites already crash without these guards once the markup is gone. Walk through every reference (grep for `chatInput\.\|chatHistory\.\|drillUi\.\|drillTitle\.`) and add the guard.

- [ ] **Step 3: Delete dead CSS**

In `public/css/layout.css`, find rules that target `.drill-ui-embedded`, `.drill-ui` (when scoped to the embedded mount), `.chat-input-area`, `.chat-history`. Delete them. Be careful: keep any styles still referenced by the chamber (none should be — the chamber has its own namespace).

- [ ] **Step 4: Bump cache-bust on touched assets**

In `public/index.html`:
- `app.js?v=82` → `app.js?v=83`
- `drill-chamber.css?v=2` (already at v2 from Task 3) — confirm
- `drill-chamber.js?v=1` — confirm

- [ ] **Step 5: Manual smoke**

Re-run the full Task 6 smoke flow. Confirm nothing crashes from removed-element references.

- [ ] **Step 6: Commit**

```bash
git add public/index.html public/js/app.js public/css/layout.css
git commit -m "refactor(drill): remove embedded drill UI; chamber owns the surface"
```

---

## Task 9: Playwright smoke — chamber end-to-end

**Files:**
- Create: `tests/e2e/test_drill_chamber.py`

- [ ] **Step 1: Write the failing test**

Create `tests/e2e/test_drill_chamber.py`:

```python
"""End-to-end smoke for the ironclad drill chamber view.

Covers: enter chamber from concept page, send a turn, receive AI response,
exit back to map, verify state is preserved.
"""
from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect


@pytest.fixture
def base_url() -> str:
    return "http://localhost:8000"


def test_chamber_enters_on_drill_start(page: Page, base_url: str) -> None:
    page.goto(base_url)
    # Guest path — handle /login redirect if it appears
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    # Open the seeded Photosynthesis concept and trigger drill.
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    page.locator("#concept-start-drill").click()  # "Try from memory"
    chamber = page.locator("#drill-chamber-view")
    expect(chamber).to_be_visible()
    # Question should be populated within ~10s after the AI's opening turn.
    expect(page.locator("#chamber-question")).not_to_have_text("—", timeout=10_000)


def test_chamber_send_round_trip(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    page.locator("#concept-start-drill").click()
    expect(page.locator("#drill-chamber-view")).to_be_visible()
    # Wait for opening question
    expect(page.locator("#chamber-question")).not_to_have_text("—", timeout=10_000)
    initial_question = page.locator("#chamber-question").text_content()

    composer = page.locator("#chamber-composer")
    composer.fill(
        "Light is absorbed by chlorophyll and used to split water, producing electrons "
        "that drive ATP synthase via the electron transport chain. The Calvin cycle "
        "fixes CO2 into G3P using the resulting ATP and NADPH."
    )
    page.locator("#chamber-send").click()

    # Question should change after the AI's follow-up arrives.
    expect(page.locator("#chamber-question")).not_to_have_text(initial_question or "", timeout=15_000)
    # History widget should now show >=2 turns
    expect(page.locator("#chamber-history-widget")).to_be_visible()
    expect(page.locator("#chamber-history-count")).to_contain_text("2")


def test_chamber_exit_restores_map(page: Page, base_url: str) -> None:
    page.goto(base_url)
    if page.url.endswith("/login"):
        page.locator("#guest-continue-link").click()
    page.locator('aside .concept-item:has-text("Photosynthesis")').first.click()
    page.locator("#concept-start-drill").click()
    expect(page.locator("#drill-chamber-view")).to_be_visible()
    page.locator("#chamber-exit").click()
    expect(page.locator("#drill-chamber-view")).to_be_hidden()
    # Concept's map view should be visible again.
    expect(page.locator("#graph-content")).to_be_visible()
```

- [ ] **Step 2: Run the smoke**

In the main checkout (where the dev server runs):

```bash
bash scripts/qa-smoke.sh local tests/e2e/test_drill_chamber.py -v
```

If `scripts/qa-smoke.sh` doesn't accept a path arg, run directly:

```bash
HEADED=0 pytest tests/e2e/test_drill_chamber.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 3: If any test fails, fix the implementation, not the test**

Inspect the failure: which assertion failed, what was the actual page state. Common failure modes and fixes:
- Chamber not appearing → check `DrillChamber.show()` is reached; verify `#drill-chamber-view[hidden]` is removed
- Question stuck at `—` → check the seed prompt path; verify `swapQuestion` is being called with the AI response
- History count not updating → check `appendHistoryTurn` is called for both AI and learner sides
- Exit not restoring map → check `showMapView` is called in `cancelDrill` after `DrillChamber.hide()`

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/test_drill_chamber.py
git commit -m "test(e2e): drill chamber smoke — enter, round-trip, exit"
```

---

## Task 10: Coverage gate + final manual verification

**Files:**
- (no edits unless gate fails)

- [ ] **Step 1: Run the coverage gate**

```bash
./scripts/check-coverage.sh
```

Expected: exit 0.

If it fails, the most likely cause is the new `public/js/drill-chamber.js` lacking V8 coverage from the smoke. Fix by ensuring the e2e smoke exercises every branch in the chamber module (mount, send, swap, history toggle, exit). Add additional smoke assertions if necessary.

- [ ] **Step 2: Final manual verify**

In a browser, walk the full happy path with a fresh guest session:
1. Land on Desk
2. Open a concept (Photosynthesis seeded)
3. Click "Try from memory" on the Core Thesis tile
4. Verify chamber appears with the doctrine intact:
   - Anchor pillar visible on the left of the active block
   - History widget hidden (zero turns yet)
   - "Send turn" ghost pill enabled after AI opening
   - Composer placeholder reads "Write what comes to mind. Fragments are fine."
   - Hint reads "a sentence is enough · cmd · return to send"
   - Crumb dims when composer is focused
5. Send a real attempt
6. Verify: composer empties, AI question swaps in with subtle fade, history widget shows "2 earlier turns this attempt"
7. Click `show` on the history — both turns reveal cleanly
8. Click `← Return to map` — chamber hides, concept page restored
9. Verify NO regressions: graph still renders, sidebar concept list still works, ignition still works

- [ ] **Step 3: Final commit message + push**

```bash
git log --oneline dev..HEAD  # confirm all chamber commits are present
git push -u origin feat/drill-chamber-port
```

- [ ] **Step 4: Open the PR via gh**

```bash
gh pr create --base main --title "Drill chamber: ironclad design ported to production" --body "$(cat <<'EOF'
## Summary
- Ports the ironclad drill chamber design from `public/_lab/drill-chamber-iterations.html?variant=ironclad` into production
- Drill is now a separate focused view (full-screen single column), no longer embedded in the right `graph-detail` panel
- Synthesized from 3 customer-feedback rounds (Maya skeptic / Jordan ADHD undergrad / Robert autodidact); see `public/_lab/drill-chamber-iterations.NOTES.md`

## What's new
- `public/css/drill-chamber.css` — chamber styles (anchor pillar, single column, dim-on-focus crumb, subtle ambient glow)
- `public/js/drill-chamber.js` — chamber view module (mount, swap-question, append-turn, history toggle)
- `tests/e2e/test_drill_chamber.py` — 3 smoke tests (enter, round-trip, exit)

## What's removed
- The embedded `<div class="drill-ui drill-ui-embedded">` block in `index.html`
- Dead CSS targeting `.drill-ui-embedded` / `.chat-input-area` / `.chat-history`

## Doctrinal guardrails preserved
- No praise / scoring / mastery copy
- No "AI is typing" indicator
- Composer placeholder honors fragmented recall: "Write what comes to mind. Fragments are fine."
- Sub-affordance: "a sentence is enough"
- Reduced-motion clients get instant transitions

## Test plan
- [x] Manual happy path verified
- [x] e2e smoke (`tests/e2e/test_drill_chamber.py`) — 3/3 passing
- [x] Coverage gate (`./scripts/check-coverage.sh`) — exit 0

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

---

## Self-review notes

**Spec coverage:**
- ✓ Acceptance #1 (chamber takeover): Tasks 5, 7
- ✓ Acceptance #2 (chamber composition): Tasks 2, 3
- ✓ Acceptance #3 (round-trip behavior): Tasks 5, 6
- ✓ Acceptance #4 (exit restoration): Task 7
- ✓ Acceptance #5 (doctrine survives): Task 3 (CSS) + Task 9 (smoke verifies absence of forbidden elements implicitly via the test fixtures using neutral copy)
- ✓ Acceptance #6 (reduced motion): Task 3 (CSS @media block)
- ✓ Acceptance #7 (coverage gate): Task 10
- ✓ Acceptance #8 (Playwright smoke): Task 9

**Open question for the executor:** Whether `chamberLastShownQuestion` is best held as a module-level closure variable in app.js or as a property of the chamber module itself. Either works; pick the one that reads cleanest in the surrounding code style. Default: module-level closure in app.js, since the chamber module shouldn't know about turn-pairing semantics.

**Out of scope for this plan:**
- The "Targeted Study mirror" (the post-attempt artifact saying "you named X / study next: Y"). That's a separate plan — this one only ports the drill chamber surface.
- Light-mode chamber styling. Dark-only for v1, matches the original lab design.
- Mobile-specific layout adjustments. The chamber's max-width 760px works on tablet+; mobile audit is a follow-up.
