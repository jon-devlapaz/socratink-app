# Pre-merge fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five MUST-FIX bugs identified by the pre-merge code review (superpowers:code-reviewer) and QA test (Kai/Gemini persona) on `feat/drill-chamber-port` so the branch is mergeable to `dev`.

**Architecture:** All fixes are surgical edits to existing files (`public/js/app.js`, `public/js/drill-chamber.js`). No new modules, no architectural shifts.

**Bugs to fix (in execution order):**

1. **B-1** Chamber history pairs each learner reply with the previous AI question (off-by-one) — reviewer
2. **B-2** First-cold-attempt creed writes to deleted `#chat-history`, silently dropped — reviewer
3. **B-3** Visited-node + retry counters increment even when `bypassSessionLimits=true`, polluting telemetry — reviewer
4. **K-20** Send button stays enabled during transit; click-spam sends N duplicate API calls — Kai
5. **K-27** If `/api/drill` returns non-2xx, composer stays disabled forever ("Socratic Void") — Kai

**Out of scope (follow-up PR):**
- B-4 (1px side-stripe), B-5 (reduced-motion fade timing), B-6 (rebind early-return)
- K-19 (4000-char payload limit), K-24 (browser back), K-28 (network drop with auto-retry)
- Test coverage gaps the reviewer named (chamber send round-trip, threshold edit save, entry-0-never-blocked)

**Acceptance criteria (verifiable):**
1. Sending two replies in the chamber produces history entries paired correctly: (AI-q1, learner-r1), (AI-q2, learner-r2). Not the off-by-one shape the reviewer found.
2. After the first cold attempt where `generative_commitment === true`, the chamber surfaces the doctrinal "what you just did" beat (the cold-attempt creed lines).
3. With `bypassSessionLimits=true`, `sessionState.retriesByNode[nodeId]` does NOT increment between drill attempts; `visitedNodeIds` does NOT change.
4. Clicking the Send turn button during a turn-in-flight is a no-op (button is disabled until response lands).
5. When `/api/drill` returns a non-2xx response, the chamber clears the loading placeholder, re-enables the composer, and shows an error message in the question slot ("The drill service failed to respond. Try again when ready." or similar).

---

## Task 1: Pre-flight

- [ ] **Step 1: Confirm worktree is clean**

```bash
cd /Users/jondev/dev/socratink/prod/socratink-app/.worktrees/drill-chamber-port
git status --short
```

Expected: clean, on `feat/drill-chamber-port`.

- [ ] **Step 2: Read the bug context**

Read these files in full before any edit:
- `public/js/app.js` lines 3580-3870 (the drill state machine, `requestDrillTurn`, `startDrill`, the chamber-onSend handler)
- `public/js/drill-chamber.js` (all of it)

Identify each bug's exact location before fixing.

---

## Task 2: B-1 — Fix chamber history off-by-one

**Files:** Modify `public/js/app.js`

**Bug recap:** `chamberLastShownQuestion` is captured by the AI-render path, but on first send it's still `''` because `setLoading(true)` was used instead of `appendBubble`. So the history records (empty AI, learner-r1), then on next send (AI-q1, learner-r2), etc.

- [ ] **Step 1: Seed `chamberLastShownQuestion` at chamber-show time**

In `app.js` find `startDrill` (~line 3722). Right after `window.DrillChamber.show({ ... question: nodeContext.detail || ... })`, set the seed:

```js
chamberLastShownQuestion = nodeContext.detail || 'Explain this in your own words.';
```

This ensures the first send pairs the seed question (which the learner saw on screen) with their first reply.

- [ ] **Step 2: Verify call ordering in onSend handler**

In `startDrill`'s `DrillChamber.onSend(async (text) => { ... })` block (~line 3835), ensure history append happens BEFORE `requestDrillTurn(text)`:

```js
window.DrillChamber.appendHistoryTurn('ai', chamberLastShownQuestion || '');
window.DrillChamber.appendHistoryTurn('learner', text);
window.DrillChamber.setComposerEnabled(false);
try {
  await requestDrillTurn(text);
} catch (err) { /* existing */ }
```

The order is already correct in the file; just verify it's intact and the seed from Step 1 makes the first append non-empty.

- [ ] **Step 3: Manual smoke**

In a browser at `:8001`:
1. Hard reload, open a concept, click Try from memory
2. Wait for first AI question to land
3. Type "first reply", send
4. Wait for follow-up
5. Click `show` on the history widget
6. Verify the FIRST history pair is (AI seed question, "first reply") — NOT (empty, "first reply")

- [ ] **Step 4: Commit**

Bump `app.js?v=` cache-bust by +1. Then:

