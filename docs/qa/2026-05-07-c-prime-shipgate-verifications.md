# C-prime — Ship-Gate Verifications (Antigravity-runnable)

**Date:** 2026-05-07
**Branch under test:** `dev` @ `46f52d6` (or any commit at-or-after this SHA on `dev`)
**Companion to:** `docs/qa/2026-05-07-c-prime-antigravity-qa-plan.md` (which left these two items BLOCKED)

This is a tight, focused prompt covering the two verifications that the prior QA cycle could not exercise: the server-side bypass guard (TC-04 expanded matrix) and the persistence-then-clear ordering under runtime failure injection (TC-113). Together they prove the **doctrinal contracts** of the C-prime redesign hold end-to-end:

- **Principle #2** — no graph or thesis from concept name alone (server enforces with 422).
- **Principle §3.2 ordering** — `socratink:pendingShell` is cleared **only after** client-side persistence succeeds; if persistence fails, the shell stays put.

Estimated total time: ~10 minutes. Output: a 30-line report.

---

## 0. Setup

### 0.1 Backend up

```bash
cd /Users/jondev/dev/socratink/prod/socratink-app
bash scripts/dev-host.sh   # backend at http://127.0.0.1:8000
```

Wait for `Application startup complete`.

### 0.2 Browser ready

Open `http://127.0.0.1:8000` in Chrome via DevTools MCP / claude-in-chrome / equivalent. Sign in if there's an auth gate. Open DevTools.

### 0.3 Clean slate

DevTools → Application → Storage → **Clear site data** → Reload. You should land on an empty home/desk.

---

## TC-A — Server bypass guard (5 variations via curl-equivalent)

The C-prime spec §5.2 table requires `/api/extract` to reject `{name, source: null, starting_sketch: empty/idk-pattern}` with HTTP 422 `error: thin_sketch_no_source`. This guard is the **only** thing standing between a buggy client and provider-prior generation per principle #2 of the spec.

### Method

If your environment supports raw curl (no auth gate or auth bypass available):

```bash
curl -i -s -X POST http://127.0.0.1:8000/api/extract \
  -H "Content-Type: application/json" \
  -d '<PAYLOAD>'
```

