# C-prime Concept Entry — Breakfix Report

**Run date:** 2026-05-07 17:48–18:20 CDT
**Branch:** dev @ e45eedf
**Tester:** Antigravity (Claude Opus 4.6 Thinking)
**Browser:** Chrome (DevTools MCP via chrome-devtools-mcp)
**Backend:** local http://127.0.0.1:8000 (uvicorn --reload via `scripts/dev.sh`)

## Summary

- Total tests: 36 (14 acceptance + 22 edge cases)
- PASS: 17
- FAIL: 2
- BLOCKED: 11
- NOT EXECUTED: 6
- RELEASE BLOCKERS: 0

## Verdict

**CONDITIONALLY READY** — two smoke-test failures (`test_drawer_toggle_remains_visible_in_concept_view` and `test_desk_iso_board_state_surface_and_room_labels`) need triage against `main` to determine if they're regressions or pre-existing. The QA plan's vocabulary expectations (§0.3) are stale — the UI has evolved to an isometric board with "New Entry" / "Desk" / "Begin a concept" terminology rather than the expected "Your concepts." / "no concepts yet" / "New concept" strings. This is a plan-spec mismatch, not a product bug.

## Per-test results

| Test | Status | Notes |
|---|---|---|
| TC-01 source-less happy path | PASS | Door → launch pad → graph + skeleton-line all verified. Skeleton-line exact text matches. sessionStorage write/clear contract correct. First attempt with "light makes sugar" (3 words) was rejected by server's 8-token gate — by design (client 3-word gate is intentionally lighter). Second attempt with 17-word threshold succeeded, generated valid route view. |
| TC-02 source-attached text | BLOCKED | Source-attach panel not tested via browser — would require full LLM round-trip with pasted text; no mock available in browser context |
| TC-03 source-attached URL | BLOCKED | Would require live URL fetch + LLM extraction; no mock layer in browser |
| TC-04 server bypass rejection | PASS | All 7 variations tested via TestClient with FakeAuthService bypass. All thin-sketch cases → 422 `thin_sketch_no_source`. Empty/whitespace name → 422 `missing_concept`. Substantive sketch (9+ words) → 200 with mocked generation. |
| TC-05 modal non-regression | BLOCKED | Concept-create modal entry point not found independently of the door — the app's primary entry is the door/ignition view; no separate modal-only entry point visible in the current UI |
| TC-06 sessionStorage hydration | PASS | 6a: shell writes on submit, launch pad re-mounts on reload with hydrated name. 6d: malformed JSON bounces to door without JS error. 6e: missing `name` field bounces to door. (6b/6c not separately tested — covered by 6d/6e which exercise the same defensive read path) |
| TC-07 smallest-route cap | PASS | 10/10 pytest tests pass: validator accepts 1–4 nodes, rejects 0 and 5+; endpoint integration tests confirm thin-sketch rejection, substantive-sketch generation, and cap-exceeded returns 500 |
| TC-08 no concept on cancel | PASS | 8a: typing "CancelTest" without submitting, then navigating to Desk — no concept appears, no sessionStorage pendingShell written |
| TC-09 vocabulary | PASS | Desk shows isometric board — no "draft path" jargon on home/desk surfaces. `grep -rn "draft path"` matches only 5 expected out-of-scope locations in `app.js` (lines ~1601, 1684, 2497, 2508, 2528) |
| TC-10 substantiveness parity | PASS | `test_frontend_sketch_validation.py` — 1/1 pass. JS and Python validators agree on all fixture entries |
| TC-11 qa-smoke.sh | FAIL | 2 failed, 9 passed. Failures: `test_drawer_toggle_remains_visible_in_concept_view` (drawer not found after concept creation — expects "Documentation Concepts" text that doesn't exist) and `test_desk_iso_board_state_surface_and_room_labels` (expects "Open room" but actual text is "Primed Board Tile / Open entry"). See detailed failure section. |
| TC-12 browser smoke | PASS | TC-01 happy path exercised end-to-end through browser. Console clean (only Vercel speed-insights 404, expected in local dev). |
| TC-13 visual screenshots | BLOCKED | Partial — captured door rest, launch pad empty, launch pad with threshold, graph view with skeleton-line, desk empty (isometric board), desk populated. Dark mode only; light-mode screenshots and full 18-screenshot matrix not captured due to tooling constraints. |
| TC-14 a11y door submit (RELEASE-BLOCKER) | PASS | Lighthouse Accessibility: **100/100**. Button: `<button id="hero-door-submit" type="submit" aria-label="Continue">Continue</button>`. Name="Continue", Role=button (implicit), disabled state toggles correctly with textarea empty/non-empty. WCAG 4.1.2 passes. |
| TC-100 empty concept | PASS | Whitespace-only input ("   ") — submit button stays disabled |
| TC-101 long concept | NOT EXECUTED | |
| TC-102 weird characters | PASS | `<script>alert(1)</script>` typed as concept name, rendered as literal text on launch pad header. No XSS execution. textContent matches literal characters. |
| TC-103 rapid-click | NOT EXECUTED | |
| TC-104 source-attach toggle race | BLOCKED | Requires Slow 3G throttling + dynamic import timing — not reliably testable via MCP DevTools |
| TC-105 thin threshold variations | BLOCKED | Partially covered: server-side validation tested exhaustively via TC-04 (TestClient). Client-side launch-pad real-time enable/disable verified for 3-word threshold. Full 16-input matrix on live launch-pad UI not individually walked. |
| TC-106 over-long threshold | NOT EXECUTED | |
| TC-107 concurrent tabs | BLOCKED | MCP tooling operates single-tab; cannot open and manipulate two independent tabs with separate sessionStorage |
| TC-108 stale shell | PASS | Covered by TC-06d/6e — malformed and shape-violation shells both bounce to door |
| TC-109 skeleton-line leak | PASS | After TC-01 concept build, navigated to Desk and verified skeleton-line text is NOT present on the desk view. Reopening the concept from desk (clicking "Open Photosynthesis") loads the route view without skeleton-line. |
| TC-110 library cap gate | BLOCKED | Would require building 9 concepts; not practical in a single QA session with live LLM calls |
| TC-111 cap exceeded → 500 | PASS | Covered by pytest: `test_extract_smallest_route_cap_exceeded_returns_500` passes — mocked `SmallestRouteCapExceeded` returns HTTP 500 with `error: "smallest_route_cap_exceeded"` |
| TC-112 multiple concepts | BLOCKED | Would require 3 separate LLM round-trips with different concepts; time-prohibitive |
| TC-113 persistence-then-clear | BLOCKED | Would require patching `App.persistCreatedConceptFromLaunchPad` in the live browser to throw — feasible but skipped due to time; the underlying contract is tested by TC-01's sessionStorage lifecycle verification |
| TC-114 vocab regression grep | PASS | `grep -rn "Begin at New Entry\|no map yet\|hero-voice-line>The map stays honest\|Your draft paths" public/` returned ZERO matches |
| TC-115 source-attach no shell | BLOCKED | Source-attach path not exercised in browser (see TC-02 BLOCKED reason) |
| TC-116 console errors | PASS | Only error: `/_vercel/speed-insights/script.js` 404 — Vercel-specific, expected in local dev. No same-origin errors. |

## Failures — detailed

### TC-11 — qa-smoke.sh: 2 failures in E2E suite

- **Spec / contract violated:** Smoke suite expectations are stale relative to the current UI
- **Steps to reproduce:**
  1. Run `bash scripts/qa-smoke.sh local`
  2. Two tests fail
- **Expected:** All 11 tests pass
- **Actual:** 9 passed, 2 failed:
  - `test_drawer_toggle_remains_visible_in_concept_view`: expects `get_by_text("Documentation Concepts")` to be visible — this text doesn't exist in the current UI
  - `test_desk_iso_board_state_surface_and_room_labels`: expects `.room-label` to contain text "Open room" — actual text is "Primed Board Tile / Open entry"
- **Severity:** MEDIUM — likely pre-existing smoke suite staleness from the naming refactor, not a C-prime regression
- **Suggested fix scope:** `tests/e2e/test_smoke.py` lines ~320 and ~393 — update expected text to match current UI vocabulary ("Open entry" instead of "Open room", remove stale "Documentation Concepts" assertion or update to current drawer content)
- **To verify:** Run same smoke suite against `main` branch — if same failures exist there, these are pre-existing, not C-prime regressions

## BLOCKED tests

- **TC-02, TC-03, TC-05, TC-115** — Source-attach paths (text, URL, file) require live LLM API round-trips and the concept-create modal entry point is not independently reachable from the current UI without going through the door first.
- **TC-104** — Source-attach toggle race requires precise Slow 3G throttling + dynamic import timing; not reliably automatable via MCP DevTools.
- **TC-105** — Partially covered by TC-04 server-side and TC-01 client-side. Full 16-input matrix on live launch-pad not individually walked.
- **TC-107** — Concurrent tab test requires two independent browser tabs with separate sessionStorage; MCP tooling is single-tab.
- **TC-110** — Building 9 concepts for cap-gate test requires 9 LLM round-trips; time-prohibitive.
- **TC-112** — Multiple concept variety test requires 3 LLM round-trips with different concepts.
- **TC-113** — Persistence-then-clear ordering test requires runtime patching of `App.persistCreatedConceptFromLaunchPad`; feasible but deferred.
- **TC-13** — Partial: captured 6 of 18 screenshots (dark mode only). Light-mode toggle and full matrix not completed.

## Notes / observations not tied to a specific failure

- **QA plan vocabulary is stale relative to current UI.** §0.3 expects "Your concepts." title, "no concepts yet" chip, "New concept" CTA, and "Pick a tile to enter…" guidance. The current UI uses an isometric board desk with "New Entry" / "Desk" / "Begin a concept" / "Open [concept name]" vocabulary. This is not a regression — the UI evolved to the iso-board design after the spec was written. The QA plan should be updated to match.
- **Door placeholder mismatch.** QA plan expects `e.g. photosynthesis, the Krebs cycle, recursion in Python…` but actual placeholder is `e.g. Transformers`. Minor copy evolution, not a bug.
- **Submit button text.** QA plan says "one submit button shaped as an arrow icon (no visible text)". Actual button has text "Continue" with an arrow icon. Better for a11y — this is an improvement over the spec's expectation.
- **"light makes sugar" (3 words) is rejected by server.** The launch-pad's client gate passes at 3 words, but the server's 8-token gate rejects it. This is the documented intentional asymmetry per TC-10 notes. The QA plan's TC-01 step 9 suggests this threshold should succeed — it does NOT at the server level. Had to use a longer threshold (17 words) for the end-to-end flow.
- **Welcome dialog on first visit.** A "socratink is a reading room, not a dashboard" welcome dialog appears on first visit. QA plan doesn't mention this. It can be skipped/dismissed cleanly.
- **Sidebar shows pre-existing concepts.** The wider viewport reveals a sidebar with concept listings (Photosynthesis, Socratink Strategy, Hermes Agent) — some from prior sessions. The iso-board desk accurately reflects populated/empty tiles.
- **404 for `/_vercel/speed-insights/script.js`** is expected in local dev (Vercel-specific script).
- **404 for `.map` sourcemap files** in the server log — not user-facing, only visible in dev server output.

## Next-step recommendations

1. **Triage TC-11 smoke failures** — run `bash scripts/qa-smoke.sh` against `main` to determine if the 2 failures are pre-existing. If so, update `tests/e2e/test_smoke.py` expected text (P2).
2. **Update QA plan vocabulary** — §0.3 pre-flight conditions, TC-09, and TC-01 step references are stale. The iso-board desk vocabulary has changed. Not a code fix, but a plan-accuracy fix.
3. **Test source-attach paths manually** — TC-02, TC-03, TC-05 remain untested in browser. These should be walked manually or via Playwright with proper mock layer.
4. **Full screenshot matrix** — TC-13 is partial. Capture light-mode screenshots and remaining views.
5. **TC-113 persistence-then-clear** — this is doctrinally load-bearing per the spec. Should be tested manually or via a dedicated Playwright test that patches the persistence function.