```bash
git add public/js/app.js public/index.html
git commit -m "fix(chamber): seed chamberLastShownQuestion so first history pair is correct

Bug B-1 from pre-merge review: chamberLastShownQuestion was only
set by appendBubble('ai',...) which runs AFTER requestDrillTurn
resolves. On the first send (the cold attempt), it stayed empty
because setLoading(true) replaced the appendBubble call. Result:
first history entry pairs (empty, learner-r1); subsequent entries
pair (AI-q-prev, learner-r-curr) -- one off.

Fix: seed chamberLastShownQuestion from nodeContext.detail at
DrillChamber.show time so the first send writes the seed question
the learner actually saw on screen."
```

---

## Task 3: B-2 — Route first-cold-attempt creed through the chamber

**Files:** Modify `public/js/app.js`, possibly `public/js/drill-chamber.js`

**Bug recap:** `appendFirstColdAttemptCreed()` writes directly to `#chat-history`, which we deleted. The doctrinal "You tried first / Study has a target now / Return later" beat that lands when `generative_commitment === true` is silently dropped in chamber mode.

- [ ] **Step 1: Read the current creed**

In `app.js`, find `function appendFirstColdAttemptCreed()` (search the file). Read its HTML structure — it's three list items with diamond bullets.

- [ ] **Step 2: Add a `DrillChamber.appendCreed()` method**

In `public/js/drill-chamber.js`, add to the public API:

```js
/**
 * Show the doctrinal first-cold-attempt creed in the chamber after
 * generative_commitment === true. Three lines, diamond bullets,
 * fades in below the active question.
 */
function appendCreed() {
  bind();
  if (!els.view) return;
  // Replace the active question + composer area with the creed.
  // Composer stays present-but-disabled so the learner sees the creed
  // is the moment of completion -- they're not expected to keep typing.
  const creedHtml = `
    <ul class="drill-chamber__creed">
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>You tried first.</strong> The system saw your reasoning before any study material was shown.</span></li>
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>Study has a target now.</strong> The repair is scoped to what you just attempted.</span></li>
      <li><span class="drill-chamber__creed-diamond" aria-hidden="true"></span><span><strong>Return later.</strong> Only spaced re-drill can change the record.</span></li>
  </ul>
  `;
  els.question.insertAdjacentHTML('afterend', creedHtml);
  setComposerEnabled(false);
}
```

Add `appendCreed` to the public API at the bottom of the file:

```js
window.DrillChamber = {
  show, hide, appendHistoryTurn, swapQuestion,
  setComposerEnabled, setLoading,
  getComposerValue, clearComposer,
  appendCreed,
  onSend, onExit,
};
```

- [ ] **Step 3: Add the creed CSS**

In `public/css/drill-chamber.css`, add styles for `.drill-chamber__creed` matching the chamber's quiet idiom (cream/ink in light, cream-on-graphite in dark, diamond bullets violet, line-height 1.7, indent under the question):

```css
.drill-chamber__creed {
  list-style: none;
  margin: 24px 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.drill-chamber__creed li {
  display: grid;
  grid-template-columns: 14px 1fr;
  gap: 12px;
  align-items: start;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text-muted, rgba(36, 32, 56, 0.68));
}
.drill-chamber__creed strong {
  color: var(--text-strong);
  font-weight: 600;
}
.drill-chamber__creed-diamond {
  display: inline-block;
  width: 8px; height: 8px;
  margin-top: 6px;
  background: var(--accent-primary);
  transform: rotate(45deg);
  border-radius: 1px;
}
[data-theme="dark"] .drill-chamber__creed li { color: rgba(247, 236, 225, 0.72); }
[data-theme="dark"] .drill-chamber__creed strong { color: rgba(247, 236, 225, 0.96); }
[data-theme="dark"] .drill-chamber__creed-diamond { background: rgba(176, 156, 224, 0.85); }
```

Bump `drill-chamber.css?v=` cache-bust + `drill-chamber.js?v=` cache-bust.

- [ ] **Step 4: Wire the call site**

In `app.js`'s drill response handler (search for `appendFirstColdAttemptCreed`), find the place where it's called when `generative_commitment === true && drillMode === 'cold_attempt'`. Replace OR add alongside:

```js
if (window.DrillChamber && typeof window.DrillChamber.appendCreed === 'function') {
  window.DrillChamber.appendCreed();
} else if (chatHistory) {
  appendFirstColdAttemptCreed(); // legacy fallback
}
```

If the legacy `appendFirstColdAttemptCreed` is no longer reachable (chat-history is gone), the `else` branch is dead and can be deleted.

- [ ] **Step 5: Manual smoke**

1. Hard reload, open a concept with a fresh entry-0
2. Click Try from memory
3. Type a substantive cold attempt (>200 chars, real engagement)
4. Send
5. After AI response, verify the creed appears below the AI's question, with diamond bullets, in chamber's calm idiom