If raw curl is auth-blocked, run via FastAPI TestClient (auth bypass via the project's `_FakeAuthService` fixture):

```bash
cd /Users/jondev/dev/socratink/prod/socratink-app
python -c "
from fastapi.testclient import TestClient
from main import app
c = TestClient(app)
import json
payloads = [
    {'name':'X','starting_sketch':'','source':None},
    {'name':'X','starting_sketch':'   ','source':None},
    {'name':'X','starting_sketch':'idk','source':None},
    {'name':'X','starting_sketch':'?','source':None},
    {'name':'X','starting_sketch':\"i don't know\",'source':None},
    {'name':'','starting_sketch':'plants take in light and make sugar','source':None},
    {'name':'X','starting_sketch':'plants take in light and somehow make sugar through leaves','source':None},
]
for p in payloads:
    r = c.post('/api/extract', json=p)
    body = r.json()
    err = body.get('detail',{}).get('error','-') if isinstance(body, dict) else '-'
    print(f'{r.status_code} {err:<32} {json.dumps(p)}')
"
```

### Expected output

| # | Payload | Expected status | Expected error |
|---|---|---|---|
| 1 | empty sketch + source null | **422** | `thin_sketch_no_source` |
| 2 | whitespace-only sketch + source null | **422** | `thin_sketch_no_source` |
| 3 | `idk` | **422** | `thin_sketch_no_source` |
| 4 | `?` | **422** | `thin_sketch_no_source` |
| 5 | `i don't know` | **422** | `thin_sketch_no_source` |
| 6 | empty name + substantive sketch | **422** | `missing_concept` |
| 7 | substantive name + substantive sketch | **200** (or whatever the live AI returns) | — |

### TC-A pass criteria

- Lines 1–5 ALL return `422 thin_sketch_no_source`.
- Line 6 returns `422 missing_concept`.
- Line 7 returns 200 (or any non-422 success status if the model is reachable; if your env doesn't have an AI key, line 7 may return 500 — that is acceptable, just not 422).

If ANY of lines 1–6 returns a status other than 422, OR returns a different error code than specified — that is a **release-blocking regression** of principle #2.

---

## TC-B — Persistence-then-clear under runtime failure injection

The C-prime spec §3.2 requires the launch-pad to clear `socratink:pendingShell` from sessionStorage **only after** client-side persistence succeeds. If persistence throws, the shell stays put so the learner can retry without re-typing.

### Steps

1. From the home/desk, click `New concept`. (Verify: the bottom-nav and top-nav now both read `New concept` — confirms the vocab sweep landed.)
2. The door (Ignition view) appears. Type `TC-B persistence test` in the concept input.
3. DevTools → Console. Paste and run:
   ```javascript
   window.__origPersist = App.persistCreatedConceptFromLaunchPad;
   App.persistCreatedConceptFromLaunchPad = function() {
     throw new Error('TC-B injected failure');
   };
   ```
   Verify the console returns the new function reference (no error).
4. Click the door's arrow submit. Verify in DevTools → Application → Session Storage: `socratink:pendingShell = {"name":"TC-B persistence test","ts":<recent>}`.
5. The launch pad should mount. Type:
   ```
   This is a forced-failure test of the persist-then-clear ordering contract. Long enough threshold to pass both client and server gates.
   ```
   The submit button enables.
6. Open DevTools → Network tab. Click `Build my map`.
7. **Observe in this order:**
   - The `POST /api/extract` request fires and returns **200** (the network call itself succeeds — the server has no idea persistence is patched).
   - The patched `persistCreatedConceptFromLaunchPad` throws "TC-B injected failure" (visible in console).
   - **CRITICAL:** Application → Session Storage shows `socratink:pendingShell` is **STILL PRESENT** (NOT cleared).
   - The launch-pad validation footer shows a retry-friendly error message.
   - The submit button re-enables (or remains enabled) for retry.
8. Verify the user is **still on the launch pad** (NOT navigated to the graph view).
9. Restore the original function:
   ```javascript
   App.persistCreatedConceptFromLaunchPad = window.__origPersist;
   delete window.__origPersist;
   ```
10. Click `Build my map` again. This time:
    - `POST /api/extract` fires (or the response is reused — check Network).
    - Persistence succeeds.
    - sessionStorage `socratink:pendingShell` is now **GONE**.
    - The graph view renders with the smallest route and the *"This is the skeleton…"* framing line.

### TC-B pass criteria

- Step 7: sessionStorage `socratink:pendingShell` is NOT cleared while persistence is patched to throw.
- Step 7: launch pad does not navigate away.
- Step 10: after restoring, the retry succeeds and clears the shell.

If sessionStorage clears in step 7 BEFORE persistence is restored, the persist-then-clear ordering contract is **broken** — that is a release-blocking regression of spec §3.2.

---

## Output: Ship-gate report

Reply with this exact format. Do not skip rows. If a step couldn't be executed, say `BLOCKED` with one-line reason.

```markdown
# C-prime Ship-Gate Report

**Run date:** {YYYY-MM-DD HH:MM TZ}
**Branch:** dev @ {commit SHA at time of run}
**Tester:** {agent + model}
**Backend:** {URL}

## TC-A — Server bypass guard

| # | Payload | Status returned | Error code returned | Result |
|---|---|---|---|---|
| 1 | empty sketch + source null | | | PASS/FAIL |
| 2 | whitespace-only sketch | | | PASS/FAIL |
| 3 | idk | | | PASS/FAIL |
| 4 | ? | | | PASS/FAIL |
| 5 | i don't know | | | PASS/FAIL |
| 6 | empty name + substantive sketch | | | PASS/FAIL |
| 7 | substantive name + substantive sketch | | | PASS/FAIL |

TC-A verdict: PASS / FAIL  [if FAIL, name which row]

## TC-B — Persistence-then-clear

- Step 7 — sessionStorage still present when persistence threw: YES / NO  [evidence: paste the value of sessionStorage.getItem('socratink:pendingShell') from the DevTools console]
- Step 7 — launch pad did not navigate away: YES / NO
- Step 10 — retry after restore succeeded and cleared the shell: YES / NO

TC-B verdict: PASS / FAIL  [if FAIL, name which step]

## Ship-gate verdict

[READY TO PUSH | DO NOT PUSH (list blockers)]

## Notes

(Anything unexpected, console errors, race conditions observed.)
```

---

## Doctrine reminders for the executing agent

- **Don't fix bugs you find.** Report them.
- **Don't restore the patched function before completing step 7's verification.** The whole point is to observe the failure path with sessionStorage intact.
- **Don't accept "looks fine."** Step 7 has a precise check: `sessionStorage.getItem('socratink:pendingShell')` must return a non-null JSON string with the original concept name. Read the value, paste it.
- **TC-B step 6 is the critical observation.** The 200 response from the server is correct; the bug we're guarding against is the client clearing sessionStorage *before* the persistence layer confirms.