- [ ] **Step 6: Commit**

```bash
git add public/js/app.js public/js/drill-chamber.js public/css/drill-chamber.css public/index.html
git commit -m "fix(chamber): route first-cold-attempt creed through chamber

Bug B-2 from pre-merge review: appendFirstColdAttemptCreed() wrote
into the deleted #chat-history container. The doctrinal 'You tried
first / Study has a target / Return later' beat that lands when
generative_commitment is true was silently dropped in chamber mode.

Fix: new DrillChamber.appendCreed() method appends the three-line
creed under the active question with diamond bullets matching the
chamber's quiet idiom. Light + dark mode supported."
```

---

## Task 4: B-3 — Don't pollute counters when bypassing limits

**Files:** Modify `public/js/app.js`

**Bug recap:** `markNodeVisitedThisSession`, `retriesByNode++`, and `startedAt = ...` all run unconditionally even when `bypassSessionLimits=true`. Counters get persisted via `persistSessionState` and shipped to the API as `nodes_drilled` / `attempt_turn_count`.

- [ ] **Step 1: Gate the writes**

In `app.js`'s `startDrill` find lines 3793-3795 (the unconditional write block). Wrap in the bypass check:

```js
if (!bypassSessionLimits) {
  if (isNewSessionNode) markNodeVisitedThisSession(nodeContext.id);
  sessionState.retriesByNode[nodeContext.id] = (sessionState.retriesByNode[nodeContext.id] || 0) + 1;
  if (!sessionState.startedAt) sessionState.startedAt = new Date().toISOString();
  persistSessionState();
}
```

Audit any subsequent reads of these counters — they should default to safe values when missing.

- [ ] **Step 2: Manual smoke**

Open a concept, click Try from memory 3+ times in a row on the same entry. Verify:
- No "Retrieval ceiling reached" block (the bypass works)
- `localStorage.getItem('learnops_drill_session')` does NOT show the entry's id in `retriesByNode` after the 3 attempts (counter wasn't bumped)

- [ ] **Step 3: Commit**

```bash
git add public/js/app.js public/index.html
git commit -m "fix(drill): don't pollute session counters when limits bypassed

Bug B-3 from pre-merge review: markNodeVisitedThisSession, retry
counter increment, and startedAt timestamp all ran unconditionally
even with bypassSessionLimits=true. Counters got persisted to
localStorage and shipped to /api/drill as nodes_drilled and
attempt_turn_count.

Fix: gate the writes behind !bypassSessionLimits. When limits
re-enable post-launch, the counter ledger will be clean."
```

---

## Task 5: K-20 — Disable Send during transit

**Files:** Modify `public/js/app.js`

**Bug recap:** Click-spam Send during a turn-in-flight = N duplicate API calls.

- [ ] **Step 1: Audit the existing send guard**

In `app.js`'s `DrillChamber.onSend` handler, the current code is:

```js
window.DrillChamber.onSend(async (text) => {
  if (!text || drillState.pending) return;
  // ... append history, setComposerEnabled(false), requestDrillTurn ...
});
```

The `drillState.pending` check exists. Find where `drillState.pending` is set to `true` at the start of a turn and `false` at the end. Verify it's set BEFORE the API call and cleared after.

- [ ] **Step 2: Belt-and-suspenders the Send button itself**

Even with `drillState.pending`, the button is still visually enabled during transit. Tighten the chamber so the Send button disables synchronously on click:

In `drill-chamber.js`'s `bind()`, change the click handler to:

```js
els.send.addEventListener('click', () => {
  if (typeof sendHandler !== 'function') return;
  if (els.send.disabled) return;        // hard guard against spam
  els.send.disabled = true;             // visually + functionally lock immediately
  els.composer.disabled = true;
  sendHandler(getComposerValue());
});
```

The send button stays disabled until `setComposerEnabled(true)` is called from the response path.

- [ ] **Step 3: Manual smoke**

Open a concept, enter chamber, type a reply, click Send 5 times rapidly. Verify in DevTools Network tab: only ONE `/api/drill` POST is made.

- [ ] **Step 4: Commit**

```bash
git add public/js/drill-chamber.js public/index.html
git commit -m "fix(chamber): hard-disable Send button on click to prevent spam

Bug K-20 from QA test: click-spamming the Send button during a
turn-in-flight could send N duplicate /api/drill POSTs. The
drillState.pending check existed but the button was still visually
clickable.

Fix: Send + composer disable synchronously inside the click handler,
before sendHandler runs. They re-enable from the response path
(setComposerEnabled(true) on success, error path handles failure)."
```

---

## Task 6: K-27 — Handle non-2xx response without trapping the user

**Files:** Modify `public/js/app.js`

**Bug recap:** If `/api/drill` returns 5xx, the composer stays disabled forever ("Socratic Void"). Existing catch block has `setComposerEnabled(false)` in the error path but should re-ENABLE so the learner can retry.

- [ ] **Step 1: Audit the existing error path**

In `app.js`'s `startDrill` `requestDrillTurn().catch(...)` block (~line 3855):

```js
}).catch((err) => {
  console.error(err);
  hideTypingIndicator();
  if (window.DrillChamber) {
    window.DrillChamber.setLoading?.(false);
    window.DrillChamber.swapQuestion('The drill service failed to respond. Try again when ready.');
    window.DrillChamber.setComposerEnabled(false);  // <-- BUG: should be true so retry is possible
  } else {
    appendBubble('ai', 'The drill service failed to respond. Try again when ready.');
  }
  drillState.pending = false;
  if (chatInput) chatInput.disabled = false;
  ...
});
```

- [ ] **Step 2: Re-enable composer on error**

Change `setComposerEnabled(false)` → `setComposerEnabled(true)` in the chamber error branch. The learner can edit their reply and press Send again.

Also audit the other error path at the chamber's `onSend` catch:

```js
} catch (err) {
  console.error(err);
  window.DrillChamber.swapQuestion('The drill service failed to respond. Try again when ready.');
  window.DrillChamber.setComposerEnabled(true);  // <-- already correct here
}
```

This one is correct. Just fix the first one.

- [ ] **Step 3: Manual smoke**

Open DevTools Network tab → enable "Block request URL" for `localhost:8001/api/drill`. Open a concept, click Try from memory. The chamber should:
1. Show the loading placeholder
2. After ~3-10s timeout, show "The drill service failed to respond. Try again when ready." in the question slot
3. Composer should be enabled (you can type)
4. Send turn button should be enabled (you can retry)

Then unblock the URL and click Send again. Should retry successfully.

- [ ] **Step 4: Commit**

```bash
git add public/js/app.js public/index.html
git commit -m "fix(chamber): re-enable composer on /api/drill failure

Bug K-27 from QA test: when /api/drill returns non-2xx, the catch
block sets composer DISABLED, trapping the learner in a 'Socratic
Void' with no way to retry.

Fix: setComposerEnabled(true) in the error path so the learner can
edit their reply and retry the send. The error message in the
question slot tells them what happened."
```

---

## Task 7: Coverage gate + push + PR update

- [ ] **Step 1: Coverage gate**

```bash
./scripts/check-coverage.sh
```

If exit 0: proceed. If non-zero, document the failure in the PR body update.

- [ ] **Step 2: Run the existing e2e to confirm nothing regressed**

```bash
pytest tests/e2e/test_drill_chamber.py tests/e2e/test_concept_page_b2.py tests/e2e/test_strip_nav.py -v
```

All should still pass.

- [ ] **Step 3: Push**

```bash
git push origin feat/drill-chamber-port
```

- [ ] **Step 4: Update PR description**

Append a section to PR #236 noting the pre-merge fixes landed:

```bash
gh pr view 236 --json body --jq .body > /tmp/pr-body.txt
cat >> /tmp/pr-body.txt <<'EOF'

## Pre-merge fixes (2026-05-11)

Five bugs identified by the pre-merge code review (superpowers:code-reviewer)
and the QA customer test (Kai persona). All landed in 5 commits:

- B-1: chamber history off-by-one (seeded chamberLastShownQuestion)
- B-2: first-cold-attempt creed routed through chamber (new DrillChamber.appendCreed)
- B-3: bypassed session counters no longer pollute telemetry
- K-20: Send button hard-disables on click (no duplicate POSTs from spam)
- K-27: composer re-enables on /api/drill failure (learner can retry)

Polish items deferred to a follow-up PR:
- B-4 (1px side-stripe), B-5 (reduced-motion fade timing), B-6 (rebind early-return)
- K-19 (4000-char limit), K-24 (browser back), K-28 (auto-retry on network drop)

Branch is now ready for merge to dev.
EOF
gh pr edit 236 --body-file /tmp/pr-body.txt
```

---

## Self-review

**Spec coverage:**
- Acceptance #1 (history pairing): Task 2
- Acceptance #2 (creed surfaces): Task 3
- Acceptance #3 (counters not polluted): Task 4
- Acceptance #4 (no duplicate POSTs from click-spam): Task 5
- Acceptance #5 (recoverable from API failure): Task 6

**No placeholders.** Every step has the exact code or grep target.

**Open question for the executor:** If `appendFirstColdAttemptCreed()` is the legacy function and the e2e suite doesn't currently cover it, and the chamber path is now the only consumer, consider deleting `appendFirstColdAttemptCreed` itself in Task 3 Step 4. The legacy fallback `else` branch keeps it around defensively. Pick whichever feels less rotting.
